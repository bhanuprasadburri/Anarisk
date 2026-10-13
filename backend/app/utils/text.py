"""Text normalisation and similarity used by the impersonation detector and ingestion."""
from __future__ import annotations

import re
import unicodedata

from rapidfuzz import fuzz

# Common Cyrillic / Greek / typographic look-alikes -> ASCII
_HOMOGLYPHS = str.maketrans({
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "у": "y", "х": "x", "і": "i", "ј": "j", "ѕ": "s",
    "һ": "h", "ԁ": "d", "ɡ": "g", "ᴏ": "o", "ο": "o", "ν": "v", "ι": "i", "α": "a", "ρ": "p", "τ": "t",
    "ƅ": "b", "ｌ": "l", "ı": "i", "ӏ": "l", "ɑ": "a", "ȷ": "j",
})
_LEET = str.maketrans({"0": "o", "1": "l", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s", "!": "i", "|": "l"})

# Generic words impersonators append to a brand name; stripped to expose the brand core.
GENERIC_AFFIXES = (
    "official", "real", "support", "help", "helpdesk", "team", "care", "customer", "customercare", "service",
    "services", "verified", "india", "global", "app", "hq", "world", "online", "ofc", "original",
)


def normalize_text(value: str | None) -> str:
    """Unicode-normalise, strip accents, lower-case, map homoglyphs, collapse whitespace."""
    if not value:
        return ""
    s = unicodedata.normalize("NFKD", value)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.translate(_HOMOGLYPHS).casefold()
    s = re.sub(r"\s+", " ", s).strip()
    return s


def squash_identity(value: str | None, *, strip_affixes: bool = False) -> str:
    """Aggressive identity form: normalised, leetspeak mapped, only [a-z0-9]. Optionally drops generic affixes."""
    s = normalize_text(value).translate(_LEET)
    s = re.sub(r"[^a-z0-9]", "", s)
    if strip_affixes:
        changed = True
        while changed and s:
            changed = False
            for a in sorted(GENERIC_AFFIXES, key=len, reverse=True):
                if s.startswith(a) and len(s) - len(a) >= 3:
                    s, changed = s[len(a):], True
                if s.endswith(a) and len(s) - len(a) >= 3:
                    s, changed = s[: -len(a)], True
    return s


# Long, unambiguous generic words are ignored wherever they appear (inserting "official" mid-name must not
# make an impersonation look *less* similar). Short affixes ('app', 'hq') are only trimmed at the edges.
_STRONG_GENERIC = tuple(sorted((a for a in GENERIC_AFFIXES if len(a) >= 6), key=len, reverse=True))


def _drop_strong_generic(s: str) -> str:
    out = s
    for a in _STRONG_GENERIC:
        out = out.replace(a, "")
    return out if len(out) >= 3 else s


def identity_similarity(a: str | None, b: str | None) -> tuple[float, str]:
    """Similarity in [0,1] between two names/handles plus a short reason string."""
    sa, sb = squash_identity(a), squash_identity(b)
    if not sa or not sb:
        return 0.0, "empty"
    if sa == sb:
        return 1.0, "identical after normalisation"
    ca, cb = squash_identity(a, strip_affixes=True), squash_identity(b, strip_affixes=True)
    if ca and cb and ca == cb:
        return 0.95, "identical once generic words (e.g. 'official', 'support') are removed"
    best, reason = fuzz.ratio(sa, sb) / 100, "edit-distance ratio"
    core = fuzz.ratio(ca, cb) / 100 if ca and cb else 0.0
    if core > best:
        best, reason = core * 0.97, "edit-distance ratio after removing generic words"
    # brand embedded in a longer identity (e.g. 'acmebank_rewards_claim')
    short, long_ = sorted((_drop_strong_generic(ca or sa), _drop_strong_generic(cb or sb)), key=len)
    if len(short) >= 5 and short in long_ and short != long_:
        embed = 0.80 + 0.15 * (len(short) / len(long_))
        if embed > best:
            best, reason = min(embed, 0.95), "official name embedded in a longer identity"
    return max(0.0, min(1.0, best)), reason


def text_overlap(a: str | None, b: str | None) -> float:
    """Word-set overlap in [0,1] for bios/descriptions (detects copied text, tolerant to reordering)."""
    na, nb = normalize_text(a), normalize_text(b)
    if len(na) < 20 or len(nb) < 20:
        return 0.0
    return fuzz.token_set_ratio(na, nb) / 100
