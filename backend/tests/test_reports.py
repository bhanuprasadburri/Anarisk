"""Reports API: aggregate overview and CSV exports."""
from __future__ import annotations

import csv
import io


def test_reports_overview_shape(client, world, f):
    admin = world.h["admin"]
    # Create a little data (world already has one brand with references).
    f.website(world.h["owner"], world.brand["id"])
    f.profile(world.h["owner"], world.brand["id"])

    r = client.get("/api/v1/reports/overview", headers=admin)
    assert r.status_code == 200
    body = r.json()
    for key in ("generated_at", "date_range", "totals", "threat_distribution", "cases_by_status",
                "risk_trend", "threats_by_channel", "top_connected_entities", "entity_type_distribution",
                "severity_by_type", "mobile_apps", "evidence", "data_notes"):
        assert key in body, f"missing {key}"

    assert body["totals"]["entities"] >= 2
    assert isinstance(body["totals"]["open_cases"], int)
    assert isinstance(body["cases_by_status"], dict)
    assert isinstance(body["risk_trend"], list)
    assert body["evidence"]["total"] >= 0
    assert isinstance(body["mobile_apps"]["total"], int)
    assert isinstance(body["data_notes"], list) and body["data_notes"]

    # Date range defaults to the last 30 days and can be overridden.
    r = client.get("/api/v1/reports/overview?from=2026-01-01&to=2026-12-31", headers=admin)
    assert r.status_code == 200
    assert r.json()["date_range"] == {"from": "2026-01-01", "to": "2026-12-31"}

    # An invalid range is rejected before any data is read.
    r = client.get("/api/v1/reports/overview?from=not-a-date", headers=admin)
    assert r.status_code == 422


def test_reports_overview_permissions(client, world):
    # An investigator can read the overview.
    r = client.get("/api/v1/reports/overview", headers=world.h["inv"])
    assert r.status_code == 200
    # A partner lacks dashboard:read.
    r = client.get("/api/v1/reports/overview", headers=world.h["partner"])
    assert r.status_code == 403
    # Another org's member sees their own (empty) scope, not an error.
    r = client.get("/api/v1/reports/overview", headers=world.h["outsider"])
    assert r.status_code == 200
    assert r.json()["totals"]["entities"] == 0
    # Unauthenticated.
    assert client.get("/api/v1/reports/overview").status_code == 401


def test_reports_csv_export(client, world):
    admin = world.h["admin"]
    for report in ("threats", "entities", "cases", "evidence", "apps"):
        r = client.get(f"/api/v1/reports/export/csv?report={report}", headers=admin)
        assert r.status_code == 200, f"{report}: {r.text}"
        assert "text/csv" in r.headers.get("content-type", "")
        assert "attachment" in r.headers.get("content-disposition", "")
        lines = r.text.splitlines()
        assert len(lines) >= 1, f"{report} produced no CSV rows"
        # Parse it back to prove it is well-formed CSV with a header.
        parsed = list(csv.reader(io.StringIO(r.text)))
        assert parsed[0], f"{report} header row is empty"

    # Unknown report -> 422 (rejected before any data is read).
    r = client.get("/api/v1/reports/export/csv?report=bogus", headers=admin)
    assert r.status_code == 422


def test_reports_csv_permissions(client, world):
    # An investigator can export threats.
    r = client.get("/api/v1/reports/export/csv?report=threats", headers=world.h["inv"])
    assert r.status_code == 200
    # A partner holds entity:read / case:read / evidence:read, so every report is permitted.
    r = client.get("/api/v1/reports/export/csv?report=cases", headers=world.h["partner"])
    assert r.status_code == 200
    # Another org's member exports their own (empty) scope.
    r = client.get("/api/v1/reports/export/csv?report=threats", headers=world.h["outsider"])
    assert r.status_code == 200
    # Unauthenticated.
    assert client.get("/api/v1/reports/export/csv?report=threats").status_code == 401
