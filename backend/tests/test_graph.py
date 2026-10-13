import pytest

SHARED_URL = "https://acmebank-secure-login.xyz/verify"
BIO = "AcmeBank - secure everyday banking for everyone. Customer care is available 24/7 - DM us!"


def rel(client, h, a, b, rtype="shares_domain", conf=0.8, note="same link in bio"):
    return client.post("/api/v1/graph/relationships", headers=h, json={"source_entity_id": a, "target_entity_id": b, "relationship_type": rtype, "confidence": conf, "evidence_note": note})


@pytest.fixture
def campaign(client, f, world):
    """3 linked high-risk entities + 1 isolated benign entity + 1 isolated risky entity."""
    h, bid = world.h["inv"], world.brand["id"]
    p1 = f.profile(h, bid, handle="acmebank_support_help", bio=BIO, links=[SHARED_URL], account_created_at="2026-10-08T00:00:00Z", image_phashes=["f869a5169f611a69"])
    p2 = f.profile(h, bid, handle="acme.bank.official", platform="instagram", bio="Claim your AcmeBank reward! " + SHARED_URL, links=[SHARED_URL], account_created_at="2026-10-01T00:00:00Z", image_phashes=["f869a5169f611a68"])
    site = f.website(h, bid, url=SHARED_URL, registered_at="2026-10-02T00:00:00Z", hosting={"ip": "203.0.113.7"})
    benign = f.profile(h, bid, handle="gardening_fan", bio="I post about roses and tomatoes every single week of the year.", account_created_at="2015-01-01T00:00:00Z")
    lone = f.website(h, bid, url="https://acmebank-lonely-bonus.top/claim")
    class C: pass
    c = C(); c.p1, c.p2, c.site, c.benign, c.lone, c.h, c.bid = p1, p2, site, benign, lone, h, bid
    return c


def test_manual_relationship_validation_and_canonical_order(client, campaign):
    c = campaign
    r = rel(client, c.h, c.p2["id"], c.p1["id"], "similar_identity", 0.7)
    assert r.status_code == 201
    out = r.json()
    assert out["source_entity_id"] < out["target_entity_id"] and out["relationship_type"] == "similar_identity" and out["confidence"] == 0.7
    assert out["evidence_note"] and out["created_at"] and out["auto_generated"] is False
    again = rel(client, c.h, c.p1["id"], c.p2["id"], "similar_identity", 0.9)                  # reversed order, same pair/type -> upsert
    assert again.status_code == 201 and again.json()["id"] == out["id"] and again.json()["confidence"] == 0.9
    lower = rel(client, c.h, c.p1["id"], c.p2["id"], "similar_identity", 0.2)
    assert lower.json()["confidence"] == 0.9                                                   # never downgraded by weaker evidence
    assert rel(client, c.h, c.p1["id"], c.p1["id"]).status_code == 422                         # self loop
    assert rel(client, c.h, c.p1["id"], c.p2["id"], conf=1.5).status_code == 422
    assert rel(client, c.h, c.p1["id"], c.p2["id"], "friends").status_code == 422
    assert rel(client, c.h, c.p1["id"], "00000000-0000-0000-0000-000000000000").status_code == 404


def test_relationship_evidence_reference_must_belong_to_entities(client, f, campaign, world):
    c = campaign
    ev = client.post("/api/v1/evidence", headers=c.h, json={"entity_id": c.benign["id"], "kind": "text", "title": "t", "text_content": "x"}).json()
    bad = client.post("/api/v1/graph/relationships", headers=c.h, json={"source_entity_id": c.p1["id"], "target_entity_id": c.p2["id"], "relationship_type": "shares_image", "confidence": 0.8, "evidence_id": ev["id"], "evidence_note": "n/a"})
    assert bad.status_code == 422
    ev2 = client.post("/api/v1/evidence", headers=c.h, json={"entity_id": c.p1["id"], "kind": "text", "title": "t", "text_content": "x"}).json()
    ok = client.post("/api/v1/graph/relationships", headers=c.h, json={"source_entity_id": c.p1["id"], "target_entity_id": c.p2["id"], "relationship_type": "shares_image", "confidence": 0.8, "evidence_id": ev2["id"], "evidence_note": "same logo"})
    assert ok.status_code == 201 and ok.json()["evidence_id"] == ev2["id"]
    assert client.post("/api/v1/graph/relationships", headers=world.h["owner"], json={"source_entity_id": c.p1["id"], "target_entity_id": c.p2["id"], "relationship_type": "shares_image", "confidence": 0.8, "evidence_note": "n/a"}).status_code == 403


