"""Synthetic sample-listing connector. Produces clearly labelled FAKE lookalike entities for demos and tests.
Nothing here is observed from any real platform."""
from __future__ import annotations

import re
from typing import Any

from app.models import Brand
from app.models.enums import EntityType, SourceKind
from app.services.connectors.base import SourceConnector
from app.services.ingestion import NormalizedEntity, normalize_submission


class SampleListingsConnector(SourceConnector):
    key = "sample-listings"
    name = "Synthetic sample listings (demo)"
    kind = SourceKind.SYNTHETIC
    description = "Generates SYNTHETIC lookalike app/profile/domain listings for the selected brand. Not real data."
    live = False

    def is_configured(self) -> bool:
        return True

    def collect(self, brand: Brand, query: dict[str, Any]) -> list[NormalizedEntity]:
        slug = re.sub(r"[^a-z0-9]", "", brand.name.lower()) or "brand"
        n = brand.name
        items = [
            normalize_submission(EntityType.MOBILE_APP, f"{n} Rewards Official", "google_play", None, {
                "app_name": f"{n} Rewards Official", "package_id": f"com.{slug}rewards.official", "store": "google_play",
                "publisher_name": f"{n} Digital Services Ltd", "store_url": f"https://play.google.example/store/apps/details?id=com.{slug}rewards.official",
                "description": f"[SYNTHETIC SAMPLE] Claim your {n} rewards now. Login to verify your account at https://{slug}-rewards-claim.xyz/login",
                "permissions": ["READ_SMS", "READ_CONTACTS", "SYSTEM_ALERT_WINDOW"], "permissions_source": "manual",
                "linked_websites": [f"https://{slug}-rewards-claim.xyz/login"],
            }),
            normalize_submission(EntityType.SOCIAL_PROFILE, f"{n} Support Team", "x", None, {
                "handle": f"{slug}_support_help", "bio": f"[SYNTHETIC SAMPLE] Official support for {n}. DM us to resolve account issues quickly.",
                "links": [f"https://{slug}-rewards-claim.xyz/login"],
            }),
            normalize_submission(EntityType.DOMAIN, None, None, None, {"domain": f"{slug}-rewards-claim.xyz"}),
        ]
        return items
