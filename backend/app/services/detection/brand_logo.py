"""Signal A - brand and logo similarity via 64-bit perceptual hashing (pHash) against registered official images."""
from __future__ import annotations

from app.models.enums import ReferenceKind, SignalStatus, SignalType
from app.services.detection.base import DetectionContext, SignalResult
from app.services.detection.common import attrs, entity_hashes
from app.utils.images import hamming


def distance_to_score(d: int, near: int, max_d: int) -> float:
    """0 -> 1.0 (exact); 1..near -> 0.95..0.60 (near-duplicate / altered); near..max -> 0.60..0; >= max -> 0."""
    if d <= 0:
        return 1.0
    if d <= near:
        return round(0.95 - 0.35 * (d / near), 4)
    if d >= max_d:
        return 0.0
    return round(0.60 * (1 - (d - near) / (max_d - near)), 4)


class BrandLogoDetector:
    signal_type = SignalType.BRAND_LOGO

    def run(self, ctx: DetectionContext) -> SignalResult:
        s = ctx.settings
        suspects = entity_hashes(ctx.entity, ctx.evidence)
        suspect_sha = {str(attrs(ctx.entity).get("sha256") or "").lower()} | {(e.sha256 or "").lower() for e in ctx.evidence if e.sha256}
        suspect_sha.discard("")
        official = [r for r in ctx.references if r.kind == ReferenceKind.IMAGE]
        if not suspects and not suspect_sha:
            return SignalResult.unavailable(self.signal_type, "no image data (perceptual hash or uploaded image) for this entity")
        if not official:
            return SignalResult.unavailable(self.signal_type, "the brand has no registered official images to compare against")

        matches = []
        for r in official:
            if r.sha256 and r.sha256.lower() in suspect_sha:
                matches.append({"reference_id": str(r.id), "distance": 0, "exact_file_match": True, "suspect_hash": None, "evidence_id": None, "reference_note": r.note})
            if r.perceptual_hash:
                for sus in suspects:
                    d = hamming(sus["hash"], r.perceptual_hash)
                    matches.append({"reference_id": str(r.id), "distance": d, "exact_file_match": False, "suspect_hash": sus["hash"], "evidence_id": sus["evidence_id"], "reference_note": r.note})
        if not matches:
            return SignalResult.unavailable(self.signal_type, "official images have no perceptual hash and no byte-identical match was found")
        matches.sort(key=lambda m: m["distance"])
        best = matches[0]
        score = distance_to_score(best["distance"], s.image_hash_near_duplicate, s.image_hash_max_distance)
        refs = [{"type": "brand_reference", "id": best["reference_id"]}]
        if best["evidence_id"]:
            refs.append({"type": "evidence", "id": best["evidence_id"]})
        label = best["reference_note"] or "official brand image"
        if best["exact_file_match"]:
            expl = f"Image is a byte-identical copy of the registered official image ({label})."
        elif best["distance"] == 0:
            expl = f"Image has an identical perceptual hash to the official image ({label}): reused visual."
        elif score >= 0.5:
            expl = f"Image is visually very similar to the official image ({label}): perceptual-hash distance {best['distance']}/64 - likely reused or lightly altered."
        elif score > 0:
            expl = f"Image shows weak visual similarity to the official image ({label}): distance {best['distance']}/64."
        else:
            expl = f"No visual match: closest official image is {best['distance']}/64 bits away (threshold {s.image_hash_max_distance})."
        return SignalResult(
            self.signal_type, SignalStatus.OK, score, expl, refs,
            {"best_distance": best["distance"], "similarity": round(1 - best["distance"] / 64, 4), "hash_bits": 64,
             "compared_suspect_images": len(suspects), "compared_official_images": len(official), "top_matches": matches[:5]},
        )