def test_discovery_derives_relationships_from_observable_data(client, campaign):
    c = campaign
    d = client.post("/api/v1/graph/discover", params={"brand_id": c.bid}, headers=c.h)
    assert d.status_code == 200 and d.json()["pairs_compared"] == 10 and d.json()["relationships_created"] >= 3
    g = client.get("/api/v1/graph", params={"brand_id": c.bid}, headers=c.h).json()
    assert g["node_count"] == 5
    types = {(e["relationship_type"]) for e in g["edges"]}
    assert {"shares_domain", "shares_image"} <= types
    linked = {n["id"] for e in g["edges"] for n in (e["source"], e["target"]) for n in [{"id": n}]}
    assert c.p1["id"] in linked and c.p2["id"] in linked and c.site["id"] in linked
    assert c.benign["id"] not in linked and c.lone["id"] not in linked                         # unrelated entities stay unlinked
    for e in g["edges"]:
        assert e["evidence_note"] and 0 < e["confidence"] <= 1 and e["created_at"] and e["auto_generated"] is True
    again = client.post("/api/v1/graph/discover", params={"brand_id": c.bid}, headers=c.h).json()
    assert again["relationships_created"] == 0 and again["relationships_existing"] >= 3        # idempotent
    assert client.post("/api/v1/graph/discover", params={"brand_id": c.bid}, headers=c.h).status_code == 200


def test_infrastructure_and_coordinated_behavior_edges(client, f, world):
    h, bid = world.h["inv"], world.brand["id"]
    a = f.website(h, bid, url="https://acme-one.top", hosting={"ip": "198.51.100.9"})
    b = f.website(h, bid, url="https://totally-other.xyz", hosting={"ip": "198.51.100.9"})
    posts = [f"2026-10-0{d}T1{h_}:00:00Z" for d in range(1, 5) for h_ in (0, 5)]
    pa = f.profile(h, bid, handle="poster_alpha", post_timestamps=posts)
    pb = f.profile(h, bid, handle="poster_omega", post_timestamps=[p.replace(":00:00Z", ":00:20Z") for p in posts])
    client.post("/api/v1/graph/discover", params={"brand_id": bid}, headers=h)
    edges = client.get("/api/v1/graph", params={"brand_id": bid}, headers=h).json()["edges"]
    kinds = {(e["relationship_type"], frozenset((e["source"], e["target"]))) for e in edges}
    assert ("same_infrastructure", frozenset((a["id"], b["id"]))) in kinds
    assert ("coordinated_behavior", frozenset((pa["id"], pb["id"]))) in kinds


def analyzed(client, c):
    client.post("/api/v1/graph/discover", params={"brand_id": c.bid}, headers=c.h)
    client.post("/api/v1/detection/analyze", headers=c.h, json={"brand_id": c.bid})


def test_clusters_proposal_requires_evidence_and_thresholds(client, campaign):
    c = campaign
    client.post("/api/v1/graph/discover", params={"brand_id": c.bid}, headers=c.h)
    before = client.get("/api/v1/graph/clusters", params={"brand_id": c.bid}, headers=c.h).json()
    assert len(before) == 1 and before[0]["size"] == 3
    assert before[0]["propose_for_investigation"] is False and any("no member has been risk-assessed" in r for r in before[0]["proposal_reasons"])   # connected != malicious
    client.post("/api/v1/detection/analyze", headers=c.h, json={"brand_id": c.bid})
    cl = client.get("/api/v1/graph/clusters", params={"brand_id": c.bid}, headers=c.h).json()[0]
    assert cl["propose_for_investigation"] is True and cl["max_risk_score"] >= 0.6 and cl["mean_edge_confidence"] >= 0.6
    assert set(cl["entity_ids"]) == {c.p1["id"], c.p2["id"], c.site["id"]} and cl["entity_type_counts"] == {"social_profile": 2, "website": 1}
    assert cl["relationship_type_counts"] and cl["headline"] and cl["existing_case_ids"] == [] and len(cl["cluster_id"]) == 16
    assert client.get("/api/v1/graph/clusters", params={"brand_id": c.bid, "proposed_only": True}, headers=c.h).json()[0]["cluster_id"] == cl["cluster_id"]


def test_weakly_linked_or_low_risk_cluster_is_not_proposed(client, campaign):
    c = campaign
    analyzed(client, c)
    rel(client, c.h, c.benign["id"], c.lone["id"], "similar_identity", 0.35, "weak hunch")      # low-confidence link between low/medium nodes
    clusters = client.get("/api/v1/graph/clusters", params={"brand_id": c.bid}, headers=c.h).json()
    weak = next(x for x in clusters if c.benign["id"] in x["entity_ids"])
    assert weak["propose_for_investigation"] is False and any("below" in r for r in weak["proposal_reasons"])
    only_weak = client.get("/api/v1/graph", params={"brand_id": c.bid, "min_confidence": 0.5}, headers=c.h).json()
    assert not any({e["source"], e["target"]} == {c.benign["id"], c.lone["id"]} for e in only_weak["edges"])


