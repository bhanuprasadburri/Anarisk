"""Seed SYNTHETIC demonstration data: users, an organization, a fake brand, lookalike entities, evidence, a linked
campaign and a case. Everything is flagged provenance=synthetic and the brand is flagged is_synthetic.

    python -m scripts.seed            # idempotent; refuses to run when ENVIRONMENT=production
"""
from __future__ import annotations

import io
import sys
from datetime import UTC, datetime, timedelta

from PIL import Image, ImageDraw
from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import get_sessionmaker
from app.models import Organization, User
from app.models.enums import CaseStatus, EntityType, EvidenceKind, PartnerType, Provenance, ReferenceKind, UserRole
from app.schemas.brand import BrandCreate, ReferenceCreate
from app.schemas.case import CaseStatusUpdate, EscalateRequest
from app.schemas.entity import EntitySubmit
from app.schemas.evidence import EvidenceCreate
from app.services import analysis, brands, cases, evidence, graph, ingestion
from app.services.connectors import get_connector

DEMO_PASSWORD = "Demo-Passw0rd!"  # DEMO ONLY - local development accounts


def logo(variant: str) -> bytes:
    im = Image.new("RGB", (256, 256), "white")
    d = ImageDraw.Draw(im)
    if variant in ("official", "copy"):
        c = (10, 40, 120) if variant == "official" else (20, 50, 130)
        d.ellipse((30, 30, 226, 226), fill=c)
        d.polygon([(80, 190), (128, 60), (176, 190), (150, 190), (128, 120), (106, 190)], fill="white")
        d.rectangle((100, 150, 156, 164), fill="white")
        if variant == "copy":
            d.rectangle((0, 0, 255, 6), fill=(20, 50, 130))  # slight alteration
    else:
        for i in range(0, 256, 32):
            d.rectangle((i, 0, i + 15, 255), fill=(200, 30, 30))
        d.ellipse((90, 90, 170, 170), fill="black")
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


