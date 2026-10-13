def test_create_each_entity_type_and_canonical_ids(client, f, world):
    h, b = world.h["inv"], world.brand["id"]
    p = f.profile(h, b, handle="@AcmeBank_Help", platform="X", bio="hello")
    assert p["canonical_id"] == "x:acmebank_help" and p["display_name"] == "@AcmeBank_Help" and p["provenance"] == "manual"
    w = f.website(h, b, url="HTTP://AcmeBank-Login.XYZ:80/verify/?utm_source=abc&b=2&a=1#frag")
    assert w["canonical_id"] == "http://acmebank-login.xyz/verify?a=1&b=2"
    d = f.entity(h, b, "domain", attributes={"domain": "Acmebank-Login.xyz"})
    assert d["canonical_id"] == "acmebank-login.xyz"
    i = f.entity(h, b, "image", display_name="Logo copy", attributes={"phash": "F869A5169F611A69"})
    assert i["canonical_id"] == "phash:f869a5169f611a69"
    a = f.entity(h, b, "mobile_app", attributes={"app_name": "AcmeBank Rewards", "package_id": "com.Fake.Acme", "store": "google_play"})
    assert a["canonical_id"] == "google_play:com.fake.acme" and a["display_name"] == "AcmeBank Rewards"
    assert client.get("/api/v1/entities", params={"brand_id": b}, headers=h).json()["total"] == 5


def test_duplicate_submission_merges_and_updates_last_seen(client, f, world):
    h, b = world.h["inv"], world.brand["id"]
    first = f.profile(h, b, handle="fakeacme", bio="v1", post_timestamps=["2026-01-01T00:00:00Z"], links=["https://a-b.xyz"])
    r = client.post("/api/v1/entities", json={"brand_id": b, "entity_type": "social_profile", "platform": "x",
                                              "attributes": {"handle": "FakeAcme", "followers_count": 50, "post_timestamps": ["2026-01-02T00:00:00Z"], "links": ["https://c-d.xyz"]}}, headers=h)
    assert r.status_code == 201 and r.json()["created"] is False
    e = r.json()["entity"]
    assert e["id"] == first["id"] and e["submission_count"] == 2
    assert e["last_seen_at"] > first["last_seen_at"] and e["first_seen_at"] == first["first_seen_at"]
    assert e["attributes"]["bio"] == "v1" and e["attributes"]["followers_count"] == 50          # old kept, new added
    assert len(e["attributes"]["post_timestamps"]) == 2 and len(e["attributes"]["links"]) == 2  # lists merged
    assert client.get("/api/v1/entities", params={"brand_id": b}, headers=h).json()["total"] == 1


def test_same_canonical_in_different_brands_is_distinct(client, f, world):
    h = world.h["inv"]
    b2 = f.brand(world.h["owner"], world.org_a, name="OtherBrand", refs=False)
    e1 = f.website(h, world.brand["id"], url="https://shared-site.xyz")
    e2 = f.website(h, b2["id"], url="https://shared-site.xyz")
    assert e1["id"] != e2["id"]


