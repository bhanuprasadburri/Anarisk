"""Auth extras (forgot/reset/change password, PATCH /auth/me) + organization detail endpoints."""
from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.models import PasswordResetToken
from tests.conftest import PASSWORD

NEW_PASSWORD = "Reset-Passw0rd!"


def test_forgot_password_unknown_email_is_generic(client, world):
    r = client.post("/api/v1/auth/forgot-password", json={"email": "nobody-has-this@example.com"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "sent"
    assert not body.get("dev_reset_token")  # no token for unknown addresses (no enumeration)


def test_forgot_password_known_email_returns_dev_token_and_stores_only_hash(client, world, db):
    email = world.users["inv"].email
    r = client.post("/api/v1/auth/forgot-password", json={"email": email})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "sent" and body["dev_only"] is True
    token = body["dev_reset_token"]
    assert token and len(token) >= 30
    rows = db.scalars(select(PasswordResetToken).where(
        PasswordResetToken.user_id == world.users["inv"].id)).all()
    assert len(rows) == 1
    assert rows[0].token_hash == hashlib.sha256(token.encode()).hexdigest()
    assert token not in rows[0].token_hash  # only the SHA-256 digest is persisted


def test_reset_password_happy_path_and_single_use(client, world, db):
    email = world.users["inv"].email
    token = client.post("/api/v1/auth/forgot-password", json={"email": email}).json()["dev_reset_token"]

    r = client.post("/api/v1/auth/reset-password", json={"token": token, "new_password": NEW_PASSWORD})
    assert r.status_code == 200, r.text
    assert client.post("/api/v1/auth/login", json={"email": email, "password": NEW_PASSWORD}).status_code == 200

    # the token is single-use
    r = client.post("/api/v1/auth/reset-password", json={"token": token, "new_password": "Another-Passw0rd!"})
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "invalid_or_expired_token"


def test_reset_password_rejects_invalid_and_expired_tokens(client, world, db):
    r = client.post("/api/v1/auth/reset-password", json={"token": "z" * 43, "new_password": NEW_PASSWORD})
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "invalid_or_expired_token"

    email = world.users["inv"].email
    token = client.post("/api/v1/auth/forgot-password", json={"email": email}).json()["dev_reset_token"]
    row = db.scalars(select(PasswordResetToken).where(
        PasswordResetToken.token_hash == hashlib.sha256(token.encode()).hexdigest())).one()
    row.expires_at = datetime.now(UTC) - timedelta(minutes=1)  # simulate the 30-minute TTL expiring
    db.commit()
    r = client.post("/api/v1/auth/reset-password", json={"token": token, "new_password": NEW_PASSWORD})
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "invalid_or_expired_token"
    # password unchanged: the original still works
    assert client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD}).status_code == 200


def test_change_password_wrong_current_and_success(client, world):
    h = world.h["inv"]
    r = client.post("/api/v1/auth/change-password",
                    headers=h, json={"current_password": "wrong-current", "new_password": NEW_PASSWORD})
    assert r.status_code == 400 and r.json()["error"]["code"] == "invalid_current_password"

    r = client.post("/api/v1/auth/change-password",
                    headers=h, json={"current_password": PASSWORD, "new_password": NEW_PASSWORD})
    assert r.status_code == 200, r.text
    assert client.post("/api/v1/auth/login",
                       json={"email": world.users["inv"].email, "password": NEW_PASSWORD}).status_code == 200


def test_get_me_includes_preferences_and_organization(client, world):
    r = client.get("/api/v1/auth/me", headers=world.h["inv"])
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == world.users["inv"].email
    assert "preferences" in body
    assert body["organization"] is not None
    assert body["organization"]["id"] == str(world.org_a.id)
    assert body["organization"]["name"] == world.org_a.name


def test_patch_me_updates_name_and_preferences(client, world):
    h = world.h["inv"]
    prefs = {"theme": "dark", "email_digest": True}
    r = client.patch("/api/v1/auth/me", headers=h, json={"full_name": "Renamed Investigator", "preferences": prefs})
    assert r.status_code == 200, r.text
    assert r.json()["full_name"] == "Renamed Investigator"
    assert r.json()["preferences"] == prefs
    r = client.get("/api/v1/auth/me", headers=h)
    assert r.json()["full_name"] == "Renamed Investigator" and r.json()["preferences"] == prefs


def test_patch_me_rejects_duplicate_email(client, world):
    h = world.h["inv"]
    r = client.patch("/api/v1/auth/me", headers=h, json={"email": world.users["owner"].email})
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "email_taken"


def test_organization_detail_member_and_outsider(client, world):
    org_id = str(world.org_a.id)
    r = client.get(f"/api/v1/organizations/{org_id}", headers=world.h["inv"])  # member
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["id"] == org_id and body["slug"] == world.org_a.slug
    assert body["member_count"] == 3 and body["brand_count"] == 1
    assert "created_at" in body

    r = client.get(f"/api/v1/organizations/{org_id}", headers=world.h["outsider"])  # non-member
    assert r.status_code == 403

    r = client.get("/api/v1/organizations/00000000-0000-0000-0000-000000000000", headers=world.h["inv"])
    assert r.status_code == 404


def test_organization_patch_admin_only(client, world):
    org_id = str(world.org_a.id)
    r = client.patch(f"/api/v1/organizations/{org_id}", headers=world.h["outsider"], json={"name": "Hijacked"})
    assert r.status_code == 403  # outsider (and no org:manage)

    r = client.patch(f"/api/v1/organizations/{org_id}", headers=world.h["inv"], json={"name": "Renamed by member"})
    assert r.status_code == 403  # member without org:manage

    r = client.patch(f"/api/v1/organizations/{org_id}", headers=world.h["admin"], json={"name": "Org A Renamed"})
    assert r.status_code == 200, r.text
    assert r.json()["name"] == "Org A Renamed"
    assert r.json()["member_count"] == 3
    assert client.get(f"/api/v1/organizations/{org_id}", headers=world.h["inv"]).json()["name"] == "Org A Renamed"
