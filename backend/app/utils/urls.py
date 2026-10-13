"""Safe URL parsing and normalisation. Pure functions - never performs network access."""
from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

MAX_URL_LENGTH = 2048
_CTRL = re.compile(r"[\x00-\x20\x7f]")
_HOST_LABEL = re.compile(r"^(?!-)[a-z0-9-]{1,63}(?<!-)$")
_TRACKING = re.compile(r"^(utm_|fbclid$|gclid$|mc_|ref$)")

# Minimal multi-part public suffix list (offline). Production should use the full Public Suffix List.
_MULTI_SUFFIXES = {
    "co.uk", "org.uk", "ac.uk", "gov.uk", "com.au", "net.au", "org.au", "co.in", "net.in", "org.in", "co.nz",
    "co.za", "com.br", "com.cn", "com.mx", "co.jp", "com.sg", "com.tr", "com.ar", "co.id", "com.pk", "com.bd",
}
_URL_IN_TEXT = re.compile(r"(?i)\b(?:https?://|www\.)[^\s<>\"']+")


@dataclass(frozen=True)
class ParsedUrl:
    original: str
    scheme: str
    host: str  # IDNA (punycode) lower-case host without port
    unicode_host: str
    port: int | None
    path: str
    query: str
    has_userinfo: bool
    is_ip: bool

    @property
    def registrable_domain(self) -> str:
        return registrable_domain(self.host)

    @property
    def canonical(self) -> str:
        netloc = self.host + (f":{self.port}" if self.port and self.port not in (80, 443) else "")
        path = self.path.rstrip("/") or ""
        qs = urlencode(sorted((k, v) for k, v in parse_qsl(self.query, keep_blank_values=True) if not _TRACKING.match(k)))
        return urlunsplit((self.scheme, netloc, path, qs, ""))


def is_valid_hostname(host: str) -> bool:
    if not host or len(host) > 253:
        return False
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        pass
    labels = host.split(".")
    return len(labels) >= 2 and all(_HOST_LABEL.match(l) for l in labels)


def to_idna(host: str) -> str:
    try:
        return host.encode("idna").decode("ascii").lower()
    except UnicodeError:
        return ""


def from_idna(host: str) -> str:
    try:
        return host.encode("ascii").decode("idna")
    except UnicodeError:
        return host


def parse_url(raw: str | None, *, default_scheme: str = "http") -> ParsedUrl | None:
    """Parse untrusted input. Returns None for anything that is not a plain http(s) URL with a valid host."""
    if not raw or not isinstance(raw, str):
        return None
    s = raw.strip()
    if not s or len(s) > MAX_URL_LENGTH or _CTRL.search(s):
        return None
    if "://" not in s:
        if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", s) and not re.match(r"^[^/]*:\d+(/|$)", s):
            return None  # javascript:, data:, file:, mailto: ...
        s = f"{default_scheme}://{s.lstrip('/')}"
    try:
        parts = urlsplit(s)
        port = parts.port
    except ValueError:
        return None
    if parts.scheme.lower() not in ("http", "https"):
        return None
    host_raw = (parts.hostname or "").strip(".")
    if not host_raw:
        return None
    host = to_idna(host_raw) if not host_raw.isascii() else host_raw.lower()
    if not host or not is_valid_hostname(host):
        return None
    try:
        ipaddress.ip_address(host)
        is_ip = True
    except ValueError:
        is_ip = False
    return ParsedUrl(
        original=raw.strip(), scheme=parts.scheme.lower(), host=host, unicode_host=from_idna(host), port=port,
        path=parts.path or "", query=parts.query, has_userinfo=("@" in parts.netloc), is_ip=is_ip,
    )


def registrable_domain(host: str) -> str:
    host = host.lower().strip(".")
    try:
        ipaddress.ip_address(host)
        return host
    except ValueError:
        pass
    labels = host.split(".")
    if len(labels) <= 2:
        return host
    if ".".join(labels[-2:]) in _MULTI_SUFFIXES and len(labels) >= 3:
        return ".".join(labels[-3:])
    return ".".join(labels[-2:])


def domain_label(host: str) -> str:
    """Second-level label of the registrable domain (e.g. 'acmebank' for login.acmebank.co.uk)."""
    reg = registrable_domain(host)
    parts = reg.split(".")
    if len(parts) >= 3 and ".".join(parts[-2:]) in _MULTI_SUFFIXES:
        return parts[-3]
    return parts[0] if len(parts) >= 2 else reg


def tld_of(host: str) -> str:
    return host.rsplit(".", 1)[-1].lower() if "." in host else ""


def extract_urls(text: str | None, limit: int = 20) -> list[str]:
    if not text:
        return []
    out: list[str] = []
    for m in _URL_IN_TEXT.finditer(text):
        u = m.group(0).rstrip(".,;:!?)")
        if u not in out:
            out.append(u)
        if len(out) >= limit:
            break
    return out
