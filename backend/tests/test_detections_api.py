"""Detections feed API: model info, list, detail, re-analyze."""
from __future__ import annotations


def _make_detection(client, world, f):
    """Create and analyze an entity so the feed has at least one row."""
    admin = world.h["admin"]
    ent = f.profile(admin, world.brand["id"])
    r = client.post(f"/api/v1/entities/{ent['id']}/analyze", headers=admin)
    assert r.status_code == 201, r.text
    return ent, r.json()


def test_model_info_includes_rule_descriptions(client, world):
    r = client.get("/api/v1/detection/model", headers=world.h["admin"])
    assert r.status_code == 200
    body = r.json()
    assert body["model_version"]
    assert isinstance(body["weights"], dict) and body["weights"]
    assert isinstance(body["severity_thresholds"], dict)
    assert isinstance(body["confidence"], dict)
    assert isinstance(body["rule_description"], list)
    assert len(body["rule_description"]) >= 4
    for rd in body["rule_description"]:
        assert {"signal_type", "label", "rules"} <= set(rd)
        assert len(rd["rules"]) > 40, "rule descriptions must be substantive"


def test_detections_list_empty_then_populated(client, world, f):
    h = world.h["admin"]
    r = client.get("/api/v1/detections", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"items", "total", "page", "page_size", "pages"}
    assert body["total"] == 0

    ent, assessment = _make_detection(client, world, f)

    r = client.get("/api/v1/detections", headers=h)
    assert r.status_code == 200
    items = r.json()["items"]
    assert r.json()["total"] >= 1
    first = items[0]
    for key in ("id", "entity", "detection_type", "risk_score", "confidence", "severity",
                "status", "signals_summary", "assessed_at", "is_synthetic"):
        assert key in first, f"missing {key}"
    assert first["entity"]["id"] == ent["id"]
    assert first["status"] in ("analyzed", "partial", "unavailable")
    assert isinstance(first["signals_summary"], list)


def test_detections_filters(client, world, f):
    h = world.h["admin"]
    ent, assessment = _make_detection(client, world, f)
    sev = assessment["severity"]

    r = client.get(f"/api/v1/detections?severity={sev}", headers=h)
    assert r.status_code == 200
    assert r.json()["total"] >= 1

    r = client.get("/api/v1/detections?entity_type=social_profile", headers=h)
    assert r.status_code == 200
    assert r.json()["total"] >= 1

    r = client.get("/api/v1/detections?q=no-such-entity-name", headers=h)
    assert r.status_code == 200
    assert r.json()["total"] == 0

    r = client.get(f"/api/v1/detections?brand_id={world.brand['id']}", headers=h)
    assert r.status_code == 200
    assert r.json()["total"] >= 1

    # A sort the feed supports.
    r = client.get("/api/v1/detections?sort=risk_score&order=desc", headers=h)
    assert r.status_code == 200

    # An unsupported status value is rejected by the query validator.
    r = client.get("/api/v1/detections?status=bogus", headers=h)
    assert r.status_code == 422


def test_detection_detail_and_reanalyze(client, world, f):
    h = world.h["admin"]
    _make_detection(client, world, f)

    r = client.get("/api/v1/detections", headers=h)
    det_id = r.json()["items"][0]["id"]

    # The detail is the full assessment behind the flattened row.
    r = client.get(f"/api/v1/detections/{det_id}", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == det_id
    assert "entity_id" in body
    assert isinstance(body["signals"], list) and body["signals"]
    assert "configured_weights" in body and "effective_weights" in body

    # Re-analyze returns a NEW assessment (history is preserved).
    r = client.post(f"/api/v1/detections/{det_id}/re-analyze", headers=h)
    assert r.status_code == 200
    new_id = r.json()["id"]
    assert new_id != det_id, "re-analysis must create a new historical assessment"

    # The original assessment is still retrievable.
    r = client.get(f"/api/v1/detections/{det_id}", headers=h)
    assert r.status_code == 200


def test_detection_unknown_id_404(client, world):
    r = client.get(
        "/api/v1/detections/00000000-0000-0000-0000-000000000000",
        headers=world.h["admin"],
    )
    assert r.status_code == 404


def test_detections_require_auth(client):
    assert client.get("/api/v1/detections").status_code == 401


def test_detections_scoped_to_org(client, world, f):
    """Org B must not see org A's detections."""
    _make_detection(client, world, f)
    r = client.get("/api/v1/detections", headers=world.h["outsider"])
    assert r.status_code == 200
    assert r.json()["total"] == 0