def test_validation_errors(client, world):
    h, b = world.h["inv"], world.brand["id"]
    def post(**kw):
        return client.post("/api/v1/entities", json={"brand_id": b, **kw}, headers=h)
    r = post(entity_type="social_profile", attributes={"handle": "x"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "validation_error"                    # platform missing
    assert post(entity_type="website", attributes={"url": "javascript:alert(1)"}).status_code == 422
    assert post(entity_type="website", attributes={"url": "ftp://x.example/a"}).status_code == 422
    assert post(entity_type="website", attributes={"url": "https://ok.example", "links": ["not a url"]}).status_code == 422
    assert post(entity_type="domain", attributes={"domain": "127.0.0.1"}).status_code == 422
    assert post(entity_type="image", attributes={}).status_code == 422
    assert post(entity_type="image", attributes={"phash": "zzzz"}).status_code == 422
    assert post(entity_type="mobile_app", attributes={"app_name": "x"}).status_code == 422
    assert post(entity_type="website", attributes={"url": "https://a-b.xyz", "unknown_field": 1}).status_code == 422
    assert post(entity_type="bogus", attributes={}).status_code == 422
    assert post(entity_type="website", provenance="collected", attributes={"url": "https://a-b.xyz"}).status_code == 422  # reserved for connectors
    r = post(entity_type="website", attributes={"url": "https://a-b.xyz", "image_phashes": ["abc"]})
    assert r.status_code == 422 and any("image_phashes" in d["field"] for d in r.json()["error"]["details"])


def test_synthetic_provenance_is_preserved_and_reported(client, f, world):
    h, b = world.h["inv"], world.brand["id"]
    e = f.entity(h, b, "website", provenance="synthetic", attributes={"url": "https://fake-demo.xyz"})
    assert e["provenance"] == "synthetic"
    stats = client.get("/api/v1/dashboard/stats", headers=h).json()
    assert stats["data_provenance"] == {"collected": 0, "manual": 0, "synthetic": 1}


def test_official_asset_is_flagged_and_not_scored(client, f, world):
    h, b = world.h["inv"], world.brand["id"]
    r = client.post("/api/v1/entities", json={"brand_id": b, "entity_type": "website", "attributes": {"url": "https://www.acmebank.example/help"}, "analyze": True}, headers=h)
    assert r.status_code == 201
    body = r.json()
    assert "official brand domain" in body["matches_official_reference"] and body["assessment"] is None
    eid = body["entity"]["id"]
    a = client.post(f"/api/v1/entities/{eid}/analyze", headers=h)
    assert a.status_code == 409 and a.json()["error"]["code"] == "official_asset"
    own = f.profile(h, b, handle="AcmeBank", platform="x")
    assert client.post(f"/api/v1/entities/{own['id']}/analyze", headers=h).status_code == 409
    pkg = f.entity(h, b, "mobile_app", attributes={"app_name": "AcmeBank", "package_id": "com.acmebank.mobile"})
    assert client.post(f"/api/v1/entities/{pkg['id']}/analyze", headers=h).status_code == 409


def test_entity_list_filters_sorting_pagination(client, f, world):
    h, b = world.h["inv"], world.brand["id"]
    for i in range(5):
        f.website(h, b, url=f"https://acmebank-{i}-login.xyz")
    f.profile(h, b, handle="someone")
    r = client.get("/api/v1/entities", params={"brand_id": b, "entity_type": "website", "page_size": 2, "page": 3}, headers=h).json()
    assert r["total"] == 5 and r["pages"] == 3 and len(r["items"]) == 1 and r["page"] == 3
    assert client.get("/api/v1/entities", params={"q": "someone"}, headers=h).json()["total"] == 1
    assert client.get("/api/v1/entities", params={"assessed": True}, headers=h).json()["total"] == 0
    assert client.get("/api/v1/entities", params={"page_size": 1000}, headers=h).status_code == 422
    assert client.get("/api/v1/entities", params={"sort": "nonsense"}, headers=h).status_code == 422
    asc = [x["display_name"] for x in client.get("/api/v1/entities", params={"sort": "display_name", "order": "asc"}, headers=h).json()["items"]]
    assert asc == sorted(asc)


def test_collection_records_preserve_each_submission(client, f, world, db):
    from app.models import CollectionRecord
    h, b = world.h["inv"], world.brand["id"]
    f.website(h, b); f.website(h, b)
    recs = db.query(CollectionRecord).order_by(CollectionRecord.collected_at).all()
    assert len(recs) == 2 and [r.was_new_entity for r in recs] == [True, False] and all(r.provenance.value == "manual" for r in recs)


def test_connectors_are_honest_about_live_monitoring(client, world):
    h, b = world.h["inv"], world.brand["id"]
    cons = client.get("/api/v1/collection/connectors", headers=h).json()
    assert cons and all(c["live"] is False for c in cons)                               # no real external source is configured
    sample = next(c for c in cons if c["key"] == "sample-listings")
    assert sample["provenance_of_output"] == "synthetic"
    r = client.post("/api/v1/collection/connectors/sample-listings/run", json={"brand_id": b}, headers=h)
    assert r.status_code == 200 and r.json()["created"] == 3 and all(e["provenance"] == "synthetic" for e in r.json()["entities"])
    assert {e["entity_type"] for e in r.json()["entities"]} == {"mobile_app", "social_profile", "domain"}
    again = client.post("/api/v1/collection/connectors/sample-listings/run", json={"brand_id": b}, headers=h).json()
    assert again["created"] == 0                                                         # idempotent / deduplicated
    assert client.post("/api/v1/collection/connectors/nope/run", json={"brand_id": b}, headers=h).status_code == 404
    assert client.post("/api/v1/collection/connectors/sample-listings/run", json={"brand_id": b}, headers=world.h["owner"]).status_code == 403
    assert client.post("/api/v1/collection/connectors/sample-listings/run", json={"brand_id": b}, headers=world.h["outsider"]).status_code == 404


def test_unconfigured_connector_returns_409(client, world, monkeypatch):
    from app.models.enums import SourceKind
    from app.services.connectors import SourceConnector, register

    class NeedsKey(SourceConnector):
        key, name, kind, live = "needs-key", "Needs key", SourceKind.CONNECTOR, True
        def is_configured(self): return False
        def configuration_help(self): return "set NEEDS_KEY"
        def collect(self, brand, query): raise AssertionError("must not run")
    register(NeedsKey())
    r = client.post("/api/v1/collection/connectors/needs-key/run", json={"brand_id": world.brand["id"]}, headers=world.h["inv"])
    assert r.status_code == 409 and r.json()["error"]["code"] == "connector_not_configured"


def test_brand_reference_rules(client, world):
    h, bid = world.h["owner"], world.brand["id"]
    assert client.post(f"/api/v1/brands/{bid}/references", json={"kind": "name", "value": "Zed"}, headers=world.h["inv"]).status_code == 403  # investigators cannot edit official references
    dup = client.post(f"/api/v1/brands/{bid}/references", json={"kind": "domain", "value": "https://www.acmebank.example/"}, headers=h)
    assert dup.status_code == 409 and dup.json()["error"]["code"] == "duplicate_reference"
    assert client.post(f"/api/v1/brands/{bid}/references", json={"kind": "image", "value": "not-a-hash"}, headers=h).status_code == 422
    assert client.post(f"/api/v1/brands/{bid}/references", json={"kind": "name", "value": "X", "provenance": "collected"}, headers=h).status_code == 422
    detail = client.get(f"/api/v1/brands/{bid}", headers=h).json()
    assert len(detail["references"]) == 6 and detail["entity_count"] == 0
    rid = detail["references"][0]["id"]
    assert client.delete(f"/api/v1/brands/{bid}/references/{rid}", headers=h).status_code == 200
    assert client.delete(f"/api/v1/brands/{bid}/references/{rid}", headers=h).status_code == 404
    assert client.post("/api/v1/brands", json={"organization_id": str(world.org_a.id), "name": "AcmeBank"}, headers=h).status_code == 409  # slug taken
