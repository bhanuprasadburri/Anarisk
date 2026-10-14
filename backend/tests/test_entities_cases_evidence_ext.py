"""Extensions: entity DELETE + detail enrichment, case PATCH/DELETE, evidence link/unlink, CSV export, verification."""
import uuid

from tests.conftest import PASSWORD, png_bytes


def _entity_with_evidence(f, w):
    h = w.h
    e = f.profile(h["owner"], w.brand["id"], handle="acmebank_support_24")
    ev = f.client.post("/api/v1/evidence", json={"entity_id": e["id"], "kind": "url", "title": "Phishing page capture",
                                                 "description": "synthetic", "source_url": "https://acmebank-login.xyz/verify",
                                                 "text_content": "sign in to acmebank", "provenance": "synthetic"},
                       headers=h["owner"])
    assert ev.status_code == 201, ev.text
    return e, ev.json()


def _case(f, w, entity_id):
    r = f.client.post("/api/v1/cases", json={"brand_id": w.brand["id"], "title": "AcmeBank impersonation report",
                                             "summary": "synthetic", "entity_ids": [entity_id]}, headers=w.h["inv"])
    assert r.status_code == 201, r.text
    return r.json()


# ------------------------------- entities -------------------------------
def test_entity_detail_is_fully_enriched(world, f):
    e, ev = _entity_with_evidence(f, world)
    r = f.client.get(f"/api/v1/entities/{e['id']}", headers=world.h["inv"])
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["id"] == e["id"]
    assert d["evidence_count"] == 1
    assert [x["id"] for x in d["evidence"]] == [ev["id"]]
    assert d["evidence"][0]["verification_status"] in ("pending", "verified", "mismatch")
    assert isinstance(d["related_entities"], list) and isinstance(d["cases"], list)
    assert isinstance(d["asset_metadata"], dict)
    assert d["asset_metadata"].get("handle") == "acmebank_support_24"


def test_entity_delete_admin_only_and_cascades(world, f):
    e, ev = _entity_with_evidence(f, world)
    case = _case(f, world, e["id"])
    # investigators / brand owners may not delete
    assert f.client.delete(f"/api/v1/entities/{e['id']}", headers=world.h["inv"]).status_code == 403
    assert f.client.delete(f"/api/v1/entities/{e['id']}", headers=world.h["owner"]).status_code == 403
    # outsider (investigator in another org) is blocked by the admin-only gate first -> 403
    assert f.client.delete(f"/api/v1/entities/{e['id']}", headers=world.h["outsider"]).status_code == 403
    # admin deletes: entity + its evidence are gone, the case keeps its history
    r = f.client.delete(f"/api/v1/entities/{e['id']}", headers=world.h["admin"])
    assert r.status_code == 204, r.text
    assert f.client.get(f"/api/v1/entities/{e['id']}", headers=world.h["admin"]).status_code == 404
    assert f.client.get(f"/api/v1/evidence/{ev['id']}", headers=world.h["admin"]).status_code == 404
    kept = f.client.get(f"/api/v1/cases/{case['id']}", headers=world.h["inv"])
    assert kept.status_code == 200
    assert kept.json()["events"]  # the audit trail survived the entity deletion


def test_entity_sort_by_created_at_supported(world, f):
    f.profile(world.h["owner"], world.brand["id"], handle="acmebank_aaa")
    f.profile(world.h["owner"], world.brand["id"], handle="acmebank_bbb")
    ok = f.client.get("/api/v1/entities", params={"sort": "created_at", "order": "asc"}, headers=world.h["inv"])
    assert ok.status_code == 200, ok.text
    assert f.client.get("/api/v1/entities", params={"sort": "bogus"}, headers=world.h["inv"]).status_code == 422


# ------------------------------- cases -------------------------------
def test_case_patch_edit_and_optimistic_concurrency(world, f):
    e, _ = _entity_with_evidence(f, world)
    case = _case(f, world, e["id"])
    r = f.client.patch(f"/api/v1/cases/{case['id']}",
                       json={"title": "AcmeBank credential harvest - priority", "severity": "critical",
                             "version": case["version"]}, headers=world.h["inv"])
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["title"] == "AcmeBank credential harvest - priority"
    assert d["severity"] == "critical"
    assert d["version"] == case["version"] + 1
    # stale version -> 409
    stale = f.client.patch(f"/api/v1/cases/{case['id']}", json={"title": "Racing edit", "version": case["version"]},
                           headers=world.h["inv"])
    assert stale.status_code == 409
    # partner (read-only) may not patch; outsider 404
    assert f.client.patch(f"/api/v1/cases/{case['id']}", json={"title": "Partner edit"}, headers=world.h["partner"]).status_code == 403
    assert f.client.patch(f"/api/v1/cases/{case['id']}", json={"title": "Outsider edit"}, headers=world.h["outsider"]).status_code == 404
    # title too short -> 422
    assert f.client.patch(f"/api/v1/cases/{case['id']}", json={"title": "x"}, headers=world.h["inv"]).status_code == 422


def test_case_delete_admin_only_keeps_entities_and_evidence(world, f):
    e, ev = _entity_with_evidence(f, world)
    case = _case(f, world, e["id"])
    assert f.client.delete(f"/api/v1/cases/{case['id']}", headers=world.h["inv"]).status_code == 403
    r = f.client.delete(f"/api/v1/cases/{case['id']}", headers=world.h["admin"])
    assert r.status_code == 204, r.text
    assert f.client.get(f"/api/v1/cases/{case['id']}", headers=world.h["admin"]).status_code == 404
    # the entity and its evidence are untouched by a case deletion
    assert f.client.get(f"/api/v1/entities/{e['id']}", headers=world.h["inv"]).status_code == 200
    assert f.client.get(f"/api/v1/evidence/{ev['id']}", headers=world.h["inv"]).status_code == 200


