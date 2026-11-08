"""
test_profiler.py — profile_column tek sorgu optimizasyonu testleri (GOREV 29)
DB import yok; connector MagicMock ile simule edilir.
"""
from unittest.mock import MagicMock
from profiler import profile_column, _detect_type, normalize_column_pattern


def _make_conn(row: dict):
    """Tek satirlik sonuc donduren mock connector."""
    conn = MagicMock()
    conn.execute.return_value = [row]
    return conn


class TestProfileColumnNumeric:
    """Sayısal kolonların profil testleri (satır sayısı, boş oranı, min/max/ortalama)."""
    def test_numeric_fields(self):
        """Sayısal kolon için tip 'numeric' çıkmalı; satır sayısı 100, boş sayısı 2 → boş oranı %2.0; min/max/ortalama değerleri sorgudan olduğu gibi alınmalı."""
        conn = _make_conn({
            "row_count": 100, "null_count": 2, "dc": 80,
            "num_min": 1.0, "num_max": 99.0, "num_avg": 50.0,
            "str_min_len": None, "str_max_len": None,
            "raw_min": None, "raw_max": None,
        })
        r = profile_column(conn, "age")
        assert r["type"] == "numeric"
        assert r["row_count"] == 100
        assert r["null_count"] == 2
        assert r["distinct_count"] == 80
        assert r["null_pct"] == 2.0
        assert r["min"] == 1.0
        assert r["max"] == 99.0
        assert r["avg"] == 50.0

    def test_numeric_single_query(self):
        """execute yalnizca 1 kez cagirilmali."""
        conn = _make_conn({
            "row_count": 10, "null_count": 0, "dc": 10,
            "num_min": 0.0, "num_max": 9.0, "num_avg": 4.5,
            "str_min_len": None, "str_max_len": None,
            "raw_min": None, "raw_max": None,
        })
        profile_column(conn, "price")
        assert conn.execute.call_count == 1


class TestProfileColumnString:
    """Metin (string) kolonların profil testleri."""
    def test_string_fields(self):
        """Metin kolonda tip 'string', min/max uzunluk (3 ve 20) doğru alınmalı."""
        conn = _make_conn({
            "row_count": 50, "null_count": 0, "dc": 30,
            "num_min": None, "num_max": None, "num_avg": None,
            "str_min_len": 3, "str_max_len": 20,
            "raw_min": "alice", "raw_max": "zoe",
        })
        r = profile_column(conn, "name")
        assert r["type"] == "string"
        assert r["min_length"] == 3
        assert r["max_length"] == 20

    def test_string_single_query(self):
        """Metin kolon profili de tek sorguda (execute 1 kez) yapılmalı."""
        conn = _make_conn({
            "row_count": 50, "null_count": 0, "dc": 30,
            "num_min": None, "num_max": None, "num_avg": None,
            "str_min_len": 3, "str_max_len": 20,
            "raw_min": "alice", "raw_max": "zoe",
        })
        profile_column(conn, "name")
        assert conn.execute.call_count == 1


class TestProfileColumnDate:
    """Tarih kolonlarının profil testleri."""
    def test_date_fields(self):
        """Tarih kolonunda tip 'date' çıkmalı; min/max değerleri (2023-01-01, 2024-12-31) metin olarak aynen dönmeli."""
        conn = _make_conn({
            "row_count": 20, "null_count": 1, "dc": 15,
            "num_min": None, "num_max": None, "num_avg": None,
            "str_min_len": 10, "str_max_len": 10,
            "raw_min": "2023-01-01", "raw_max": "2024-12-31",
        })
        r = profile_column(conn, "created_at")
        assert r["type"] == "date"
        assert r["min"] == "2023-01-01"
        assert r["max"] == "2024-12-31"

    def test_date_single_query(self):
        """Tarih kolonu profili de tek sorguda yapılmalı."""
        conn = _make_conn({
            "row_count": 20, "null_count": 0, "dc": 20,
            "num_min": None, "num_max": None, "num_avg": None,
            "str_min_len": 10, "str_max_len": 10,
            "raw_min": "2023-01-01", "raw_max": "2024-12-31",
        })
        profile_column(conn, "created_at")
        assert conn.execute.call_count == 1


class TestProfileColumnEdge:
    """Sınır durumları: boş tablo, tamamen boş kolon ve sorgu hatası."""
    def test_empty_table(self):
        """Hiç satır yoksa row_count 0, boş oranı 0.0 (0'a bölme hatası yok) ve tip 'unknown' olmalı."""
        conn = _make_conn({
            "row_count": 0, "null_count": 0, "dc": 0,
            "num_min": None, "num_max": None, "num_avg": None,
            "str_min_len": None, "str_max_len": None,
            "raw_min": None, "raw_max": None,
        })
        r = profile_column(conn, "col")
        assert r["row_count"] == 0
        assert r["null_pct"] == 0.0
        assert r["type"] == "unknown"

    def test_all_null(self):
        """Tüm değerler NULL ise boş oranı %100 ve tip 'unknown' olmalı (tip çıkarılacak veri yok)."""
        conn = _make_conn({
            "row_count": 10, "null_count": 10, "dc": 0,
            "num_min": None, "num_max": None, "num_avg": None,
            "str_min_len": None, "str_max_len": None,
            "raw_min": None, "raw_max": None,
        })
        r = profile_column(conn, "col")
        assert r["null_pct"] == 100.0
        assert r["type"] == "unknown"

    def test_execute_error(self):
        """Sorgu hata verirse (bağlantı koptu vb.) profil çökmemeli; sonuçta 'error' alanı dönmeli."""
        conn = MagicMock()
        conn.execute.side_effect = Exception("DB down")
        r = profile_column(conn, "col")
        assert "error" in r


class TestDetectType:
    """_detect_type: Python listesinden kolon tipini tahmin eden yardımcı fonksiyonun testleri."""
    def test_numeric(self):
        """Sayı listesi [1,2,3] → 'numeric'."""
        assert _detect_type([1, 2, 3]) == "numeric"

    def test_string(self):
        """Metin listesi ['alice','bob'] → 'string'."""
        assert _detect_type(["alice", "bob"]) == "string"

    def test_empty(self):
        """Boş liste → 'unknown' (tahmin edilecek veri yok)."""
        assert _detect_type([]) == "unknown"


class TestNormalizePattern:
    """normalize_column_pattern: kolon adını desen adına çeviren yardımcı fonksiyonun testleri. Bu desenler kural önerileri için kullanılır."""
    def test_id(self):
        """'customer_id' → '*_id' deseni (ID kolonları)."""
        assert normalize_column_pattern("customer_id") == "*_id"

    def test_email(self):
        """'user_email' → '*email*' deseni (e-posta içeren kolonlar)."""
        assert normalize_column_pattern("user_email") == "*email*"

    def test_date(self):
        """'created_at' → '*_date' deseni (tarih kolonları)."""
        assert normalize_column_pattern("created_at") == "*_date"
