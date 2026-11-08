"""MetricStore unit testleri — SQLite backend (Postgres integration ayrı)."""
import pytest
from dq.metrics import MetricStore


class FakeResult:
    """Gerçek veritabanı yerine kullanılan basit sahte sonuç nesnesi (name ve value alanları). record_results() bu nesneleri bekler."""
    def __init__(self, name, value):
        """Sahte sonucun adını ve değerini saklar."""
        self.name = name
        self.value = value


@pytest.fixture
def store(tmp_path):
    """Her test için geçici bir MetricStore üretir (tmp_path: pytest'in her teste özel geçici klasörü). Test bitince store.close() ile kapanır; böylece testler birbirini etkilemez."""
    s = MetricStore(db_path=tmp_path / "test.db")
    yield s
    s.close()


def test_record_and_history(store):
    """record() ile aynı metriğe iki değer kaydedilince history() bu iki kaydı döndürmeli ve ilk kaydın değeri 100.0 olmalı."""
    store.record("row_count", 100.0)
    store.record("row_count", 200.0)
    h = store.history("row_count", days=1)
    assert len(h) == 2
    assert h[0]["value"] == 100.0


def test_record_results(store):
    """record_results() ile iki FakeResult gönderildiğinde geçmişte 2 kayıt görünmeli."""
    results = [FakeResult("null_ratio", 0.05), FakeResult("null_ratio", 0.10)]
    store.record_results(results)
    h = store.history("null_ratio", days=1)
    assert len(h) == 2


def test_known_metrics(store):
    """known_metrics() kaydedilmiş tüm metrik adlarını içermeli (metric_a ve metric_b)."""
    store.record("metric_a", 1.0)
    store.record("metric_b", 2.0)
    names = store.known_metrics()
    assert "metric_a" in names
    assert "metric_b" in names


def test_none_value(store):
    """None değer kaydedilebilmeli ve geri okunduğunda None olmalı (boş ölçüm olarak saklanır)."""
    store.record("nullable_metric", None)
    h = store.history("nullable_metric", days=1)
    assert h[0]["value"] is None


# ── Postgres integration testleri ─────────────────────────────────────────────

# Bu import'lar dosyanın üst kısmındakilerle aynıdır (tekrar). Zararsızdır; ayrı 'Postgres' bölümünde okunurken bağlam için bırakıldı.
import os
import pytest
from dq.metrics import MetricStore

# PostgreSQL bağlantı adresi (DSN) ortam değişkeninden okunur; kod içine yazılmaz. Değişken yoksa None olur ve entegrasyon testleri atlanır.
PG_DSN = os.environ.get("METRICS_PG_DSN")


@pytest.mark.integration
@pytest.mark.skipif(not PG_DSN, reason="METRICS_PG_DSN env değişkeni yok")
def test_postgres_record_and_history():
    """PostgreSQL entegrasyon testi. Gerçek bir Postgres gerekir; METRICS_PG_DSN ortam değişkeni yoksa atlanır (skip). 'integration' işaretiyle diğer testlerden ayrılır."""
    with MetricStore(backend="postgres", dsn=PG_DSN) as store:
        store.record("pg_row_count", 999.0)
        h = store.history("pg_row_count", days=1)
        assert any(r["value"] == 999.0 for r in h)


@pytest.mark.integration
@pytest.mark.skipif(not PG_DSN, reason="METRICS_PG_DSN env değişkeni yok")
def test_postgres_known_metrics():
    """PostgreSQL'de known_metrics() kaydedilen metrik adını döndürmeli. Gerçek Postgres gerekir; env değişkeni yoksa atlanır."""
    with MetricStore(backend="postgres", dsn=PG_DSN) as store:
        store.record("pg_metric_x", 1.0)
        names = store.known_metrics()
        assert "pg_metric_x" in names