def main() -> None:
    s = get_settings()
    if s.environment == "production":
        sys.exit("Refusing to seed synthetic data when ENVIRONMENT=production")
    db = get_sessionmaker()()
    if db.scalar(select(Organization).where(Organization.slug == "demo-security-team")):
        print("Seed data already present - nothing to do.")
        return
    org = Organization(name="Demo Security Team (SYNTHETIC)", slug="demo-security-team", description="Synthetic demonstration organization")
    other = Organization(name="Other Org (SYNTHETIC)", slug="other-org", description="Used to demonstrate tenant isolation")
    db.add_all([org, other])
    db.flush()
    def mk(email, name, role, o, pw=DEMO_PASSWORD):
        u = User(email=email, full_name=name, role=role, organization_id=o.id if o else None, hashed_password=hash_password(pw))
        db.add(u)
        return u
    admin = mk(s.bootstrap_admin_email, "Platform Admin", UserRole.ADMIN, None, s.bootstrap_admin_password)
    inv = mk("investigator@nimbus.example", "Ira Investigator", UserRole.INVESTIGATOR, org)
    inv2 = mk("investigator2@nimbus.example", "Ivan Analyst", UserRole.INVESTIGATOR, org)
    owner = mk("owner@nimbus.example", "Olive BrandOwner", UserRole.BRAND_OWNER, org)
    partner = mk("partner@nimbus.example", "Pat Legal-Partner", UserRole.PARTNER, org)
    mk("outsider@nimbus.example", "Otto Outsider", UserRole.INVESTIGATOR, other)
    db.commit()

    brand = brands.create_brand(db, admin, BrandCreate(organization_id=org.id, name="AcmeBank", slug="acmebank", description="Synthetic retail bank used for demos. Not a real company."))
    brand.is_synthetic = True
    db.commit()
    for kind, value, platform in [(ReferenceKind.NAME, "AcmeBank", None), (ReferenceKind.HANDLE, "acmebank", "x"), (ReferenceKind.DOMAIN, "acmebank.example", None),
                                  (ReferenceKind.APP_PACKAGE, "com.acmebank.mobile", None), (ReferenceKind.PUBLISHER, "AcmeBank Ltd", None),
                                  (ReferenceKind.BIO, "AcmeBank - secure everyday banking for everyone. Customer care is available 24/7 through the official app.", None)]:
        brands.add_reference(db, admin, brand.id, ReferenceCreate(kind=kind, value=value, platform=platform, provenance=Provenance.SYNTHETIC))
    brands.add_image_reference(db, admin, brand.id, logo("official"), "AcmeBank official logo (synthetic)", Provenance.SYNTHETIC)

    now = datetime.now(UTC)
    def submit(etype, **kw):
        e, _, _ = ingestion.submit_entity(db, inv, EntitySubmit(brand_id=brand.id, entity_type=etype, provenance=Provenance.SYNTHETIC, **kw))
        return e

    fake_profile = submit(EntityType.SOCIAL_PROFILE, platform="x", display_name="AcmeBank Support Team", attributes={
        "handle": "acmebank_support_help", "bio": "AcmeBank - secure everyday banking for everyone. Customer care is available 24/7 - DM us or visit https://acmebank-secure-login.xyz/verify",
        "followers_count": 18000, "account_created_at": (now - timedelta(days=6)).isoformat(),
        "post_timestamps": [(now - timedelta(minutes=5 * i)).isoformat() for i in range(1, 40)],
        "links": ["https://acmebank-secure-login.xyz/verify"]})
    second_profile = submit(EntityType.SOCIAL_PROFILE, platform="instagram", display_name="Acme Bank Official", attributes={
        "handle": "acme.bank.official", "bio": "Claim your AcmeBank reward today! https://acmebank-secure-login.xyz/verify", "followers_count": 900,
        "account_created_at": (now - timedelta(days=12)).isoformat(),
        "post_timestamps": [(now - timedelta(minutes=5 * i, seconds=20)).isoformat() for i in range(1, 25)],
        "links": ["https://acmebank-secure-login.xyz/verify"]})
    domain = submit(EntityType.WEBSITE, attributes={"url": "https://acmebank-secure-login.xyz/verify", "page_title": "AcmeBank - Verify your account",
                                                    "registered_at": (now - timedelta(days=9)).isoformat(), "hosting": {"ip": "203.0.113.7", "nameservers": ["ns1.cheap-dns.example"]}})
    app_ = submit(EntityType.MOBILE_APP, display_name="AcmeBank Rewards Official", attributes={
        "app_name": "AcmeBank Rewards Official", "package_id": "com.acmebank.rewards.official", "store": "google_play", "publisher_name": "Acme Bank Digital Ltd",
        "store_url": "https://play.google.example/store/apps/details?id=com.acmebank.rewards.official",
        "description": "AcmeBank - secure everyday banking for everyone. Customer care is available 24/7. Verify your account at https://acmebank-secure-login.xyz/verify",
        "permissions": ["READ_SMS", "READ_CONTACTS", "SYSTEM_ALERT_WINDOW"], "permissions_source": "manual", "linked_websites": ["https://acmebank-secure-login.xyz/verify"],
        "published_at": (now - timedelta(days=4)).isoformat()})
    benign = submit(EntityType.SOCIAL_PROFILE, platform="x", display_name="Bank Fans Weekly", attributes={
        "handle": "bankfans_weekly", "bio": "A community newsletter about retail banking news.", "followers_count": 1200, "account_created_at": (now - timedelta(days=1500)).isoformat()})

    for ent, kind, img in [(fake_profile, EvidenceKind.SCREENSHOT, "copy"), (app_, EvidenceKind.SCREENSHOT, "copy"), (benign, EvidenceKind.IMAGE, "other")]:
        evidence.upload_image_evidence(db, inv, ent.id, logo(img), title=f"Profile image / icon ({img}) - synthetic", description="Synthetic sample image", kind=kind,
                                       provenance=Provenance.SYNTHETIC, original_filename=f"{img}.png")
    evidence.create_evidence(db, inv, EvidenceCreate(entity_id=domain.id, kind=EvidenceKind.WHOIS, title="WHOIS excerpt (synthetic)", provenance=Provenance.SYNTHETIC,
                                                     text_content="Registered 9 days ago via a low-cost registrar; privacy protection enabled. (synthetic sample)"))
    evidence.create_evidence(db, inv, EvidenceCreate(entity_id=second_profile.id, kind=EvidenceKind.URL, title="Link in bio (synthetic)", provenance=Provenance.SYNTHETIC,
                                                     source_url="https://acmebank-secure-login.xyz/verify"))
    # also exercise the synthetic sample connector path
    get_connector("sample-listings")
    graph.discover_relationships(db, inv, brand.id)
    for e in (fake_profile, second_profile, domain, app_, benign):
        analysis.analyze_entity(db, inv, db.get(type(e), e.id))
    case, _ = cases.create_case_from_cluster(db, inv, [fake_profile.id], "Campaign: AcmeBank credential-phishing cluster (synthetic)")
    cases.change_status(db, inv, case.id, CaseStatusUpdate(status=CaseStatus.TRIAGED))
    cases.change_status(db, inv, case.id, CaseStatusUpdate(status=CaseStatus.UNDER_REVIEW, comment="Evidence reviewed: shared domain, copied logo and bio."))
    cases.assign(db, inv, case.id, inv.id, "Taking ownership")
    cases.escalate(db, inv, case.id, EscalateRequest(partner_type=PartnerType.LEGAL, partner_contact="legal@acmebank.example",
                                                      reason="Impersonation with credential-harvesting link; request legal review (handoff recorded only).",
                                                      requested_action="Review for takedown request"))
    print("Seed complete (all data is SYNTHETIC).")
    print(f"  admin:        {s.bootstrap_admin_email} / (BOOTSTRAP_ADMIN_PASSWORD)")
    print(f"  demo users:   investigator@ / investigator2@ / owner@ / partner@ / outsider@nimbus.example  password: {DEMO_PASSWORD}")
    print(f"  case:         {case.case_number}")


if __name__ == "__main__":
    main()
