"""
conftest.py — pytest fixture'ları.

Her test dosyasında otomatik kullanılabilir.
"""

import sys
from pathlib import Path

import pytest

# Proje kökünü path'e ekle
sys.path.insert(0, str(Path(__file__).parent.parent))


# ── Mock Connector ────────────────────────────────────────────────────────────

class MockConnector:
    """
    Gerçek veritabanı gerektirmeden connector arayüzünü simüle eder.
    Her test kendi query_map'ini tanımlayabilir.
    """

    def __init__(self, query_map: dict | None = None):
        """
        Args:
            query_map: SQL anahtar kelime → döndürülecek satırlar
                       Örnek: {"COUNT": [{"cnt": 10}], "SUM": [{"total": 500.0}]}
        """
        self.query_map   = query_map or {}
        self.call_log    = []   # hangi sorgular çalıştı
        self.connected   = False
        self.closed      = False

    def connect(self):
        self.connected = True

    def close(self):
        self.closed = True

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *_):
        self.close()

    def execute(self, query: str) -> list[dict]:
        self.call_log.append(query)
        qu = query.upper()
        for keyword, result in self.query_map.items():
            if keyword.upper() in qu:
                return result
        return [{"val": 1}]   # varsayılan


# ── Fixture'lar ───────────────────────────────────────────────────────────────

@pytest.fixture
def basic_connector():
    """Temel sorgu sonuçlarıyla mock connector."""
    return MockConnector({
        "COUNT(*)":  [{"cnt": 100}],
        "SUM":       [{"total": 9500.0}],
        "AVG":       [{"avg": 95.0}],
        "MAX":       [{"max_ts": "2026-05-12T20:00:00"}],
        "SELECT *":  [{"id": 1, "customer_id": 2, "amount": 99.9,
                       "created_at": "2026-05-12T20:00:00"}],
    })


@pytest.fixture
def empty_connector():
    """Boş tablo simülasyonu."""
    return MockConnector({
        "COUNT(*)": [{"cnt": 0}],
        "SUM":      [{"total": None}],
        "AVG":      [{"avg": None}],
        "SELECT *": [],
    })


@pytest.fixture
def error_connector():
    """Hata fırlatan connector — hata yönetimini test etmek için."""
    class ErrorConnector(MockConnector):
        def execute(self, query):
            raise RuntimeError("Bağlantı kesildi")
        def connect(self): pass
        def close(self): pass

    return ErrorConnector()


@pytest.fixture
def sample_checks():
    """Sık kullanılan check seti."""
    from dq.engine import Check, greater_than, less_than, between

    return [
        Check("Satır sayısı > 0",
              "SELECT COUNT(*) FROM source",
              greater_than(0), "greater_than(0)", ["critical"]),

        Check("Null oran < %10",
              "SELECT COUNT(*)*100.0/COUNT(1) FROM source WHERE id IS NULL",
              less_than(10), "less_than(10)", ["quality"]),

        Check("Ortalama tutar makul",
              "SELECT AVG(amount) FROM source",
              between(1, 9999), "between(1,9999)", ["quality"]),
    ]


@pytest.fixture
def in_memory_store():
    """In-memory SQLite MetricStore."""
    from dq.metrics import MetricStore
    store = MetricStore(":memory:")
    yield store
    store.close()
