import pytest

from app.models.enums import UserRole


def test_unauthenticated_access_rejected_everywhere(client, world):
    for method, path in [("get", "/api/v1/brands"), ("get", "/api/v1/entities"), ("get", "/api/v1/cases"), ("get", "/api/v1/graph"),
                         ("get", "/api/v1/dashboard/stats"), ("get", "/api/v1/audit"), ("get", "/api/v1/users"), ("post", "/api/v1/entities")]:
        assert getattr(client, method)(path).status_code == 401, path


def test_role_permissions(client, world):
    w, bid = world, world.brand["id"]
    body = {"brand_id": bid, "entity_type": "website", "attributes": {"url": "https://acmebank-login.xyz"}}
    assert client.post("/api/v1/entities", json=body, headers=w.h["partner"]).status_code == 403          # partner: read-only
    assert client.post("/api/v1/entities", json=body, headers=w.h["owner"]).status_code == 201            # brand owner may submit
    e = client.get("/api/v1/entities", headers=w.h["owner"]).json()["items"][0]["id"]
    assert client.post(f"/api/v1/entities/{e}/analyze", headers=w.h["owner"]).status_code == 403          # ...but not run analysis
    assert client.post(f"/api/v1/entities/{e}/analyze", headers=w.h["inv"]).status_code == 201
    assert client.get("/api/v1/users", headers=w.h["inv"]).status_code == 403                             # investigators can't manage users
    assert client.get("/api/v1/users", headers=w.h["admin"]).status_code == 200
    assert client.post("/api/v1/organizations", json={"name": "N", "slug": "nn"}, headers=w.h["inv"]).status_code == 403
    assert client.get("/api/v1/dashboard/stats", headers=w.h["partner"]).status_code == 403
    assert client.get("/api/v1/audit", headers=w.h["owner"]).status_code == 403
    case_body = {"brand_id": bid, "title": "A case", "entity_ids": [e]}
    assert client.post("/api/v1/cases", json=case_body, headers=w.h["owner"]).status_code == 403
    assert client.post("/api/v1/cases", json=case_body, headers=w.h["inv"]).status_code == 201


def test_error_response_shape_for_403(client, world):
    r = client.get("/api/v1/users", headers=world.h["inv"])
    assert r.json()["error"]["code"] == "forbidden" and "details" in r.json()["error"]


def test_org_isolation_on_brands_entities_cases_evidence(client, f, world):
    w = world
    e = f.website(w.h["inv"], w.brand["id"])
    case = client.post("/api/v1/cases", json={"brand_id": w.brand["id"], "title": "Case one", "entity_ids": [e["id"]]}, headers=w.h["inv"]).json()
    ev = client.post("/api/v1/evidence", json={"entity_id": e["id"], "kind": "text", "title": "note", "text_content": "x"}, headers=w.h["inv"]).json()
    o = w.h["outsider"]
    # every cross-tenant lookup is a 404 (no existence leak)
    assert client.get(f"/api/v1/brands/{w.brand['id']}", headers=o).status_code == 404
    assert client.get(f"/api/v1/entities/{e['id']}", headers=o).status_code == 404
    assert client.post(f"/api/v1/entities/{e['id']}/analyze", headers=o).status_code == 404
    assert client.get(f"/api/v1/cases/{case['id']}", headers=o).status_code == 404
    assert client.post(f"/api/v1/cases/{case['id']}/notes", json={"body": "hi"}, headers=o).status_code == 404
    assert client.get(f"/api/v1/evidence/{ev['id']}", headers=o).status_code == 404
    assert client.get(f"/api/v1/graph/entities/{e['id']}/neighbors", headers=o).status_code == 404
    # listings are scoped
    assert client.get("/api/v1/brands", headers=o).json()["total"] == 0
    assert client.get("/api/v1/entities", headers=o).json()["total"] == 0
    assert client.get("/api/v1/cases", headers=o).json()["total"] == 0
    assert client.get("/api/v1/evidence", headers=o).json()["total"] == 0
    assert client.get("/api/v1/graph", headers=o).json()["node_count"] == 0
    assert client.get("/api/v1/dashboard/stats", headers=o).json()["totals"]["monitored_entities"] == 0
    assert client.get("/api/v1/dashboard/stats", params={"brand_id": w.brand["id"]}, headers=o).status_code == 404
    # cannot write into another tenant's brand
    r = client.post("/api/v1/entities", json={"brand_id": w.brand["id"], "entity_type": "website", "attributes": {"url": "https://x-y.xyz"}}, headers=o)
    assert r.status_code == 404
    assert client.post(f"/api/v1/brands/{w.brand['id']}/references", json={"kind": "name", "value": "Evil"}, headers=w.h["outsider_owner"]).status_code == 404
    # admin sees everything
    assert client.get(f"/api/v1/entities/{e['id']}", headers=w.h["admin"]).status_code == 200


def test_cannot_create_brand_in_foreign_org(client, world):
    r = client.post("/api/v1/brands", json={"organization_id": str(world.org_a.id), "name": "Hijack"}, headers=world.h["outsider_owner"])
    assert r.status_code == 404


def test_user_without_organization_has_no_data_access(client, f, world):
    orphan = f.user(UserRole.INVESTIGATOR, None)
    h = f.headers(orphan)
    assert client.get("/api/v1/brands", headers=h).json()["total"] == 0
    assert client.get(f"/api/v1/brands/{world.brand['id']}", headers=h).status_code == 404
    assert client.post("/api/v1/brands", json={"name": "X"}, headers=h).status_code == 403 or client.post("/api/v1/brands", json={"name": "X"}, headers=h).status_code == 422


def test_cannot_assign_case_to_user_outside_org(client, f, world):
    w = world
    e = f.website(w.h["inv"], w.brand["id"])
    c = client.post("/api/v1/cases", json={"brand_id": w.brand["id"], "title": "Case one", "entity_ids": [e["id"]]}, headers=w.h["inv"]).json()
    client.post(f"/api/v1/cases/{c['id']}/status", json={"status": "triaged"}, headers=w.h["inv"])
    client.post(f"/api/v1/cases/{c['id']}/status", json={"status": "under_review"}, headers=w.h["inv"])
    r = client.post(f"/api/v1/cases/{c['id']}/assign", json={"assignee_id": str(w.users["outsider"].id)}, headers=w.h["inv"])
    assert r.status_code == 422


def test_cannot_attach_foreign_entity_to_case(client, f, world):
    w = world
    other_org_brand = f.brand(w.h["admin"], w.org_b, name="OtherCo")
    foreign = f.website(w.h["outsider"], other_org_brand["id"])
    mine = f.website(w.h["inv"], w.brand["id"])
    r = client.post("/api/v1/cases", json={"brand_id": w.brand["id"], "title": "Sneaky", "entity_ids": [mine["id"], foreign["id"]]}, headers=w.h["inv"])
    assert r.status_code == 404


def test_deactivated_users_and_role_change_effective(client, f, world, db):
    from app.models import User
    u = world.users["owner"]
    assert client.get("/api/v1/entities", headers=world.h["owner"]).status_code == 200
    r = client.patch(f"/api/v1/users/{u.id}", json={"role": "partner"}, headers=world.h["admin"])
    assert r.status_code == 200
    body = {"brand_id": world.brand["id"], "entity_type": "website", "attributes": {"url": "https://acmebank-login.xyz"}}
    assert client.post("/api/v1/entities", json=body, headers=world.h["owner"]).status_code == 403  # old token, new role enforced
