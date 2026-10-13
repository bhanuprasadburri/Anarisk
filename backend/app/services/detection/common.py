"""Helpers that read entity data consistently for every detector, plus pairwise relationship indicators
(shared by coordination detection and relationship discovery so both agree on what 'linked' means)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Iterable

from app.core.config import Settings
from app.models import BrandReference, DigitalEntity, EvidenceRecord
from app.models.enums import EntityType, ReferenceKind, RelationshipType
from app.utils.images import hamming, is_valid_phash
from app.utils.text import identity_similarity, normalize_text, text_overlap
from app.utils.urls import extract_urls, parse_url, registrable_domain

# Shared platforms: many unrelated entities legitimately link to these, so they never imply a connection.
COMMON_PLATFORM_DOMAINS = {
    "google.com", "apple.com", "facebook.com", "instagram.com", "twitter.com", "x.com", "youtube.com",
    "linkedin.com", "t.me", "wa.me", "whatsapp.com", "github.com", "tiktok.com", "reddit.com", "telegram.org",
    "play.google.com", "apps.apple.com", "wikipedia.org", "linktr.ee", "bit.ly", "tinyurl.com", "goo.gl", "t.co",
}


def attrs(e: DigitalEntity) -> dict[str, Any]:
    return e.attributes or {}


def parse_dt(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, str) and value:
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
        except ValueError:
            return None
    return None


def entity_created_at(e: DigitalEntity) -> tuple[datetime | None, str | None]:
    a = attrs(e)
    for key in ("account_created_at", "registered_at", "published_at"):
        dt = parse_dt(a.get(key))
        if dt:
            return dt, key
    return None, None


def post_timestamps(e: DigitalEntity) -> list[datetime]:
    out = [parse_dt(v) for v in (attrs(e).get("post_timestamps") or [])]
    return sorted(d for d in out if d)


def entity_bio(e: DigitalEntity) -> str | None:
    a = attrs(e)
    return a.get("bio") or a.get("description")


def entity_name_fields(e: DigitalEntity) -> list[tuple[str, str]]:
    a = attrs(e)
    fields = [("display_name", e.display_name)]
    for key in ("handle", "app_name", "page_title"):
        if a.get(key):
            fields.append((key, str(a[key])))
    seen, out = set(), []
    for k, v in fields:
        if v and (k, v) not in seen:
            seen.add((k, v))
            out.append((k, v))
    return out


def entity_urls(e: DigitalEntity, *, include_store_url: bool = False) -> list[str]:
    """All URL strings associated with the entity (own URL + outbound links + links found in free text)."""
    a = attrs(e)
    urls: list[str] = []
    if e.source_url:
        urls.append(e.source_url)
    if a.get("url"):
        urls.append(a["url"])
    if a.get("domain"):
        urls.append(a["domain"])
    if e.entity_type == EntityType.DOMAIN:
        urls.append(e.canonical_id)
    urls += list(a.get("links") or []) + list(a.get("linked_websites") or [])
    if include_store_url and a.get("store_url"):
        urls.append(a["store_url"])
    urls += extract_urls(a.get("bio")) + extract_urls(a.get("description"))
    if e.entity_type == EntityType.MOBILE_APP and not include_store_url and e.source_url == a.get("store_url"):
        urls = [u for u in urls if u != e.source_url]  # the store listing itself is not an outbound destination
    seen, out = set(), []
    for u in urls:
        if u and u not in seen:
            seen.add(u)
            out.append(u)
    return out


def linked_registrable_domains(e: DigitalEntity, exclude: Iterable[str] = ()) -> set[str]:
    excluded = set(exclude) | COMMON_PLATFORM_DOMAINS
    out = set()
    for u in entity_urls(e):
        p = parse_url(u)
        if p and not p.is_ip and p.registrable_domain not in excluded:
            out.add(p.registrable_domain)
    # an entity that *is* a website/domain also "uses" its own domain
    if e.entity_type in (EntityType.WEBSITE, EntityType.DOMAIN):
        p = parse_url(e.source_url or e.canonical_id)
        if p and p.registrable_domain not in excluded:
            out.add(p.registrable_domain)
    return out


def official_domains(references: Iterable[BrandReference]) -> set[str]:
    out = set()
    for r in references:
        if r.kind == ReferenceKind.DOMAIN:
            p = parse_url(r.value)
            out.add(p.registrable_domain if p else r.normalized_value)
    return out


def entity_hashes(e: DigitalEntity, evidence: Iterable[EvidenceRecord] = ()) -> list[dict[str, Any]]:
    """Perceptual hashes belonging to the entity: attribute-supplied hashes and hashes of uploaded evidence images."""
    a = attrs(e)
    found: list[dict[str, Any]] = []
    attr_hashes = list(a.get("image_phashes") or [])
    for key in ("phash", "profile_image_phash"):
        if a.get(key):
            attr_hashes.append(a[key])
    for h in attr_hashes:
        if is_valid_phash(h):
            found.append({"hash": h.lower(), "source": "attribute", "evidence_id": None, "sha256": None})
    for ev in evidence:
        if ev.perceptual_hash and is_valid_phash(ev.perceptual_hash):
            found.append({"hash": ev.perceptual_hash.lower(), "source": "evidence", "evidence_id": str(ev.id), "sha256": ev.sha256})
    uniq, seen = [], set()
    for f in found:
        k = (f["hash"], f["evidence_id"])
        if k not in seen:
            seen.add(k)
            uniq.append(f)
    return uniq


@dataclass
class PairIndicator:
    kind: RelationshipType
    confidence: float
    note: str
    evidence_id: str | None = None
    meta: dict[str, Any] | None = None


def synced_post_windows(a: list[datetime], b: list[datetime], window_s: int, cap: int = 1000) -> int:
    """Number of distinct time windows in which both accounts posted within `window_s` seconds of each other."""
    a, b = a[-cap:], b[-cap:]
    i = j = 0
    hits: set[int] = set()
    while i < len(a) and j < len(b):
        delta = (a[i] - b[j]).total_seconds()
        if abs(delta) <= window_s:
            hits.add(int(min(a[i], b[j]).timestamp() // max(window_s, 1)))
            i += 1
            j += 1
        elif delta < 0:
            i += 1
        else:
            j += 1
    return len(hits)


def pair_indicators(
    a: DigitalEntity, b: DigitalEntity, s: Settings, *, official: set[str],
    a_ev: Iterable[EvidenceRecord] = (), b_ev: Iterable[EvidenceRecord] = (),
) -> list[PairIndicator]:
    """Observable indicators linking two entities of one brand. Only reports what the data actually shows."""
    out: list[PairIndicator] = []

    # 1. shared / near-identical images
    ha, hb = entity_hashes(a, a_ev), entity_hashes(b, b_ev)
    best = None
    for x in ha:
        for y in hb:
            d = hamming(x["hash"], y["hash"])
            if d <= s.discovery_image_distance and (best is None or d < best[0]):
                best = (d, x, y)
    if best:
        d, x, y = best
        conf = 0.95 if d == 0 else max(0.6, 0.9 - 0.075 * d)
        out.append(PairIndicator(
            RelationshipType.SHARES_IMAGE, round(conf, 3),
            f"Images match (perceptual-hash distance {d}/64): {x['hash']} ~ {y['hash']}",
            evidence_id=x["evidence_id"] or y["evidence_id"], meta={"distance": d},
        ))

    # 2. shared linked domains (excluding official brand domains and common platforms)
    shared = linked_registrable_domains(a, official) & linked_registrable_domains(b, official)
    if shared:
        out.append(PairIndicator(
            RelationshipType.SHARES_DOMAIN, 0.8, "Both reference the same domain(s): " + ", ".join(sorted(shared)),
            meta={"domains": sorted(shared)},
        ))

    # 3. similar identity (names/handles, or copied bios)
    best_sim, best_pair = 0.0, None
    for ka, va in entity_name_fields(a):
        for kb, vb in entity_name_fields(b):
            sim, _ = identity_similarity(va, vb)
            if sim > best_sim:
                best_sim, best_pair = sim, (ka, va, kb, vb)
    bio_overlap = text_overlap(entity_bio(a), entity_bio(b))
    if best_sim >= 0.92 and best_pair:
        out.append(PairIndicator(
            RelationshipType.SIMILAR_IDENTITY, round(min(0.9, best_sim * 0.9), 3),
            f"Near-identical identity: {best_pair[0]}='{best_pair[1]}' vs {best_pair[2]}='{best_pair[3]}' (similarity {best_sim:.2f})",
            meta={"similarity": round(best_sim, 3)},
        ))
    elif bio_overlap >= 0.9:
        out.append(PairIndicator(
            RelationshipType.SIMILAR_IDENTITY, 0.85, f"Bio/description text is nearly identical (overlap {bio_overlap:.2f})",
            meta={"bio_overlap": round(bio_overlap, 3)},
        ))

    # 4. same infrastructure (only when hosting data was supplied/collected)
    ia, ib = attrs(a).get("hosting") or {}, attrs(b).get("hosting") or {}
    ips = ({str(ia["ip"]).strip()} if ia.get("ip") else set()) & ({str(ib["ip"]).strip()} if ib.get("ip") else set())
    ns = {n.lower() for n in (ia.get("nameservers") or [])} & {n.lower() for n in (ib.get("nameservers") or [])}
    if ips:
        out.append(PairIndicator(RelationshipType.SAME_INFRASTRUCTURE, 0.85, f"Same hosting IP: {sorted(ips)[0]}", meta={"ip": sorted(ips)[0]}))
    elif ns:
        out.append(PairIndicator(RelationshipType.SAME_INFRASTRUCTURE, 0.6, "Same nameserver(s): " + ", ".join(sorted(ns)), meta={"nameservers": sorted(ns)}))

    # 5. coordinated behaviour (synchronised posting)
    pa, pb = post_timestamps(a), post_timestamps(b)
    if pa and pb:
        n = synced_post_windows(pa, pb, s.sync_window_seconds)
        if n >= 3:
            out.append(PairIndicator(
                RelationshipType.COORDINATED_BEHAVIOR, round(min(0.9, 0.4 + 0.1 * n), 3),
                f"Posted within {s.sync_window_seconds}s of each other in {n} separate time windows", meta={"synced_windows": n},
            ))
    return out
