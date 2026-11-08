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

    """/health endpoint'inin sağlık kontrolü: çalışıyorsa 200 ve {status: ok, time: ...} döner. Yük dengeleyici ve izleme araçları bu adresi yoklar."""
    def test_health_returns_200(self, client):
        """/health 200 (başarılı) durum kodu döndürmeli."""
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_health_returns_ok(self, client):
        """/health yanıtında status alanı 'ok' olmalı."""
        # DİKKAT: Bu satırda 'resp' değişkeni gereksiz; atama zincirleri yanlışlıkla yazılmış. Davranışı değiştirmemek için dokunulmadı. (TODO(kontrol))
        data = resp = client.get("/health").json()
        assert data["status"] == "ok"

    def test_health_returns_time(self, client):
        """/health yanıtında time alanı bulunmalı (sunucu saatini gösterir)."""
        data = client.get("/health").json()
        assert "time" in data


# ── POST /api/runs ────────────────────────────────────────────────────────────

class TestPostRun:

    """POST /api/runs: Airflow'dan gelen DQ çalıştırma sonuçlarını kaydeden endpoint. sample_payload fixture'ı örnek bir çalıştırma (2 kontrol) gönderir."""
    def test_post_run_returns_201(self, client, sample_payload):
        """Geçerli payload 201 (oluşturuldu) durum kodu ile kabul edilmeli."""
        resp = client.post("/api/runs", json=sample_payload)
        assert resp.status_code == 201

    def test_post_run_returns_run_id(self, client, sample_payload):
        """Yanıtta kaydedilen çalıştırmanın run_id değeri bulunmalı."""
        resp = client.post("/api/runs", json=sample_payload).json()
        assert "run_id" in resp

    def test_post_run_returns_accepted_count(self, client, sample_payload):
        """Payload'da 2 sonuç var; yanıttaki accepted sayısı 2 olmalı (hiçbiri kaybolmamalı)."""
        resp = client.post("/api/runs", json=sample_payload).json()
        assert resp["accepted"] == 2

    def test_post_run_uses_provided_run_id(self, client, sample_payload):
        """Payload'da run_id verilmişse sunucu aynısını kullanmalı (kendi ID üretmemeli)."""
        resp = client.post("/api/runs", json=sample_payload).json()
        assert resp["run_id"] == "run_20260512"

    def test_post_run_generates_run_id_if_missing(self, client, sample_payload):
        """run_id gönderilmezse sunucu yine de dolu bir run_id üretmeli. Pop ile fixture'dan alan silinir."""
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

    """GET /api/runs: kaydedilen çalıştırmaların listesini döndüren endpoint'in testleri."""
    def test_get_runs_empty(self, client):
        """Hiç kayıt yokken liste boş [] olarak döner."""
        resp = client.get("/api/runs")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_runs_after_post(self, client, sample_payload):
        """POST sonrası GET ile tek bir çalıştırma görünmeli ve dag_id 'orders_quality' olmalı."""
        client.post("/api/runs", json=sample_payload)
        runs = client.get("/api/runs").json()
        assert len(runs) == 1
        assert runs[0]["dag_id"] == "orders_quality"

    def test_get_runs_filter_by_dag_id(self, client, sample_payload):
        """dag_id filtresi: iki farklı DAG kaydedilince ?dag_id=orders_quality yalnız o DAG'ın kaydını döndürmeli. İkinci çalıştırma 'other' farklı run_id ile eklenir (çakışmasın diye)."""
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
        """Belirli bir run_id ile tek çalıştırma getirilebilmeli (200 ve doğru dag_id)."""
        client.post("/api/runs", json=sample_payload)
        resp = client.get("/api/runs/run_20260512")
        assert resp.status_code == 200
        assert resp.json()["dag_id"] == "orders_quality"

    def test_get_run_not_found(self, client):
        """Olmayan run_id için 404 (bulunamadı) dönmeli."""
        resp = client.get("/api/runs/olmayan_id")
        assert resp.status_code == 404


# ── GET /api/results ──────────────────────────────────────────────────────────

class TestGetResults:

    """GET /api/results: tek tek kontrol sonuçlarını (satır bazında) döndüren endpoint'in testleri."""
    def test_results_empty(self, client):
        """Hiç sonuç yokken liste boş döner."""
        resp = client.get("/api/results")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_results_after_post(self, client, sample_payload):
        """Payload'daki 2 kontrol sonucu GET /api/results ile 2 satır olarak görünmeli."""
        client.post("/api/runs", json=sample_payload)
        results = client.get("/api/results").json()
        assert len(results) == 2

    def test_results_contain_expected_fields(self, client, sample_payload):
        """Her sonuç satırı name, passed, value, run_at, dag_id alanlarını içermeli (Excel/raporlama için gerekli alanlar)."""
        client.post("/api/runs", json=sample_payload)
        r = client.get("/api/results").json()[0]
        assert "name"    in r
        assert "passed"  in r
        assert "value"   in r
        assert "run_at"  in r
        assert "dag_id"  in r

    def test_results_filter_passed_false(self, client, sample_payload):
        """?passed=false filtresi: sadece başarısız kontrol (Null oran) dönmeli."""
        client.post("/api/runs", json=sample_payload)
        results = client.get("/api/results?passed=false").json()
        assert len(results) == 1
        assert results[0]["name"] == "Null oran < %10"

    def test_results_filter_passed_true(self, client, sample_payload):
        """?passed=true filtresi: sadece başarılı kontrol dönmeli. Yanıttaki passed değeri 1 çıkar; veritabanı boolean'ı sayı (1/0) olarak sakladığı için."""
        client.post("/api/runs", json=sample_payload)
        results = client.get("/api/results?passed=true").json()
        assert len(results) == 1
        assert results[0]["passed"] == 1

    def test_results_filter_by_name(self, client, sample_payload):
        """?name= filtresi: kontrol adına göre tek satır döner. Adda boşluk ve '>' karakteri vardır; URL'de bunlar çalıştığı için doğrudan yazılmıştır."""
        client.post("/api/runs", json=sample_payload)
        results = client.get("/api/results?name=Satır sayısı > 0").json()
        assert len(results) == 1


