"""Case lifecycle: status transitions, PATCH with optimistic concurrency, admin-only DELETE, evidence embed."""
from __future__ import annotations

import uuid


def _create_case(client, world, f, title="Lifecycle case"):
    ent = f.profile(world.h["owner"], world.brand["id"], handle=f"case_{uuid.uuid4().hex[:8]}")
    r = client.post(
        "/api/v1/cases",
        headers=world.h["inv"],
        json={"brand_id": world.brand["id"], "title": title, "entity_ids": [ent["id"]]},
    )
    assert r.status_code == 201, r.text
    return r.json(), ent


def test_status_workflow_detected_to_resolved(client, world, f):
    h = world.h["inv"]
    case, _ = _create_case(client, world, f)
    assert case["status"] == "detected"

    # detected -> triaged.
    r = client.post(f"/api/v1/cases/{case['id']}/status", headers=h, json={"status": "triaged"})
    assert r.status_code == 200, r.text
    updated = r.json()
    assert updated["status"] == "triaged"
    assert updated["version"] == case["version"] + 1

    # triaged -> under_review.
    r = client.post(f"/api/v1/cases/{case['id']}/status", headers=h, json={"status": "under_review"})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "under_review"

    # Assign an owner (UNDER_REVIEW -> ASSIGNED automatically).
    r = client.post(
        f"/api/v1/cases/{case['id']}/assign",
        headers=h,
        json={"assignee_id": str(world.users["inv"].id)},
    )
    assert r.status_code == 200, r.text
    updated = r.json()
    assert updated["status"] == "assigned"
    assert updated["assigned_to"]["id"] == str(world.users["inv"].id)

    # assigned -> under_review.
    r = client.post(f"/api/v1/cases/{case['id']}/status", headers=h, json={"status": "under_review"})
    assert r.status_code == 200, r.text

    # under_review -> resolved requires outcome + summary.
    r = client.post(
        f"/api/v1/cases/{case['id']}/status",
        headers=h,
        json={
            "status": "resolved",
            "resolution_outcome": "false_positive",
            "resolution_summary": "Benign account after manual review",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "resolved"
    assert body["resolution_outcome"] == "false_positive"
    assert body["resolved_at"] is not None

    # Reopen: RESOLVED -> UNDER_REVIEW needs case:reopen (administrators have it).
    r = client.post(
        f"/api/v1/cases/{case['id']}/status",
        headers=world.h["admin"],
        json={"status": "under_review", "comment": "reopening after new evidence"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "under_review"


def test_status_invalid_transition_409(client, world, f):
    h = world.h["inv"]
    case, _ = _create_case(client, world, f)
    # detected -> resolved is not a valid transition.
    r = client.post(
        f"/api/v1/cases/{case['id']}/status",
        headers=h,
        json={"status": "resolved", "resolution_outcome": "false_positive", "resolution_summary": "shortcut attempt"},
    )
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "invalid_transition"


def test_status_expected_status_conflict(client, world, f):
    h = world.h["inv"]
    case, _ = _create_case(client, world, f)
    r = client.post(
        f"/api/v1/cases/{case['id']}/status",
        headers=h,
        json={"status": "triaged", "expected_status": "under_review"},
    )
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "status_conflict"

    # Same status again -> no_change.
    r = client.post(f"/api/v1/cases/{case['id']}/status", headers=h, json={"status": "detected"})
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "no_change"


def test_patch_case_severity_and_version_conflict(client, world, f):
    h = world.h["inv"]
    case, _ = _create_case(client, world, f)

    # First patch succeeds and bumps the version.
    r = client.patch(
        f"/api/v1/cases/{case['id']}",
        headers=h,
        json={"severity": "critical", "title": "Retitled after triage", "version": case["version"]},
    )
    assert r.status_code == 200, r.text
    updated = r.json()
    assert updated["severity"] == "critical"
    assert updated["title"] == "Retitled after triage"
    assert updated["version"] == case["version"] + 1

    # Stale version -> 409 version_conflict.
    r = client.patch(
        f"/api/v1/cases/{case['id']}",
        headers=h,
        json={"severity": "low", "version": case["version"]},
    )
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "version_conflict"

    # Without a version the patch is allowed (last-write-wins).
    r = client.patch(f"/api/v1/cases/{case['id']}", headers=h, json={"summary": "updated summary"})
    assert r.status_code == 200
    assert r.json()["summary"] == "updated summary"


def test_patch_case_permissions(client, world, f):
    case, _ = _create_case(client, world, f)
    # Partner lacks case:triage.
    r = client.patch(f"/api/v1/cases/{case['id']}", headers=world.h["partner"], json={"severity": "low"})
    assert r.status_code == 403
    # Outsider (different org) cannot see the case.
    r = client.patch(f"/api/v1/cases/{case['id']}", headers=world.h["outsider"], json={"severity": "low"})
    assert r.status_code in (403, 404)
    # Unauthenticated.
    r = client.patch(f"/api/v1/cases/{case['id']}", json={"severity": "low"})
    assert r.status_code == 401


def test_delete_case_admin_only(client, world, f):
    case, ent = _create_case(client, world, f)
    # Investigator cannot delete.
    r = client.delete(f"/api/v1/cases/{case['id']}", headers=world.h["inv"])
    assert r.status_code == 403

    # Admin can delete.
    r = client.delete(f"/api/v1/cases/{case['id']}", headers=world.h["admin"])
    assert r.status_code == 204

    # Case is gone (the entity is kept).
    r = client.get(f"/api/v1/cases/{case['id']}", headers=world.h["inv"])
    assert r.status_code == 404
    r = client.get(f"/api/v1/entities/{ent['id']}", headers=world.h["inv"])
    assert r.status_code == 200


def test_delete_unknown_case_404(client, world):
    r = client.delete("/api/v1/cases/00000000-0000-0000-0000-000000000000", headers=world.h["admin"])
    assert r.status_code == 404


def test_case_detail_includes_linked_evidence(client, world, f):
    h = world.h["inv"]
    case, ent = _create_case(client, world, f)

    # Entity-scoped evidence shows up under entities[].evidence.
    ev = client.post(
        "/api/v1/evidence",
        headers=h,
        json={"entity_id": ent["id"], "kind": "text", "title": "entity proof", "text_content": "attached proof"},
    ).json()
    # Explicitly linked evidence shows up under evidence[].
    r = client.post(f"/api/v1/evidence/{ev['id']}/link", headers=h, json={"case_id": case["id"]})
    assert r.status_code == 200, r.text

    r = client.get(f"/api/v1/cases/{case['id']}", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body["evidence"], list)
    assert len(body["evidence"]) == 1
    linked = body["evidence"][0]
    assert linked["id"] == ev["id"]
    assert linked["role"] == "linked"
    assert "verification_status" in linked
    assert len(body["entities"]) == 1
    assert body["entities"][0]["entity"]["id"] == ent["id"]
    assert body["entities"][0]["evidence"][0]["id"] == ev["id"]


def test_list_cases_pagination_and_workflow(client, world, f):
    h = world.h["inv"]
    _create_case(client, world, f, title="First case")
    _create_case(client, world, f, title="Second case")
    r = client.get("/api/v1/cases", headers=h)
    assert r.status_code == 200
    page = r.json()
    assert page["total"] >= 2
    assert {"items", "total", "page", "page_size", "pages"} <= set(page)

    r = client.get("/api/v1/cases/workflow", headers=h)
    assert r.status_code == 200
    transitions = r.json()["transitions"]
    assert "detected" in transitions and "triaged" in transitions["detected"]
