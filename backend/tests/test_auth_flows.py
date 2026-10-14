"""Auth flows: password forgot/reset, change password, profile, organization."""
from __future__ import annotations

from tests.conftest import PASSWORD


def test_me_and_update_profile(client, world):
    h = world.h["admin"]
    r = client.get("/api/v1/auth/me", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == world.users["admin"].email
    assert body["organization"] is None  # the seeded admin has no organization
    assert body["preferences"] in (None, {})

    r = client.patch(
        "/api/v1/auth/me",
        headers=h,
        json={"full_name": "Renamed Admin", "preferences": {"theme": "dark"}},
    )
    assert r.status_code == 200
    assert r.json()["full_name"] == "Renamed Admin"
    assert r.json()["preferences"]["theme"] == "dark"

    r = client.get("/api/v1/auth/me", headers=h)
    assert r.json()["full_name"] == "Renamed Admin"
    assert r.json()["preferences"]["theme"] == "dark"


def test_me_includes_organization_for_member(client, world):
    r = client.get("/api/v1/auth/me", headers=world.h["inv"])
    assert r.status_code == 200
    body = r.json()
    assert body["organization"]["id"] == str(world.org_a.id)
    assert body["organization"]["name"] == world.org_a.name


def test_me_requires_auth(client):
    assert client.get("/api/v1/auth/me").status_code == 401


def test_forgot_password_dev_token_flow(client, world):
    email = world.users["owner"].email
    r = client.post("/api/v1/auth/forgot-password", json={"email": email})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "sent"
    assert body["dev_only"] is True
    token = body["dev_reset_token"]
    assert token

    # Unknown email: same generic response, no token (no user enumeration).
    r = client.post("/api/v1/auth/forgot-password", json={"email": "nobody@example.com"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "sent"
    assert body["dev_only"] is False
    assert body["dev_reset_token"] is None

    # Reset with the token and a new password.
    r = client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "Brand-New-Pass1!"},
    )
    assert r.status_code == 200
    assert r.json()["email"] == email

    # Old password no longer works; the new one does.
    r = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert r.status_code == 401
    r = client.post("/api/v1/auth/login", json={"email": email, "password": "Brand-New-Pass1!"})
    assert r.status_code == 200

    # The token is single-use.
    r = client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "Another-Pass2!"},
    )
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "invalid_or_expired_token"


def test_reset_password_invalid_token(client, world):
    r = client.post(
        "/api/v1/auth/reset-password",
        json={"token": "not-a-real-token-at-all-0123456789", "new_password": "Whatever-Pass1!"},
    )
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "invalid_or_expired_token"


def test_change_password(client, world):
    h = world.h["inv"]
    email = world.users["inv"].email
    r = client.post(
        "/api/v1/auth/change-password",
        headers=h,
        json={"current_password": PASSWORD, "new_password": "Investigator-2!"},
    )
    assert r.status_code == 200
    r = client.post("/api/v1/auth/login", json={"email": email, "password": "Investigator-2!"})
    assert r.status_code == 200

    # Wrong current password -> 400.
    r = client.post(
        "/api/v1/auth/change-password",
        headers=h,
        json={"current_password": "wrong", "new_password": "Another-3!"},
    )
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "invalid_current_password"

    # Restore the original password so other tests keep working.
    r = client.post(
        "/api/v1/auth/change-password",
        headers=h,
        json={"current_password": "Investigator-2!", "new_password": PASSWORD},
    )
    assert r.status_code == 200


def test_change_password_requires_auth(client, world):
    r = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "x", "new_password": "y"},
    )
    assert r.status_code == 401


def test_organization_detail_and_update(client, world):
    org_id = str(world.org_a.id)

    # Admin (global scope) can read any organization.
    r = client.get(f"/api/v1/organizations/{org_id}", headers=world.h["admin"])
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == org_id
    assert body["name"] == world.org_a.name
    assert body["member_count"] >= 3  # inv + owner + partner
    assert body["brand_count"] >= 1  # the world fixture's brand

    # A member can read their own organization.
    r = client.get(f"/api/v1/organizations/{org_id}", headers=world.h["inv"])
    assert r.status_code == 200

    # A member of a different organization cannot (403, not 404: no enumeration).
    r = client.get(f"/api/v1/organizations/{org_id}", headers=world.h["outsider_owner"])
    assert r.status_code == 403

    # Rename (org:manage = administrator only).
    r = client.patch(
        f"/api/v1/organizations/{org_id}",
        headers=world.h["admin"],
        json={"name": "Org A Renamed"},
    )
    assert r.status_code == 200
    assert r.json()["name"] == "Org A Renamed"

    # A brand owner in the org is a member but lacks org:manage.
    r = client.patch(
        f"/api/v1/organizations/{org_id}",
        headers=world.h["owner"],
        json={"name": "Nope"},
    )
    assert r.status_code == 403

    # Restore the name so later tests see the original.
    r = client.patch(
        f"/api/v1/organizations/{org_id}",
        headers=world.h["admin"],
        json={"name": "Org A"},
    )
    assert r.status_code == 200
    assert r.json()["name"] == "Org A"
