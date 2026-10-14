"""Notifications API: list, unread counts, mark read (single and bulk), scoping."""
from __future__ import annotations


def _make_case(client, world, f, title="Notification case"):
    """Create a case as the investigator (creator) and return it."""
    h = world.h["inv"]
    brand = world.brand  # the world fixture's brand (org A)
    ent = f.profile(world.h["owner"], brand["id"])
    r = client.post(
        "/api/v1/cases",
        headers=h,
        json={
            "brand_id": brand["id"],
            "title": title,
            "summary": "created to exercise the notification workflow",
            "entity_ids": [ent["id"]],
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def test_notifications_empty_then_created(client, world, f):
    h = world.h["inv"]
    r = client.get("/api/v1/notifications", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"items", "total", "unread_count", "page", "page_size", "pages"}
    assert body["total"] == 0
    assert body["unread_count"] == 0

    # Creating a case then triaging it notifies the creator (and admins).
    case = _make_case(client, world, f)
    r = client.post(
        f"/api/v1/cases/{case['id']}/status",
        headers=h,
        json={"status": "triaged", "comment": "looks real"},
    )
    assert r.status_code == 200, r.text

    r = client.get("/api/v1/notifications", headers=h)
    assert r.status_code == 200
    assert r.json()["total"] >= 1
    assert r.json()["unread_count"] >= 1
    item = r.json()["items"][0]
    for key in ("id", "type", "title", "is_read", "created_at"):
        assert key in item, f"missing {key}"


def test_assignment_notifies_the_assignee(client, world, f):
    h = world.h["inv"]
    case = _make_case(client, world, f, title="assign me")
    # detected -> triaged -> under_review, then assign to the investigator.
    r = client.post(
        f"/api/v1/cases/{case['id']}/status", headers=h, json={"status": "triaged"}
    )
    assert r.status_code == 200
    r = client.post(
        f"/api/v1/cases/{case['id']}/status", headers=h, json={"status": "under_review"}
    )
    assert r.status_code == 200
    r = client.post(
        f"/api/v1/cases/{case['id']}/assign",
        headers=h,
        json={"assignee_id": str(world.users["inv"].id)},
    )
    assert r.status_code == 200, r.text

    r = client.get("/api/v1/notifications", headers=h)
    assert r.status_code == 200
    types = {n["type"] for n in r.json()["items"]}
    assert "case_assigned" in types


def test_notifications_unread_count_and_mark_read(client, world, f):
    h = world.h["inv"]
    case = _make_case(client, world, f, title="mark me")
    client.post(
        f"/api/v1/cases/{case['id']}/status", headers=h, json={"status": "triaged"}
    )
    client.post(
        f"/api/v1/cases/{case['id']}/status", headers=h, json={"status": "under_review"}
    )

    r = client.get("/api/v1/notifications", headers=h)
    assert r.status_code == 200
    items = r.json()["items"]
    assert items, "expected at least one notification"
    unread_before = r.json()["unread_count"]
    assert unread_before >= 1

    # Mark exactly one as read.
    nid = next(n["id"] for n in items if not n["is_read"])
    r = client.post("/api/v1/notifications/read", headers=h, json={"ids": [nid]})
    assert r.status_code == 200
    assert r.json()["updated"] == 1
    assert r.json()["unread_count"] == unread_before - 1

    # Mark ALL remaining as read.
    r = client.post("/api/v1/notifications/read", headers=h, json={})
    assert r.status_code == 200
    assert r.json()["updated"] >= 1
    assert r.json()["unread_count"] == 0

    r = client.get("/api/v1/notifications", headers=h)
    assert r.status_code == 200
    assert all(n["is_read"] for n in r.json()["items"])

    # unread_only filter now returns nothing.
    r = client.get("/api/v1/notifications?unread_only=true", headers=h)
    assert r.status_code == 200
    assert r.json()["total"] == 0


def test_notifications_are_scoped_to_user(client, world, f):
    """A different user in the same org must not see the investigator's notifications."""
    inv_h = world.h["inv"]
    case = _make_case(client, world, f, title="scoped")
    client.post(
        f"/api/v1/cases/{case['id']}/status", headers=inv_h, json={"status": "triaged"}
    )

    # The owner (different user, same org) sees only their own notifications.
    r = client.get("/api/v1/notifications", headers=world.h["owner"])
    assert r.status_code == 200
    assert r.json()["total"] == 0


def test_notifications_require_auth(client):
    assert client.get("/api/v1/notifications").status_code == 401
