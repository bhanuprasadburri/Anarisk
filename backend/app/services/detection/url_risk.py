"""Signal C - suspicious URLs and requests: lookalike domains, link patterns and configured risk indicators."""
from __future__ import annotations

import math

from app.models.enums import EvidenceKind, ReferenceKind, SignalStatus, SignalType
from app.services.detection.base import DetectionContext, SignalResult
from app.services.detection.common import entity_urls, official_domains
from app.utils.text import identity_similarity, squash_identity
from app.utils.urls import ParsedUrl, domain_label, parse_url, tld_of


def analyze_url(p: ParsedUrl, ctx: DetectionContext, official: set[str], official_labels: dict[str, str], brand_core: str) -> dict:
    """Return {'score', 'indicators': [...], 'official': bool} for one URL. Pure function of its inputs."""
    s = ctx.settings
    reg = p.registrable_domain
    if reg in official:
        return {"url": p.canonical, "host": p.host, "score": 0.0, "official": True, "indicators": [], "note": "points to an official brand domain"}
    indicators: list[dict] = []

    def add(code: str, weight: float, text: str):
        indicators.append({"code": code, "weight": round(weight, 3), "text": text})

    label_text = domain_label(p.unicode_host)  # unicode form so homoglyphs are visible to the normaliser
    best_sim, best_off = 0.0, None
    for dom, lab in official_labels.items():
        sim, _ = identity_similarity(label_text, lab)
        if sim > best_sim:
            best_sim, best_off = sim, dom
    if best_off and best_sim >= 0.75:
        w = 0.35 + 0.45 * ((best_sim - 0.75) / 0.25)
        same_label = squash_identity(label_text) == squash_identity(official_labels[best_off])
        add("lookalike_domain", w, f"domain '{reg}' " + (f"uses the same name as official '{best_off}' on a different domain/TLD" if same_label else f"looks like official '{best_off}' (similarity {best_sim:.2f})"))
    elif brand_core and len(brand_core) >= 4:
        host_sq = squash_identity(p.unicode_host)
        path_sq = squash_identity(p.path)
        if brand_core in host_sq:
            add("brand_in_host", 0.45, f"brand name appears inside the hostname '{p.host}' of a non-official domain")
        elif brand_core in path_sq:
            add("brand_in_path", 0.25, "brand name appears in the URL path of a non-official domain")
    tld = tld_of(p.host)
    if tld in s.suspicious_tlds:
        add("suspicious_tld", 0.15, f"uses higher-risk TLD '.{tld}' (configured indicator)")
    if p.host.startswith("xn--") or ".xn--" in p.host:
        add("punycode", 0.30, "internationalised (punycode) domain - possible homograph")
    if p.is_ip:
        add("ip_host", 0.40, "host is a raw IP address")
    if p.has_userinfo:
        add("userinfo", 0.40, "URL contains '@' credentials section (hides the real host)")
    if reg in s.url_shorteners or p.host in s.url_shorteners:
        add("shortener", 0.25, "URL shortener hides the final destination")
    extra_labels = max(0, len(p.host.split(".")) - len(reg.split(".")))
    if extra_labels >= 3:
        add("many_subdomains", 0.15, f"{extra_labels} subdomain levels")
    if domain_label(p.host).count("-") >= 2:
        add("hyphenated", 0.10, "domain name contains multiple hyphens")
    if len(p.canonical) > 100:
        add("long_url", 0.05, "unusually long URL")
    haystack = squash_identity(p.unicode_host + p.path + p.query)
    hits = sorted({k for k in s.suspicious_keywords if k in haystack})
    if hits:
        add("suspicious_keywords", min(0.25, 0.10 * len(hits)), "contains request-style keywords: " + ", ".join(hits[:5]))
    if p.scheme == "http":
        add("no_https", 0.05, "not served over HTTPS")
    score = 1.0 - math.prod(1.0 - i["weight"] for i in indicators) if indicators else 0.0
    return {"url": p.canonical, "host": p.host, "score": round(min(score, 1.0), 4), "official": False, "indicators": indicators}


class UrlRiskDetector:
    signal_type = SignalType.URL_RISK

    def run(self, ctx: DetectionContext) -> SignalResult:
        official = official_domains(ctx.references)
        official_labels = {d: domain_label(d) for d in official}
        brand_core = squash_identity(ctx.brand.name)
        parsed, invalid = [], []
        for raw in entity_urls(ctx.entity):
            p = parse_url(raw)
            (parsed if p else invalid).append(p or raw)
        if not parsed:
            why = "no valid URL, domain or link found on this entity" + (f" ({len(invalid)} unparseable value(s) ignored)" if invalid else "")
            return SignalResult.unavailable(self.signal_type, why)
        seen, results = set(), []
        for p in parsed:
            if p.canonical in seen:
                continue
            seen.add(p.canonical)
            results.append(analyze_url(p, ctx, official, official_labels, brand_core))
        results.sort(key=lambda r: r["score"], reverse=True)
        top = results[0]
        refs = [{"type": "evidence", "id": str(ev.id)} for ev in ctx.evidence if ev.kind in (EvidenceKind.URL, EvidenceKind.URL_INSPECTION)][:5]
        if top["official"] and all(r["official"] for r in results):
            expl = "All URLs point to official brand domains; no suspicious link pattern."
        elif top["indicators"]:
            expl = f"Highest-risk URL {top['url']}: " + "; ".join(i["text"] for i in sorted(top["indicators"], key=lambda i: -i["weight"])[:4]) + "."
        else:
            expl = f"Analysed {len(results)} URL(s); no configured risk indicator matched."
        return SignalResult(
            self.signal_type, SignalStatus.OK, top["score"], expl, refs,
            {"urls_analyzed": len(results), "results": results[:10], "unparseable_values": len(invalid), "official_domains_known": sorted(official)},
        )