# ── GET /api/results.csv ──────────────────────────────────────────────────────

class TestCsvExport:

    """GET /api/results.csv: sonuçların CSV (Excel'de açılabilen tablo) olarak indirilmesi testleri."""
    def test_csv_returns_200(self, client, sample_payload):
        """CSV endpoint'i 200 döndürmeli."""
        client.post("/api/runs", json=sample_payload)
        resp = client.get("/api/results.csv")
        assert resp.status_code == 200

    def test_csv_content_type(self, client, sample_payload):
        """İçerik türü text/csv olmalı (tarayıcı/Excel dosyayı doğru açsın diye)."""
        client.post("/api/runs", json=sample_payload)
        resp = client.get("/api/results.csv")
        assert "text/csv" in resp.headers["content-type"]

    def test_csv_has_header(self, client, sample_payload):
        """CSV'nin ilk satırı başlık olmalı: name ve passed kolon adları bulunmalı."""
        client.post("/api/runs", json=sample_payload)
        resp = client.get("/api/results.csv")
        first_line = resp.text.split("\n")[0]
        assert "name" in first_line
        assert "passed" in first_line

    def test_csv_has_data_rows(self, client, sample_payload):
        """CSV'de başlık + 2 veri satırı = 3 satır olmalı. Boş satırlar sayılmaz."""
        client.post("/api/runs", json=sample_payload)
        resp = client.get("/api/results.csv")
        lines = [l for l in resp.text.split("\n") if l.strip()]
        # header + 2 data satırı
        assert len(lines) == 3


# ── GET /odata/Results ────────────────────────────────────────────────────────

class TestOData:

    """/odata/ uç noktaları: Power BI gibi OData destekli araçların okuyabilmesi için. $metadata şema tanımını (XML) döndürür."""
    def test_odata_metadata_returns_200(self, client):
        """/odata/$metadata 200 döndürmeli."""
        resp = client.get("/odata/$metadata")
        assert resp.status_code == 200

    def test_odata_metadata_is_xml(self, client):
        """$metadata içerik türü XML olmalı (OData şeması XML'dir)."""
        resp = client.get("/odata/$metadata")
        assert "xml" in resp.headers["content-type"]

    def test_odata_metadata_contains_entity(self, client):
        """$metadata şemasında 'Result' varlığı (entity) tanımlı olmalı."""
        assert "Result" in client.get("/odata/$metadata").text

    def test_odata_results_returns_200(self, client):
        """/odata/Results 200 döndürmeli."""
        resp = client.get("/odata/Results")
        assert resp.status_code == 200

    def test_odata_results_has_context(self, client):
        """OData yanıtında @odata.context alanı bulunmalı (OData standart alanı)."""
        data = client.get("/odata/Results").json()
        assert "@odata.context" in data

    def test_odata_results_has_value(self, client):
        """OData yanıtında value alanı (kayıt listesi) bulunmalı."""
        data = client.get("/odata/Results").json()
        assert "value" in data

    def test_odata_results_after_post(self, client, sample_payload):
        """POST sonrası OData Results listesinde 2 kayıt görünmeli."""
        client.post("/api/runs", json=sample_payload)
        data = client.get("/odata/Results").json()
        assert len(data["value"]) == 2

    def test_odata_passed_is_boolean(self, client, sample_payload):
        """OData'da passed alanı true/false (boolean) olmalı; sayı (1/0) değil. Power BI bu tipi bekler."""
        client.post("/api/runs", json=sample_payload)
        results = client.get("/odata/Results").json()["value"]
        for r in results:
            assert isinstance(r["passed"], bool)

    def test_odata_top_parameter(self, client, sample_payload):
        """$top=1 parametresi: en fazla 1 kayıt dönmeli."""
        client.post("/api/runs", json=sample_payload)
        data = client.get("/odata/Results?$top=1").json()
        assert len(data["value"]) == 1

    def test_odata_skip_parameter(self, client, sample_payload):
        """$skip=1 parametresi: ilk kaydı atlayıp kalan 1 kaydı dönmeli (2 kayıttan)."""
        client.post("/api/runs", json=sample_payload)
        data = client.get("/odata/Results?$skip=1").json()
        assert len(data["value"]) == 1
