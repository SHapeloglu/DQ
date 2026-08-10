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
    def test_numeric_fields(self):
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
    def test_string_fields(self):
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
        conn = _make_conn({
            "row_count": 50, "null_count": 0, "dc": 30,
            "num_min": None, "num_max": None, "num_avg": None,
            "str_min_len": 3, "str_max_len": 20,
            "raw_min": "alice", "raw_max": "zoe",
        })
        profile_column(conn, "name")
        assert conn.execute.call_count == 1


class TestProfileColumnDate:
    def test_date_fields(self):
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
        conn = _make_conn({
            "row_count": 20, "null_count": 0, "dc": 20,
            "num_min": None, "num_max": None, "num_avg": None,
            "str_min_len": 10, "str_max_len": 10,
            "raw_min": "2023-01-01", "raw_max": "2024-12-31",
        })
        profile_column(conn, "created_at")
        assert conn.execute.call_count == 1


class TestProfileColumnEdge:
    def test_empty_table(self):
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
        conn = MagicMock()
        conn.execute.side_effect = Exception("DB down")
        r = profile_column(conn, "col")
        assert "error" in r


class TestDetectType:
    def test_numeric(self):
        assert _detect_type([1, 2, 3]) == "numeric"

    def test_string(self):
        assert _detect_type(["alice", "bob"]) == "string"

    def test_empty(self):
        assert _detect_type([]) == "unknown"


class TestNormalizePattern:
    def test_id(self):
        assert normalize_column_pattern("customer_id") == "*_id"

    def test_email(self):
        assert normalize_column_pattern("user_email") == "*email*"

    def test_date(self):
        assert normalize_column_pattern("created_at") == "*_date"
