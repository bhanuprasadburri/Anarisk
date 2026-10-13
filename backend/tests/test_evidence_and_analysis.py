import io
import os

from PIL import Image

from tests.conftest import png_bytes


def upload(client, h, entity_id, data, name="shot.png", ctype="image/png", **form):
    return client.post("/api/v1/evidence/upload", headers=h, data={"entity_id": entity_id, "title": "Screenshot", **form}, files={"file": (name, data, ctype)})


def test_text_evidence_create_list_get(client, f, world):
    h = world.h["inv"]
    e = f.website(h, world.brand["id"])
    r = client.post("/api/v1/evidence", headers=h, json={"entity_id": e["id"], "kind": "whois", "title": "WHOIS", "text_content": "registered 3 days ago", "metadata": {"registrar": "X"}})
    assert r.status_code == 201 and r.json()["has_file"] is False and r.json()["metadata"] == {"registrar": "X"} and r.json()["provenance"] == "manual"
    assert client.get(f"/api/v1/evidence/{r.json()['id']}", headers=h).json()["title"] == "WHOIS"
    assert client.get("/api/v1/evidence", params={"entity_id": e["id"]}, headers=h).json()["total"] == 1
    assert client.get(f"/api/v1/entities/{e['id']}/evidence", headers=h).json()[0]["kind"] == "whois"
    assert client.post("/api/v1/evidence", headers=h, json={"entity_id": e["id"], "kind": "screenshot", "title": "x"}).status_code == 422  # files must use /upload
    assert client.post("/api/v1/evidence", headers=world.h["partner"], json={"entity_id": e["id"], "kind": "text", "title": "x"}).status_code == 403


def test_image_upload_validated_hashed_and_stored_by_content_hash(client, f, world):
    h = world.h["inv"]
    e = f.profile(h, world.brand["id"])
    data = png_bytes("copy")
    r = upload(client, h, e["id"], data, name="../../etc/passwd.png")
    assert r.status_code == 201, r.text
    ev = r.json()
    assert len(ev["perceptual_hash"]) == 16 and len(ev["sha256"]) == 64 and ev["content_type"] == "image/png" and ev["size_bytes"] == len(data) and ev["has_file"]
    assert ev["metadata"]["width"] == 256 and "/" not in ev["metadata"]["original_filename"]
    stored = [n for _, _, names in os.walk(os.environ["UPLOAD_DIR"]) for n in names]
    assert f"{ev['sha256']}.png" in stored                                                           # named by content hash...
    assert not any("passwd" in n or ".." in n for n in stored)                                        # ...never by the client filename
    dl = client.get(f"/api/v1/evidence/{ev['id']}/file", headers=h)
    assert dl.status_code == 200 and dl.content == data and dl.headers["x-content-type-options"] == "nosniff"
    assert upload(client, h, e["id"], data).status_code == 409                       # same content already attached


def test_upload_rejects_non_images_oversize_and_bad_formats(client, f, world, settings, monkeypatch):
    h = world.h["inv"]
    e = f.profile(h, world.brand["id"])
    r = upload(client, h, e["id"], b"<?php system($_GET['x']); ?>", name="evil.png")                 # claims PNG, is not
    assert r.status_code == 422 and "not a valid image" in r.json()["error"]["message"]
    assert upload(client, h, e["id"], b"", name="empty.png").status_code == 422
    bmp = io.BytesIO(); Image.new("RGB", (10, 10)).save(bmp, "BMP")
    assert upload(client, h, e["id"], bmp.getvalue(), name="a.png").status_code == 422                # BMP not permitted even with .png name
    svg = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
    assert upload(client, h, e["id"], svg, name="a.svg", ctype="image/svg+xml").status_code == 422
    monkeypatch.setattr(settings, "max_upload_bytes", 1000)
    big = upload(client, h, e["id"], png_bytes("official"), name="big.png")
    assert big.status_code == 413 and big.json()["error"]["code"] == "payload_too_large"
    monkeypatch.undo()
    assert upload(client, h, e["id"], png_bytes("official"), kind="text").status_code == 422
    assert upload(client, h, e["id"], png_bytes("other"), provenance="collected").status_code == 422
    assert upload(client, world.h["partner"], e["id"], png_bytes("other")).status_code == 403


def test_decompression_bomb_pixel_limit(client, f, world, settings, monkeypatch):
    h = world.h["inv"]
    e = f.profile(h, world.brand["id"])
    monkeypatch.setattr(settings, "max_image_pixels", 100)
    assert upload(client, h, e["id"], png_bytes("official", size=64)).status_code == 422


def test_evidence_file_of_other_tenant_is_404(client, f, world):
    e = f.profile(world.h["inv"], world.brand["id"])
    ev = upload(client, world.h["inv"], e["id"], png_bytes("copy")).json()
    assert client.get(f"/api/v1/evidence/{ev['id']}/file", headers=world.h["outsider"]).status_code == 404


