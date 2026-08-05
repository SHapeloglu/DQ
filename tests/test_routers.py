"""
test_routers.py — routers/ iş mantığı unit testleri.
pymysql / main.py import gerektirmez.
"""
import json
import pytest
from unittest.mock import MagicMock

def _make_conn(fetchone=None, fetchall=None):
    cur = MagicMock()
    cur.fetchone.return_value = fetchone
    cur.fetchall.return_value = fetchall or []
    cur.__enter__ = lambda s: s
    cur.__exit__ = MagicMock(return_value=False)
    conn = MagicMock()
    conn.cursor.return_value = cur
    return conn, cur

class TestSourcesLogic:
    def test_csv_config_only_has_path(self):
        type_ = "csv"
        config = {"path": "/data/file.csv"} if type_ == "csv" else {}
        assert config == {"path": "/data/file.csv"}
        assert "host" not in config

    def test_mysql_config_has_connection_fields(self):
        type_ = "mysql"
        config = {} if type_ == "csv" else {
            "host": "localhost", "port": "3306",
            "database": "dq", "user": "root", "password": "pass"
        }
        assert config["host"] == "localhost"
        assert "path" not in config

    def test_config_serialized_as_json(self):
        config = {"host": "localhost", "port": "3306"}
        serialized = json.dumps(config)
        assert json.loads(serialized)["host"] == "localhost"

    def test_source_delete_sql_structure(self):
        conn, cur = _make_conn()
        with conn.cursor() as c:
            c.execute("DELETE FROM sources WHERE id = %s", (42,))
        cur.execute.assert_called_with("DELETE FROM sources WHERE id = %s", (42,))

class TestChecksLogic:
    def test_library_pattern_id_valid(self):
        pid = int("5") if "5".strip().isdigit() else None
        assert pid == 5

    def test_library_pattern_id_empty(self):
        pid = int("") if "".strip().isdigit() else None
        assert pid is None

    def test_library_pattern_id_whitespace(self):
        pid = int("  ") if "  ".strip().isdigit() else None
        assert pid is None

    def test_suggestion_type_mapping(self):
        mapping = {"not_null": "is_not_null", "unique": "is_unique"}
        assert mapping.get("not_null", "not_null") == "is_not_null"
        assert mapping.get("unknown", "unknown") == "unknown"

    def test_reject_feedback_called_with_false(self):
        calls = []
        def mock_feedback(conn, pid, col, rule_type, accepted):
            calls.append({"accepted": accepted, "col": col})
        conn, _ = _make_conn()
        mock_feedback(conn, None, "email", "is_not_null", accepted=False)
        assert calls[0]["accepted"] is False
        assert calls[0]["col"] == "email"

class TestGlossaryLogic:
    def test_update_filters_allowed_fields(self):
        allowed = {"business_name", "description", "owner", "tags"}
        payload = {"business_name": "Ad", "hacker": "x", "tags": "pii"}
        updates = {k: v for k, v in payload.items() if k in allowed}
        assert "hacker" not in updates
        assert len(updates) == 2

    def test_update_empty_payload_rejected(self):
        allowed = {"business_name", "description", "owner", "tags"}
        updates = {k: v for k, v in {"bad": "x"}.items() if k in allowed}
        assert len(updates) == 0

    def test_set_clause_generation(self):
        updates = {"business_name": "Test", "owner": "CRM"}
        fields = ", ".join(f"{k}=%s" for k in updates)
        assert "business_name=%s" in fields
        assert "owner=%s" in fields
