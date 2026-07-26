"""
test_api.py — FastAPI endpointleri için testler.

Kurulum:
    pip install pytest pytest-asyncio httpx fastapi

Çalıştır:
    pytest tests/test_api.py -v
"""

import json
import pytest
from datetime import datetime, timezone


# FastAPI test client'ı
try:
    from fastapi.testclient import TestClient
    from dq.api import app, _get_db
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False

pytestmark = pytest.mark.skipif(
    not HAS_FASTAPI,
    reason="fastapi veya httpx kurulu değil — pip install fastapi httpx"
)


# ── Test client fixture ───────────────────────────────────────────────────────

@pytest.fixture
def client(tmp_path, monkeypatch):
    """
    Her test için temiz in-memory veritabanıyla client döndürür.
    """
    import sqlite3
    from dq import api as api_module

    # Geçici DB yolu
    db_path = tmp_path / "test_dq.db"
    monkeypatch.setattr(api_module, "DB_PATH", db_path)

    with TestClient(app) as c:
        yield c


@pytest.fixture
def sample_payload():
    """Airflow'dan gelecek örnek payload."""
    return {
        "dag_id":  "orders_quality",
        "task_id": "check_orders",
        "run_id":  "run_20260512",
        "run_at":  datetime.now(timezone.utc).isoformat(),
        "config":  "checks.toml",
        "mode":    "checks",
        "results": [
            {
                "name":     "Satır sayısı > 0",
                "passed":   True,
                "value":    412,
                "expected": "greater_than(0)",
            },
            {
                "name":     "Null oran < %10",
                "passed":   False,
                "value":    12.5,
                "expected": "less_than(10)",
            },
        ],
        "summary": {"total": 2, "passed": 1},
    }


# ── /health ───────────────────────────────────────────────────────────────────