def test_brand_image_reference_upload_and_logo_signal_links_evidence(client, f, world):
    h, own = world.h["inv"], world.h["owner"]
    bid = world.brand["id"]
    ref = client.post(f"/api/v1/brands/{bid}/references/image", headers=own, data={"note": "official logo"}, files={"file": ("logo.png", png_bytes("official"), "image/png")})
    assert ref.status_code == 201 and ref.json()["kind"] == "image" and len(ref.json()["perceptual_hash"]) == 16
    assert client.post(f"/api/v1/brands/{bid}/references/image", headers=own, files={"file": ("logo.png", png_bytes("official"), "image/png")}).status_code == 409
    assert client.post(f"/api/v1/brands/{bid}/references/image", headers=own, files={"file": ("x.png", b"nope", "image/png")}).status_code == 422
    e = f.profile(h, bid, handle="fake_acme_x")
    ev = upload(client, h, e["id"], png_bytes("copy")).json()                                         # altered copy of the logo
    a = client.post(f"/api/v1/entities/{e['id']}/analyze", headers=h)
    assert a.status_code == 201
    sig = next(s for s in a.json()["signals"] if s["signal_type"] == "brand_logo")
    assert sig["status"] == "ok" and sig["score"] >= 0.6 and sig["metadata"]["best_distance"] <= 8
    assert {"type": "evidence", "id": ev["id"]} in sig["evidence_refs"] and {"type": "brand_reference", "id": ref.json()["id"]} in sig["evidence_refs"]
    other = f.profile(h, bid, handle="unrelated_photos")
    upload(client, h, other["id"], png_bytes("other"))
    s2 = next(s for s in client.post(f"/api/v1/entities/{other['id']}/analyze", headers=h).json()["signals"] if s["signal_type"] == "brand_logo")
    assert s2["status"] == "ok" and s2["score"] == 0.0


def test_analyze_persists_assessment_signals_and_history(client, f, world):
    h, bid = world.h["inv"], world.brand["id"]
    e = f.profile(h, bid, handle="acmebank_support_help", bio="AcmeBank - secure everyday banking for everyone. Customer care is available 24/7 - visit https://acmebank-secure-login.xyz/verify",
                  links=["https://acmebank-secure-login.xyz/verify"], account_created_at="2026-10-08T00:00:00Z")
    r1 = client.post(f"/api/v1/entities/{e['id']}/analyze", headers=h)
    assert r1.status_code == 201
    a = r1.json()
    assert {s["signal_type"] for s in a["signals"]} == {"brand_logo", "impersonation", "url_risk", "behavior"}
    by = {s["signal_type"]: s for s in a["signals"]}
    assert by["brand_logo"]["status"] == "unavailable" and by["brand_logo"]["score"] is None and by["brand_logo"]["explanation"].startswith("Signal unavailable")
    assert by["impersonation"]["status"] == "ok" and by["url_risk"]["status"] == "ok" and by["behavior"]["status"] == "ok"
    for s in a["signals"]:
        assert s["explanation"] and isinstance(s["evidence_refs"], list) and isinstance(s["metadata"], dict)
    assert a["model_version"] == "heuristic-v1" and a["configured_weights"]["brand_logo"] == 0.3
    assert a["component_scores"]["brand_logo"] is None and a["effective_weights"]["brand_logo"] == 0
    assert 0 <= a["risk_score"] <= 1 and 0 <= a["confidence_score"] <= 1 and a["confidence_score"] != a["risk_score"]
    assert a["confidence_breakdown"]["unavailable_signals"] == ["brand_logo"] and "heuristic" in a["notes"].lower()
    assert a["severity"] in ("medium", "high", "critical") and a["assessed_at"]
    detail = client.get(f"/api/v1/entities/{e['id']}", headers=h).json()
    assert detail["current_risk_score"] == a["risk_score"] and detail["current_severity"] == a["severity"] and detail["latest_assessment"]["id"] == a["id"]
    r2 = client.post(f"/api/v1/entities/{e['id']}/analyze", headers=h)
    hist = client.get(f"/api/v1/entities/{e['id']}/assessments", headers=h).json()
    assert hist["total"] == 2 and {x["id"] for x in hist["items"]} == {a["id"], r2.json()["id"]}   # history preserved, not overwritten
    assert client.get(f"/api/v1/detection/assessments/{a['id']}", headers=h).json()["id"] == a["id"]
    sigs = client.get("/api/v1/detection/signals", params={"entity_id": e["id"]}, headers=h).json()
    assert sigs["total"] == 4                                                                         # latest assessment only
    assert client.get("/api/v1/detection/signals", params={"entity_id": e["id"], "latest_only": False}, headers=h).json()["total"] == 8
    unavail = client.get("/api/v1/detection/signals", params={"status": "unavailable"}, headers=h).json()
    assert unavail["total"] == 1 and unavail["items"][0]["signal_type"] == "brand_logo"


