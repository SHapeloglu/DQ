"""MetricStore unit testleri — SQLite backend (Postgres integration ayrı)."""
import pytest
from dq.metrics import MetricStore


class FakeResult:
    def __init__(self, name, value):
        self.name = name
        self.value = value


@pytest.fixture
def store(tmp_path):
    s = MetricStore(db_path=tmp_path / "test.db")
    yield s
    s.close()


def test_record_and_history(store):
    store.record("row_count", 100.0)
    store.record("row_count", 200.0)
    h = store.history("row_count", days=1)
    assert len(h) == 2
    assert h[0]["value"] == 100.0


def test_record_results(store):
    results = [FakeResult("null_ratio", 0.05), FakeResult("null_ratio", 0.10)]
    store.record_results(results)
    h = store.history("null_ratio", days=1)
    assert len(h) == 2


def test_known_metrics(store):
    store.record("metric_a", 1.0)
    store.record("metric_b", 2.0)
    names = store.known_metrics()
    assert "metric_a" in names
    assert "metric_b" in names


def test_none_value(store):
    store.record("nullable_metric", None)
    h = store.history("nullable_metric", days=1)
    assert h[0]["value"] is None


# ── Postgres integration testleri ─────────────────────────────────────────────

import os
import pytest
from dq.metrics import MetricStore

PG_DSN = os.environ.get("METRICS_PG_DSN")


@pytest.mark.integration
@pytest.mark.skipif(not PG_DSN, reason="METRICS_PG_DSN env değişkeni yok")
def test_postgres_record_and_history():
    with MetricStore(backend="postgres", dsn=PG_DSN) as store:
        store.record("pg_row_count", 999.0)
        h = store.history("pg_row_count", days=1)
        assert any(r["value"] == 999.0 for r in h)


@pytest.mark.integration
@pytest.mark.skipif(not PG_DSN, reason="METRICS_PG_DSN env değişkeni yok")
def test_postgres_known_metrics():
    with MetricStore(backend="postgres", dsn=PG_DSN) as store:
        store.record("pg_metric_x", 1.0)
        names = store.known_metrics()
        assert "pg_metric_x" in names