class TestHealth:

    def test_health_returns_200(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_health_returns_ok(self, client):
        data = resp = client.get("/health").json()
        assert data["status"] == "ok"

    def test_health_returns_time(self, client):
        data = client.get("/health").json()
        assert "time" in data


# ── POST /api/runs ────────────────────────────────────────────────────────────

class TestPostRun:

    def test_post_run_returns_201(self, client, sample_payload):
        resp = client.post("/api/runs", json=sample_payload)
        assert resp.status_code == 201

    def test_post_run_returns_run_id(self, client, sample_payload):
        resp = client.post("/api/runs", json=sample_payload).json()
        assert "run_id" in resp

    def test_post_run_returns_accepted_count(self, client, sample_payload):
        resp = client.post("/api/runs", json=sample_payload).json()
        assert resp["accepted"] == 2

    def test_post_run_uses_provided_run_id(self, client, sample_payload):
        resp = client.post("/api/runs", json=sample_payload).json()
        assert resp["run_id"] == "run_20260512"

    def test_post_run_generates_run_id_if_missing(self, client, sample_payload):
        sample_payload.pop("run_id")
        resp = client.post("/api/runs", json=sample_payload).json()
        assert len(resp["run_id"]) > 0

    def test_post_empty_results(self, client):
        """Sonuçsuz payload kabul edilmeli."""
        resp = client.post("/api/runs", json={
            "dag_id": "test", "results": []
        })
        assert resp.status_code == 201
        assert resp.json()["accepted"] == 0


# ── GET /api/runs ─────────────────────────────────────────────────────────────

class TestGetRuns:

    def test_get_runs_empty(self, client):
        resp = client.get("/api/runs")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_runs_after_post(self, client, sample_payload):
        client.post("/api/runs", json=sample_payload)
        runs = client.get("/api/runs").json()
        assert len(runs) == 1
        assert runs[0]["dag_id"] == "orders_quality"

    def test_get_runs_filter_by_dag_id(self, client, sample_payload):
        client.post("/api/runs", json=sample_payload)

        # Farklı dag_id ile ikinci run
        other = dict(sample_payload)
        other["dag_id"]  = "other_dag"
        other["run_id"]  = "run_other"
        client.post("/api/runs", json=other)

        runs = client.get("/api/runs?dag_id=orders_quality").json()
        assert len(runs) == 1
        assert runs[0]["dag_id"] == "orders_quality"

    def test_get_run_by_id(self, client, sample_payload):
        client.post("/api/runs", json=sample_payload)
        resp = client.get("/api/runs/run_20260512")
        assert resp.status_code == 200
        assert resp.json()["dag_id"] == "orders_quality"

    def test_get_run_not_found(self, client):
        resp = client.get("/api/runs/olmayan_id")
        assert resp.status_code == 404


# ── GET /api/results ──────────────────────────────────────────────────────────

class TestGetResults:

    def test_results_empty(self, client):
        resp = client.get("/api/results")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_results_after_post(self, client, sample_payload):
        client.post("/api/runs", json=sample_payload)
        results = client.get("/api/results").json()
        assert len(results) == 2

    def test_results_contain_expected_fields(self, client, sample_payload):
        client.post("/api/runs", json=sample_payload)
        r = client.get("/api/results").json()[0]
        assert "name"    in r
        assert "passed"  in r
        assert "value"   in r
        assert "run_at"  in r
        assert "dag_id"  in r

    def test_results_filter_passed_false(self, client, sample_payload):
        client.post("/api/runs", json=sample_payload)
        results = client.get("/api/results?passed=false").json()
        assert len(results) == 1
        assert results[0]["name"] == "Null oran < %10"

    def test_results_filter_passed_true(self, client, sample_payload):
        client.post("/api/runs", json=sample_payload)
        results = client.get("/api/results?passed=true").json()
        assert len(results) == 1
        assert results[0]["passed"] == 1

    def test_results_filter_by_name(self, client, sample_payload):
        client.post("/api/runs", json=sample_payload)
        results = client.get("/api/results?name=Satır sayısı > 0").json()
        assert len(results) == 1


# ── GET /api/results.csv ──────────────────────────────────────────────────────

class TestCsvExport:

    def test_csv_returns_200(self, client, sample_payload):
        client.post("/api/runs", json=sample_payload)
        resp = client.get("/api/results.csv")
        assert resp.status_code == 200

    def test_csv_content_type(self, client, sample_payload):
        client.post("/api/runs", json=sample_payload)
        resp = client.get("/api/results.csv")
        assert "text/csv" in resp.headers["content-type"]

    def test_csv_has_header(self, client, sample_payload):
        client.post("/api/runs", json=sample_payload)
        resp = client.get("/api/results.csv")
        first_line = resp.text.split("\n")[0]
        assert "name" in first_line
        assert "passed" in first_line

    def test_csv_has_data_rows(self, client, sample_payload):
        client.post("/api/runs", json=sample_payload)
        resp = client.get("/api/results.csv")
        lines = [l for l in resp.text.split("\n") if l.strip()]
        # header + 2 data satırı
        assert len(lines) == 3


# ── GET /odata/Results ────────────────────────────────────────────────────────

class TestOData:

    def test_odata_metadata_returns_200(self, client):
        resp = client.get("/odata/$metadata")
        assert resp.status_code == 200

    def test_odata_metadata_is_xml(self, client):
        resp = client.get("/odata/$metadata")
        assert "xml" in resp.headers["content-type"]

    def test_odata_metadata_contains_entity(self, client):
        assert "Result" in client.get("/odata/$metadata").text

    def test_odata_results_returns_200(self, client):
        resp = client.get("/odata/Results")
        assert resp.status_code == 200

    def test_odata_results_has_context(self, client):
        data = client.get("/odata/Results").json()
        assert "@odata.context" in data

    def test_odata_results_has_value(self, client):
        data = client.get("/odata/Results").json()
        assert "value" in data

    def test_odata_results_after_post(self, client, sample_payload):
        client.post("/api/runs", json=sample_payload)
        data = client.get("/odata/Results").json()
        assert len(data["value"]) == 2

    def test_odata_passed_is_boolean(self, client, sample_payload):
        client.post("/api/runs", json=sample_payload)
        results = client.get("/odata/Results").json()["value"]
        for r in results:
            assert isinstance(r["passed"], bool)

    def test_odata_top_parameter(self, client, sample_payload):
        client.post("/api/runs", json=sample_payload)
        data = client.get("/odata/Results?$top=1").json()
        assert len(data["value"]) == 1

    def test_odata_skip_parameter(self, client, sample_payload):
        client.post("/api/runs", json=sample_payload)
        data = client.get("/odata/Results?$skip=1").json()
        assert len(data["value"]) == 1