def test_graph_filters(client, campaign):
    c = campaign
    analyzed(client, c)
    full = client.get("/api/v1/graph", params={"brand_id": c.bid}, headers=c.h).json()
    sites = client.get("/api/v1/graph", params={"brand_id": c.bid, "entity_type": "website"}, headers=c.h).json()
    assert {n["entity_type"] for n in sites["nodes"]} == {"website"} and sites["edge_count"] == 0
    risky = client.get("/api/v1/graph", params={"brand_id": c.bid, "min_risk": 0.6}, headers=c.h).json()
    assert all(n["risk_score"] >= 0.6 for n in risky["nodes"]) and c.benign["id"] not in {n["id"] for n in risky["nodes"]} and risky["node_count"] < full["node_count"]
    sev = client.get("/api/v1/graph", params={"severity": ["high", "critical"]}, headers=c.h).json()
    assert all(n["severity"] in ("high", "critical") for n in sev["nodes"])
    assert client.get("/api/v1/graph", params={"min_risk": 2}, headers=c.h).status_code == 422
    assert client.get("/api/v1/graph", params={"brand_id": "00000000-0000-0000-0000-000000000000"}, headers=c.h).status_code == 404
    reb = client.post("/api/v1/graph/rebuild", headers=c.h, params={"brand_id": c.bid}).json()
    assert reb["node_count"] == 5 and reb["edge_count"] == full["edge_count"] and reb["cluster_count"] == 1


def test_neighbors_and_related_entities(client, campaign):
    c = campaign
    rel(client, c.h, c.p1["id"], c.site["id"], "shares_domain", 0.8)
    rel(client, c.h, c.site["id"], c.lone["id"], "same_infrastructure", 0.5)
    n1 = client.get(f"/api/v1/graph/entities/{c.p1['id']}/neighbors", headers=c.h).json()
    assert {n["id"] for n in n1["nodes"]} == {c.p1["id"], c.site["id"]}
    n2 = client.get(f"/api/v1/graph/entities/{c.p1['id']}/neighbors", params={"depth": 2}, headers=c.h).json()
    assert {n["id"] for n in n2["nodes"]} == {c.p1["id"], c.site["id"], c.lone["id"]}
    rel_ = client.get(f"/api/v1/graph/entities/{c.p1['id']}/related", headers=c.h).json()
    assert [r["entity"]["id"] for r in rel_] == [c.site["id"], c.lone["id"]]                  # ranked by path confidence
    assert rel_[0]["path_confidence"] == 0.8 and rel_[1]["path_confidence"] == pytest.approx(0.4) and rel_[1]["distance"] == 2
    assert rel_[1]["via"] == ["shares_domain", "same_infrastructure"]
    only_close = client.get(f"/api/v1/graph/entities/{c.p1['id']}/related", params={"max_depth": 1}, headers=c.h).json()
    assert [r["entity"]["id"] for r in only_close] == [c.site["id"]]
    assert client.get(f"/api/v1/graph/entities/{c.benign['id']}/related", headers=c.h).json() == []


def test_case_from_cluster_links_entities_and_blocks_duplicates(client, campaign):
    c = campaign
    analyzed(client, c)
    mixed = client.post("/api/v1/graph/clusters/case", headers=c.h, json={"entity_ids": [c.p1["id"], c.benign["id"]]})
    assert mixed.status_code == 409 and mixed.json()["error"]["code"] == "different_clusters"          # never silently merge unlinked entities
    assert client.get(f"/api/v1/entities/{c.benign['id']}/cases", headers=c.h).json() == []
    r = client.post("/api/v1/graph/clusters/case", headers=c.h, json={"entity_ids": [c.p1["id"]]})
    assert r.status_code == 201                                                                  # the whole connected cluster of p1 is used
    case = r.json()
    assert case["status"] == "detected" and case["entity_count"] >= 3 and case["cluster_key"]
    assert {e["entity"]["id"] for e in case["entities"]} >= {c.p1["id"], c.p2["id"], c.site["id"]}
    assert "Proposed by the platform" in case["summary"] and case["severity"] in ("high", "critical")
    cl = client.get("/api/v1/graph/clusters", params={"brand_id": c.bid}, headers=c.h).json()
    covered = next(x for x in cl if c.p1["id"] in x["entity_ids"])
    assert case["id"] in covered["existing_case_ids"] and covered["propose_for_investigation"] is False
    dup = client.post("/api/v1/graph/clusters/case", headers=c.h, json={"entity_ids": [c.p1["id"], c.p2["id"]]})
    assert dup.status_code == 409 and dup.json()["error"]["code"] == "cluster_has_open_case"
    assert client.get(f"/api/v1/entities/{c.p1['id']}/cases", headers=c.h).json()[0]["id"] == case["id"]
    lonely = client.post("/api/v1/graph/clusters/case", headers=c.h, json={"entity_ids": [c.benign["id"]]})
    assert lonely.status_code == 409 and lonely.json()["error"]["code"] == "not_a_cluster"
