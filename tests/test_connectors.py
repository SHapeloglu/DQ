"""
test_connectors.py — OracleConnector ve SqlAlchemyConnector testleri.

Birim testleri (gerçek DB gerekmez):
    pytest tests/test_connectors.py -v -k "not integration"

Entegrasyon testleri (gerçek Oracle/SQLite gerekir):
    pytest tests/test_connectors.py -v -k "integration"
"""

import sys
import pytest

sys.path.insert(0, ".")
sys.path.insert(0, "./dq_web")   # test_mysql_connector.py ile aynı desen

from dq.connectors import (
    OracleConnector, SqlAlchemyConnector, build_connector, CONNECTOR_REGISTRY,
)


# ══════════════════════════════════════════════════════════════════════════
# OracleConnector
# ══════════════════════════════════════════════════════════════════════════

class TestOracleConnectorUnit:

    def test_registry_contains_oracle(self):
        assert "oracle" in CONNECTOR_REGISTRY

    def test_build_connector_returns_oracle(self):
        conn = build_connector({
            "type":         "oracle",
            "host":         "oracle-source",
            "port":         1521,
            "service_name": "freepdb1",
            "user":         "hr",
            "password":     "secret",
        })
        assert isinstance(conn, OracleConnector)

    def test_config_fields(self):
        conn = OracleConnector(
            host="oracle-source", port=1521,
            service_name="freepdb1", user="hr", password="secret",
        )
        assert conn.host         == "oracle-source"
        assert conn.port         == 1521
        assert conn.service_name == "freepdb1"
        assert conn.user         == "hr"
        assert conn.password     == "secret"

    def test_port_cast_to_int(self):
        conn = OracleConnector(host="oracle-source", port="1521",
                               service_name="freepdb1", user="hr", password="p")
        assert isinstance(conn.port, int)

    def test_default_port(self):
        conn = OracleConnector(host="oracle-source",
                               service_name="freepdb1", user="hr", password="p")
        assert conn.port == 1521

    def test_context_manager_interface(self):
        """BaseConnector'dan miras alınan __enter__/__exit__ tanımlı olmalı."""
        conn = OracleConnector(host="oracle-source",
                               service_name="freepdb1", user="hr", password="p")
        assert hasattr(conn, "__enter__")
        assert hasattr(conn, "__exit__")

    def test_build_connector_pops_type(self):
        config = {
            "type": "oracle", "host": "oracle-source", "port": 1521,
            "service_name": "freepdb1", "user": "hr", "password": "p",
        }
        build_connector(config)
        assert "type" not in config

    def test_connect_raises_clear_error_without_oracledb(self, monkeypatch):
        """oracledb kurulu değilse anlaşılır bir ImportError vermeli."""
        import builtins
        real_import = builtins.__import__

        def fake_import(name, *a, **k):
            if name == "oracledb":
                raise ImportError("no module")
            return real_import(name, *a, **k)

        monkeypatch.setattr(builtins, "__import__", fake_import)
        conn = OracleConnector(host="x", service_name="y", user="u", password="p")
        with pytest.raises(ImportError):
            conn.connect()


@pytest.mark.integration
class TestOracleConnectorIntegration:
    """
    Gerçek Oracle bağlantısı gerektirir (örn. gvenzl/oracle-free container).
    Çalıştır: pytest tests/test_connectors.py -v -k "Oracle and integration"
    """

    @pytest.fixture
    def conn(self):
        c = OracleConnector(
            host="oracle-source", port=1521,
            service_name="freepdb1", user="hr", password="hr_password",
        )
        yield c

    def test_connection_succeeds(self, conn):
        result = conn.test_connection()
        if not result["success"]:
            pytest.skip(f"oracle-source erişilemiyor: {result.get('error')}")
        assert result["success"] is True

    def test_execute_count(self, conn):
        with conn as c:
            rows = c.execute("SELECT COUNT(*) AS cnt FROM employees")
        assert isinstance(rows, list)
        assert len(rows) == 1

    def test_execute_returns_dict_rows(self, conn):
        with conn as c:
            rows = c.execute("SELECT 1 AS val FROM dual")
        assert isinstance(rows[0], dict)


# ══════════════════════════════════════════════════════════════════════════
# SqlAlchemyConnector
# ══════════════════════════════════════════════════════════════════════════

class TestSqlAlchemyConnectorUnit:

    def test_registry_contains_sqlalchemy(self):
        assert "sqlalchemy" in CONNECTOR_REGISTRY

    def test_build_connector_returns_sqlalchemy(self):
        conn = build_connector({
            "type": "sqlalchemy",
            "url":  "sqlite:///:memory:",
        })
        assert isinstance(conn, SqlAlchemyConnector)

    def test_url_used_directly_when_given(self):
        conn = SqlAlchemyConnector(url="sqlite:///:memory:")
        assert conn.url == "sqlite:///:memory:"

    def test_raises_without_url_or_dialect(self):
        with pytest.raises(ValueError):
            SqlAlchemyConnector()

    def test_dialect_builds_url(self):
        """dialect verildiğinde sqlalchemy.engine.URL ile bağlantı stringi kurulmalı."""
        pytest.importorskip("sqlalchemy")
        conn = SqlAlchemyConnector(
            dialect="sqlite", host=None, port=None,
            database="/tmp/test.db", user="", password="",
        )
        assert "sqlite" in str(conn.url)

    def test_context_manager_interface(self):
        conn = SqlAlchemyConnector(url="sqlite:///:memory:")
        assert hasattr(conn, "__enter__")
        assert hasattr(conn, "__exit__")

    def test_build_connector_pops_type(self):
        config = {"type": "sqlalchemy", "url": "sqlite:///:memory:"}
        build_connector(config)
        assert "type" not in config


@pytest.mark.integration
class TestSqlAlchemyConnectorIntegration:
    """
    Gerçek bağlantı gerektirir - SQLite stdlib'de olduğu için ekstra
    kurulum gerekmez, sadece 'sqlalchemy' paketi (requirements.txt'te var).
    Çalıştır: pytest tests/test_connectors.py -v -k "SqlAlchemy and integration"
    """

    def test_sqlite_end_to_end(self, tmp_path):
        pytest.importorskip("sqlalchemy")
        import sqlite3

        db_path = tmp_path / "test.db"
        raw = sqlite3.connect(str(db_path))
        raw.execute("CREATE TABLE orders (id INTEGER, amount REAL)")
        raw.execute("INSERT INTO orders VALUES (1, 10.5), (2, 20.0)")
        raw.commit()
        raw.close()

        conn = SqlAlchemyConnector(url=f"sqlite:///{db_path}")
        with conn as c:
            rows = c.execute("SELECT COUNT(*) AS cnt FROM orders")
        assert rows[0]["cnt"] == 2

    def test_sqlite_test_connection(self, tmp_path):
        pytest.importorskip("sqlalchemy")
        conn = SqlAlchemyConnector(url=f"sqlite:///{tmp_path}/empty.db")
        result = conn.test_connection()
        assert result["success"] is True
        assert result["dialect"] == "sqlite"
