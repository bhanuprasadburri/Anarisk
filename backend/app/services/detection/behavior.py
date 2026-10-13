"""Signal D - account age, velocity and coordination. Components with no input data are *unavailable*, never zero."""
from __future__ import annotations

from app.models.enums import SignalStatus, SignalType
from app.services.detection.base import DetectionContext, SignalResult
from app.services.detection.common import (
    attrs, entity_created_at, entity_hashes, entity_bio, linked_registrable_domains, official_domains,
    pair_indicators, post_timestamps,
)
from app.models.enums import RelationshipType

COMPONENT_WEIGHTS = {"account_age": 0.4, "velocity": 0.3, "coordination": 0.3}
# probability-style contribution per coordination indicator type
COORD_P = {
    RelationshipType.SHARES_IMAGE: 0.50, RelationshipType.SIMILAR_IDENTITY: 0.40, RelationshipType.SHARES_DOMAIN: 0.40,
    RelationshipType.SAME_INFRASTRUCTURE: 0.50, RelationshipType.COORDINATED_BEHAVIOR: 0.60,
}


def age_score(age_days: float, thresholds: list[int]) -> float:
    for limit, sc in zip(thresholds, (1.0, 0.7, 0.4, 0.15)):
        if age_days < limit:
            return sc
    return 0.0


class BehaviorDetector:
    signal_type = SignalType.BEHAVIOR

    def run(self, ctx: DetectionContext) -> SignalResult:
        s, e, now = ctx.settings, ctx.entity, ctx.now
        a = attrs(e)
        comps: dict[str, dict] = {}
        notes: list[str] = []

        # --- account age ---
        created, key = entity_created_at(e)
        if created:
            age = max(0.0, (now - created).total_seconds() / 86400)
            sc = age_score(age, s.account_age_days_thresholds)
            comps["account_age"] = {"score": sc, "available": True, "age_days": round(age, 1), "source_field": key}
            notes.append(f"created {age:.0f} day(s) ago")
        else:
            comps["account_age"] = {"score": None, "available": False, "reason": "no creation/registration date supplied"}

        # --- velocity ---
        posts = post_timestamps(e)
        followers = a.get("followers_count")
        vel_parts, vel_meta = [], {}
        if len(posts) >= s.min_posts_for_velocity:
            span_days = max((posts[-1] - posts[0]).total_seconds() / 86400, 1 / 24)
            rate = len(posts) / span_days
            vel_parts.append(min(1.0, rate / s.velocity_posts_per_day_saturation))
            vel_meta.update(posts_observed=len(posts), posts_per_day=round(rate, 2))
            notes.append(f"{rate:.1f} posts/day")
        if created and followers is not None:
            age_d = max((now - created).total_seconds() / 86400, 1.0)
            growth = followers / age_d
            vel_parts.append(min(1.0, growth / s.follower_growth_per_day_saturation))
            vel_meta.update(followers_count=followers, followers_per_day=round(growth, 1))
            notes.append(f"{growth:.0f} followers/day")
        if vel_parts:
            comps["velocity"] = {"score": round(max(vel_parts), 4), "available": True, **vel_meta}
        else:
            comps["velocity"] = {"score": None, "available": False, "reason": f"needs >= {s.min_posts_for_velocity} post timestamps, or followers_count with a creation date"}

        # --- coordination ---
        has_indicator_data = bool(entity_hashes(e, ctx.evidence) or entity_bio(e) or posts or linked_registrable_domains(e) or a.get("hosting"))
        if ctx.peers and has_indicator_data:
            official = official_domains(ctx.references)
            by_kind: dict[RelationshipType, list[str]] = {}
            for peer in ctx.peers:
                for ind in pair_indicators(e, peer, s, official=official, a_ev=ctx.evidence):
                    by_kind.setdefault(ind.kind, []).append(str(peer.id))
            p_notfired = 1.0
            fired = {}
            for kind, peers in by_kind.items():
                p = COORD_P[kind] + (0.10 if len(set(peers)) >= 3 else 0.0)
                p_notfired *= 1 - min(p, 0.95)
                fired[kind.value] = sorted(set(peers))
            repeat = ctx.collection_count >= 3
            if repeat:
                p_notfired *= 0.9
            comps["coordination"] = {
                "score": round(1 - p_notfired, 4), "available": True, "peers_compared": len(ctx.peers),
                "shared_indicators": fired, "repeated_submissions": ctx.collection_count if repeat else 0,
            }
            if fired:
                notes.append("shares " + ", ".join(sorted(fired)) + f" with {len({p for v in fired.values() for p in v})} other entit(y/ies)")
        else:
            why = "no other monitored entities for this brand to compare against" if not ctx.peers else "entity has no images, bio, links, hosting or timestamps to compare"
            comps["coordination"] = {"score": None, "available": False, "reason": why}

        avail = {k: v for k, v in comps.items() if v["available"]}
        if not avail:
            return SignalResult.unavailable(self.signal_type, "no timestamps, activity data or peer entities available", components=comps)
        tw = sum(COMPONENT_WEIGHTS[k] for k in avail)
        score = round(sum(COMPONENT_WEIGHTS[k] * v["score"] for k, v in avail.items()) / tw, 4)
        missing = [k for k, v in comps.items() if not v["available"]]
        expl = "Behavioural indicators: " + ("; ".join(notes) if notes else "no concerning pattern observed") + "."
        if missing:
            expl += " Not assessed (no data): " + ", ".join(missing) + "."
        refs = [{"type": "entity", "id": pid} for v in comps.get("coordination", {}).get("shared_indicators", {}).values() for pid in v]
        uniq_refs = [dict(t) for t in {tuple(sorted(r.items())) for r in refs}]
        return SignalResult(self.signal_type, SignalStatus.OK, score, expl, uniq_refs[:20],
                            {"components": comps, "component_weights": COMPONENT_WEIGHTS, "unavailable_components": missing})
