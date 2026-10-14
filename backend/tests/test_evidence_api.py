"""Evidence API: create/upload, detail, list filters, verify, link/unlink, CSV export, delete."""
from __future__ import annotations

import uuid

from tests.conftest import png_bytes


def _entity(world, f):
    return f.profile(world.h["owner"], world.brand["id"], handle=f"ev_{uuid.uuid4().hex[:8]}")


def _case(client, world, f, ent):
    r = client.post(
        "/api/v1/cases",
        headers=world.h["inv"],
        json={"brand_id": world.brand["id"], "title": "Evidence case", "entity_ids": [ent["id"]]},
    )
    assert r.status_code == 201, r.text
    return r.json()


def test_create_text_evidence_and_get_detail(client, world, f):
    h = world.h["inv"]
    ent = _entity(world, f)

    r = client.post(
        "/api/v1/evidence",
        headers=h,
        json={
            "entity_id": ent["id"],
            "kind": "text",
            "title": "Bio capture",
            "description": "from takedown review",
            "text_content": "Suspicious text captured from profile bio",
        },
    )
    assert r.status_code == 201, r.text
    ev = r.json()
    assert ev["kind"] == "text"
    assert ev["sha256"]  # sha256 of the text is computed at creation
    assert ev["verification_status"] == "pending"  # not 'verified' until the bytes are re-hashed
    assert ev["case_ids"] == []
    assert ev["entity"]["id"] == ent["id"]

    # Detail.
    r = client.get(f"/api/v1/evidence/{ev['id']}", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == ev["id"]
    assert body["verification_status"] == "pending"
    assert body["entity"]["id"] == ent["id"]

    # List filters: entity, kind, verification_status, q.
    r = client.get(f"/api/v1/evidence?entity_id={ent['id']}", headers=h)
    assert r.status_code == 200 and r.json()["total"] >= 1
    r = client.get("/api/v1/evidence?kind=text", headers=h)
    assert r.status_code == 200 and r.json()["total"] >= 1
    r = client.get("/api/v1/evidence?verification_status=pending", headers=h)
    assert r.status_code == 200 and r.json()["total"] >= 1
    r = client.get("/api/v1/evidence?q=Bio", headers=h)
    assert r.status_code == 200 and r.json()["total"] >= 1


def test_upload_png_evidence_and_download(client, world, f):
    h = world.h["inv"]
    ent = _entity(world, f)

    r = client.post(
        "/api/v1/evidence/upload",
        headers=h,
        data={"entity_id": ent["id"], "title": "Fake login screen"},
        files={"file": ("screen.png", png_bytes(), "image/png")},
    )
    assert r.status_code == 201, r.text
    ev = r.json()
    assert ev["kind"] == "screenshot"  # default kind for uploads
    assert ev["has_file"] is True
    assert ev["file_name"] == "screen.png"
    assert ev["verification_status"] == "verified"  # uploads are verified at rest
    assert ev["size_bytes"] > 0 and ev["perceptual_hash"]

    # File download works and is served as an image.
    r = client.get(f"/api/v1/evidence/{ev['id']}/file", headers=h)
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("image/")
    assert len(r.content) > 0

    # Uploading identical bytes to the same entity again -> 409 duplicate_evidence.
    r = client.post(
        "/api/v1/evidence/upload",
        headers=h,
        data={"entity_id": ent["id"], "title": "Same bytes again"},
        files={"file": ("screen.png", png_bytes(), "image/png")},
    )
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "duplicate_evidence"


def test_verify_endpoint_marks_text_verified(client, world, f):
    h = world.h["inv"]
    ent = _entity(world, f)
    ev = client.post(
        "/api/v1/evidence",
        headers=h,
        json={"entity_id": ent["id"], "kind": "text", "title": "to be verified", "text_content": "content that will be re-hashed"},
    ).json()
    assert ev["verification_status"] == "pending"

    r = client.post(f"/api/v1/evidence/{ev['id']}/verify", headers=h, json={})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["matches"] is True
    assert body["sha256"] == body["stored_sha256"]

    # The record now reports verified.
    r = client.get(f"/api/v1/evidence/{ev['id']}", headers=h)
    assert r.json()["verification_status"] == "verified"


def test_link_and_unlink_evidence_to_case(client, world, f):
    h = world.h["inv"]
    ent = _entity(world, f)
    case1 = _case(client, world, f, ent)
    case2 = _case(client, world, f, ent)

    # Standalone evidence (no case).
    r = client.post(
        "/api/v1/evidence",
        headers=h,
        json={"entity_id": ent["id"], "kind": "text", "title": "standalone", "text_content": "not yet linked"},
    )
    assert r.status_code == 201, r.text
    ev = r.json()
    assert ev["case_ids"] == []

    # Link to case1.
    r = client.post(f"/api/v1/evidence/{ev['id']}/link", headers=h, json={"case_id": case1["id"]})
    assert r.status_code == 200, r.text
    assert case1["id"] in r.json()["case_ids"]

    # Duplicate link is an idempotent no-op success.
    r = client.post(f"/api/v1/evidence/{ev['id']}/link", headers=h, json={"case_id": case1["id"]})
    assert r.status_code == 200
    assert r.json()["case_ids"].count(case1["id"]) == 1

    # Link to case2 as well.
    r = client.post(f"/api/v1/evidence/{ev['id']}/link", headers=h, json={"case_id": case2["id"]})
    assert r.status_code == 200
    assert len(r.json()["case_ids"]) == 2

    # Unlink case1 (204, no body); case2 link remains.
    r = client.delete(f"/api/v1/evidence/{ev['id']}/link/{case1['id']}", headers=h)
    assert r.status_code == 204
    r = client.get(f"/api/v1/evidence/{ev['id']}", headers=h)
    assert r.json()["case_ids"] == [case2["id"]]


def test_evidence_list_by_case_includes_entity_linked(client, world, f):
    h = world.h["inv"]
    ent = _entity(world, f)
    case = _case(client, world, f, ent)
    client.post(
        "/api/v1/evidence",
        headers=h,
        json={"entity_id": ent["id"], "kind": "text", "title": "case-scoped", "text_content": "attached to the case entity"},
    )
    r = client.get(f"/api/v1/evidence?case_id={case['id']}", headers=h)
    assert r.status_code == 200
    assert r.json()["total"] >= 1


def test_evidence_csv_export(client, world, f):
    h = world.h["inv"]
    ent = _entity(world, f)
    client.post(
        "/api/v1/evidence",
        headers=h,
        json={"entity_id": ent["id"], "kind": "text", "title": "exported row", "text_content": "row content"},
    )
    r = client.get("/api/v1/evidence/export/csv", headers=h)
    assert r.status_code == 200
    assert "text/csv" in r.headers.get("content-type", "")
    assert "attachment" in r.headers.get("content-disposition", "")
    assert len(r.text.splitlines()) >= 2  # header + at least one row


def test_delete_evidence_admin_and_investigator(client, world, f):
    admin, inv = world.h["admin"], world.h["inv"]
    ent = _entity(world, f)
    ev = client.post(
        "/api/v1/evidence",
        headers=inv,
        json={"entity_id": ent["id"], "kind": "text", "title": "delete me", "text_content": "to be deleted"},
    ).json()

    # Investigator may delete.
    r = client.delete(f"/api/v1/evidence/{ev['id']}", headers=inv)
    assert r.status_code == 204
    r = client.get(f"/api/v1/evidence/{ev['id']}", headers=admin)
    assert r.status_code == 404

    # Admin may delete too.
    ev2 = client.post(
        "/api/v1/evidence",
        headers=inv,
        json={"entity_id": ent["id"], "kind": "text", "title": "delete me 2", "text_content": "to be deleted as well"},
    ).json()
    r = client.delete(f"/api/v1/evidence/{ev2['id']}", headers=admin)
    assert r.status_code == 204


def test_delete_evidence_partner_forbidden(client, world, f):
    ent = _entity(world, f)
    ev = client.post(
        "/api/v1/evidence",
        headers=world.h["inv"],
        json={"entity_id": ent["id"], "kind": "text", "title": "partner delete attempt", "text_content": "kept"},
    ).json()
    # Partner has evidence:read but not delete.
    r = client.delete(f"/api/v1/evidence/{ev['id']}", headers=world.h["partner"])
    assert r.status_code == 403


def test_evidence_requires_auth(client):
    assert client.get("/api/v1/evidence").status_code == 401
    assert client.get("/api/v1/evidence/export/csv").status_code == 401
    assert client.post("/api/v1/evidence", json={}).status_code == 401


def test_evidence_not_found(client, world):
    r = client.get("/api/v1/evidence/00000000-0000-0000-0000-000000000000", headers=world.h["inv"])
    assert r.status_code == 404