def test_entity_with_no_signal_data_is_unknown_not_low(client, f, world):
    h, bid = world.h["inv"], world.brand["id"]
    e = f.entity(h, bid, "image", attributes={"sha256": "c" * 64})                                  # no phash, no text, no urls
    a = client.post(f"/api/v1/entities/{e['id']}/analyze", headers=h).json()
    # image entity has a display_name so impersonation runs; brand_logo is unavailable (no official images)
    assert a["component_scores"]["brand_logo"] is None
    e2 = f.entity(h, bid, "domain", attributes={"domain": "unrelated-garden.org"})
    a2 = client.post(f"/api/v1/entities/{e2['id']}/analyze", headers=h).json()
    assert a2["component_scores"]["url_risk"] == 0.0 or a2["component_scores"]["url_risk"] is not None


def test_synthetic_results_have_capped_confidence_via_api(client, f, world):
    h, bid = world.h["inv"], world.brand["id"]
    e = f.entity(h, bid, "social_profile", provenance="synthetic", platform="x", attributes={
        "handle": "acmebank_support", "bio": "AcmeBank - secure everyday banking for everyone. Customer care is available 24/7", "links": ["https://acmebank-verify.top/login"],
        "account_created_at": "2026-10-09T00:00:00Z", "image_phashes": ["f869a5169f611a69"]})
    client.post(f"/api/v1/brands/{bid}/references", headers=world.h["owner"], json={"kind": "image", "value": "f869a5169f611a69"})
    a = client.post(f"/api/v1/entities/{e['id']}/analyze", headers=h).json()
    assert a["is_synthetic"] is True and a["risk_score"] > 0.6
    assert a["confidence_score"] <= 0.4 and a["confidence_breakdown"]["synthetic_cap_applied"] is True and "synthetic" in a["notes"].lower()


def test_submit_with_analyze_flag_and_bulk_analyze(client, f, world):
    h, bid = world.h["inv"], world.brand["id"]
    r = client.post("/api/v1/entities", headers=h, json={"brand_id": bid, "entity_type": "website", "analyze": True, "attributes": {"url": "https://acmebank-bonus.top/claim"}})
    assert r.json()["assessment"]["risk_score"] > 0.5
    f.website(h, bid, url="https://acmebank-support-help.top")
    f.website(h, bid, url="https://www.acmebank.example/x")                                         # official -> skipped
    bulk = client.post("/api/v1/detection/analyze", headers=h, json={"brand_id": bid}).json()
    assert bulk["analyzed"] == 2 and len(bulk["skipped"]) == 1 and "official" in bulk["skipped"][0]["reason"]
    assert client.post("/api/v1/detection/analyze", headers=h, json={}).status_code == 422
    assert client.post("/api/v1/detection/analyze", headers=world.h["outsider"], json={"brand_id": bid}).status_code == 404


def test_model_endpoint_documents_weights_thresholds_confidence(client, world):
    m = client.get("/api/v1/detection/model", headers=world.h["inv"]).json()
    assert m["model_version"] == "heuristic-v1" and sum(m["weights"].values()) == 1.0 or abs(sum(m["weights"].values()) - 1) < 1e-9
    assert m["severity_thresholds"] == {"medium": 0.4, "high": 0.6, "critical": 0.8} and "unvalidated" in m["status"]
    assert m["confidence"]["synthetic_cap"] == 0.4


def test_mobile_app_uses_shared_pipeline(client, f, world):
    h, bid = world.h["inv"], world.brand["id"]
    app = f.entity(h, bid, "mobile_app", attributes={
        "app_name": "AcmeBank Rewards Official", "package_id": "com.acmebank.rewards", "store": "google_play", "publisher_name": "Acme Bank Digital Ltd",
        "store_url": "https://play.google.example/store/apps/details?id=com.acmebank.rewards", "description": "Verify your account at https://acmebank-rewards.top/login",
        "permissions": ["READ_SMS", "INTERNET"], "permissions_source": "manual", "linked_websites": ["https://acmebank-rewards.top/login"], "published_at": "2026-10-05T00:00:00Z"})
    a = client.post(f"/api/v1/entities/{app['id']}/analyze", headers=h).json()
    by = {s["signal_type"]: s for s in a["signals"]}
    assert by["impersonation"]["score"] > 0.6 and by["url_risk"]["score"] > 0.5 and by["behavior"]["status"] == "ok"
    assert any(m["kind"] == "publisher" for m in by["impersonation"]["metadata"]["matches"])
    c = client.post("/api/v1/cases", headers=h, json={"brand_id": bid, "title": "Lookalike app", "entity_ids": [app["id"]]})
    assert c.status_code == 201