def test_case_detail_hydrates_evidence_with_roles(world, f):
    e, ev = _entity_with_evidence(f, world)
    case = _case(f, world, e["id"])
    link = f.client.post(f"/api/v1/evidence/{ev['id']}/link", json={"case_id": case["id"]}, headers=world.h["owner"])
    assert link.status_code == 200, link.text
    assert case["id"] in link.json()["case_ids"]
    d = f.client.get(f"/api/v1/cases/{case['id']}", headers=world.h["inv"]).json()
    assert [x["id"] for x in d["evidence"]] == [ev["id"]]
    assert d["evidence"][0]["role"] in ("linked", "supporting")
    assert d["allowed_transitions"]


# ------------------------------- evidence -------------------------------
def test_evidence_unlink_case_and_entity(world, f):
    e, ev = _entity_with_evidence(f, world)
    case = _case(f, world, e["id"])
    h = world.h["owner"]
    assert f.client.post(f"/api/v1/evidence/{ev['id']}/link", json={"case_id": case["id"]}, headers=h).status_code == 200
    # path variant
    r = f.client.delete(f"/api/v1/evidence/{ev['id']}/link/{case['id']}", headers=h)
    assert r.status_code == 204, r.text
    assert f.client.get(f"/api/v1/evidence/{ev['id']}", headers=h).json()["case_ids"] == []
    # query variant: detach from the entity, the record stays in the brand pool
    r = f.client.delete(f"/api/v1/evidence/{ev['id']}/link", params={"entity_id": e["id"]}, headers=h)
    assert r.status_code == 204, r.text
    still = f.client.get(f"/api/v1/evidence/{ev['id']}", headers=h)
    assert still.status_code == 200
    assert still.json()["entity"] is None
    # neither id -> 422
    assert f.client.delete(f"/api/v1/evidence/{ev['id']}/link", headers=h).status_code == 422
    assert f.client.post(f"/api/v1/evidence/{ev['id']}/link", json={}, headers=h).status_code == 422


def test_evidence_csv_export_with_filters(world, f):
    e, ev = _entity_with_evidence(f, world)
    h = world.h["inv"]
    r = f.client.get("/api/v1/evidence/export", headers=h)
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("text/csv")
    assert "attachment; filename=" in r.headers["content-disposition"]
    body = r.text.strip().splitlines()
    assert "title" in body[0].lower() and "case_ids" in body[0].lower()
    assert len(body) == 2 and ev["id"] in r.text
    # /export/csv is the same handler
    assert f.client.get("/api/v1/evidence/export/csv", headers=h).text == r.text
    # filters thread through
    assert len(f.client.get("/api/v1/evidence/export", params={"entity_id": e["id"]}, headers=h).text.strip().splitlines()) == 2
    assert len(f.client.get("/api/v1/evidence/export", params={"q": "no-such-capture"}, headers=h).text.strip().splitlines()) == 1
    assert f.client.get("/api/v1/evidence/export", params={"verification_status": "mismatch"}, headers=h).text.count("\n") <= 1


def test_evidence_verification_statuses_and_sort(world, f):
    e, _ = _entity_with_evidence(f, world)
    h = world.h["owner"]
    up = f.client.post("/api/v1/evidence/upload",
                       data={"entity_id": e["id"], "title": "Screenshot of the fake profile", "kind": "screenshot",
                             "provenance": "manual"}, files={"file": ("shot.png", png_bytes("copy"), "image/png")}, headers=h)
    assert up.status_code == 201, up.text
    ev_id = up.json()["id"]
    # uploads are marked verified at rest
    assert f.client.get(f"/api/v1/evidence/{ev_id}", headers=h).json()["verification_status"] == "verified"
    v = f.client.post(f"/api/v1/evidence/{ev_id}/verify", headers=h)
    assert v.status_code == 200 and v.json()["matches"] is True
    # filters: only-verified vs pending
    assert f.client.get("/api/v1/evidence", params={"verification_status": "verified"}, headers=h).json()["total"] == 1
    assert f.client.get("/api/v1/evidence", params={"verification_status": "pending"}, headers=h).json()["total"] == 1
    # sort by size_bytes
    r = f.client.get("/api/v1/evidence", params={"sort": "size_bytes", "order": "desc"}, headers=h)
    assert r.status_code == 200
    sizes = [x["size_bytes"] for x in r.json()["items"] if x["size_bytes"] is not None]
    assert sizes == sorted(sizes, reverse=True)
    assert f.client.get("/api/v1/evidence", params={"sort": "bogus"}, headers=h).status_code == 422


def test_evidence_delete_permissions(world, f):
    e, ev = _entity_with_evidence(f, world)
    assert f.client.delete(f"/api/v1/evidence/{ev['id']}", headers=world.h["partner"]).status_code == 403
    assert f.client.delete(f"/api/v1/evidence/{ev['id']}", headers=world.h["outsider"]).status_code == 404
    r = f.client.delete(f"/api/v1/evidence/{ev['id']}", headers=world.h["admin"])
    assert r.status_code == 204, r.text
    assert f.client.get(f"/api/v1/evidence/{ev['id']}", headers=world.h["admin"]).status_code == 404


def test_entity_evidence_subresource_matches_list(world, f):
    e, ev = _entity_with_evidence(f, world)
    r = f.client.get(f"/api/v1/entities/{e['id']}/evidence", headers=world.h["inv"])
    assert r.status_code == 200, r.text
    assert [x["id"] for x in r.json()] == [ev["id"]]
    assert r.json()[0]["case_ids"] == []
