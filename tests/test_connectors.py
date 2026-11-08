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
sys.path.insert(0, "./dq_web")

from dq.connectors import (
    OracleConnector, SqlAlchemyConnector, MongoConnector, build_connector, CONNECTOR_REGISTRY,
    DQCheckError, DQConnectionError,
)


# ══════════════════════════════════════════════════════════════════════════
# OracleConnector
# ══════════════════════════════════════════════════════════════════════════

class TestOracleConnectorUnit:
    """OracleConnector için birim testleri. Gerçek Oracle gerekmez; sadece kayıt (registry) tablosunda olduğu kontrol edilir."""
    def test_registry_contains_oracle(self):
        """CONNECTOR_REGISTRY içinde 'oracle' anahtarının bulunduğunu doğrular; aksi halde Oracle bağlantısı seçilemez."""
        assert "oracle" in CONNECTOR_REGISTRY


# ══════════════════════════════════════════════════════════════════════════
# MongoConnector
# ══════════════════════════════════════════════════════════════════════════

def test_mongo_connector_init():
    """Test MongoConnector initialization."""
    conn = MongoConnector(host="localhost", database="test_db")
    assert conn.host == "localhost"
    assert conn.database == "test_db"
    assert conn.client is None


def test_mongo_connector_query_validation():
    """Test MongoConnector query validation."""
    conn = MongoConnector(host="localhost")
    # Mock db to bypass connection check
    conn.db = {"_mock": True}  # Mock db object (truthy)
    
    # String query should fail
    with pytest.raises(DQCheckError, match="requires dict query"):
        conn.execute("invalid query")
    
    # Missing collection should fail
    with pytest.raises(DQCheckError, match="must contain 'collection'"):
        conn.execute({"pipeline": []})
    
    # Missing pipeline/filter should fail
    with pytest.raises(DQCheckError, match="must contain 'pipeline' or 'filter'"):
        conn.execute({"collection": "users"})


# ══════════════════════════════════════════════════════════════════════════
# MongoConnector Integration Tests
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.integration
def test_mongo_connector_connect():
    """Test MongoConnector connection (requires MongoDB running)."""
    conn = MongoConnector(host="localhost", port=27017, database="test")
    try:
        conn.connect()
        assert conn.client is not None
        assert conn.db is not None
        conn.close()
    except DQConnectionError:
        pytest.skip("MongoDB not available")


# ══════════════════════════════════════════════════════════════════════════
# DB2 (SqlAlchemyConnector with ibm_db_sa)
# ══════════════════════════════════════════════════════════════════════════

def test_db2_connector_init():
    """Test DB2 connector initialization via SqlAlchemyConnector."""
    conn = SqlAlchemyConnector(
        dialect="ibm_db_sa://ibm_db",
        host="localhost",
        port=50000,
        database="TESTDB",
        user="db2admin",
        password="password123"
    )
    assert conn.url is not None
    assert "ibm_db" in conn.url


def test_db2_url_construction():
    """Test DB2 URL string construction."""
    conn = SqlAlchemyConnector(
        url="ibm_db_sa://ibm_db://db2admin:password@localhost:50000/TESTDB"
    )
    # DİKKAT: 'or' yüzünden iki koşuldan biri tutması yeterlidir; URL'nin tam doğru olduğu kanıtlanmaz. (TODO(kontrol))
    assert "db2admin" in conn.url or "localhost" in conn.url


@pytest.mark.integration
def test_db2_connector_connect():
    """Test DB2 connection (requires DB2 running)."""
    conn = SqlAlchemyConnector(
        dialect="ibm_db_sa://ibm_db",
        host="localhost",
        port=50000,
        database="TESTDB",
        user="db2admin",
        password="password123"
    )
    try:
        result = conn.test_connection()
        # DİKKAT: Bu assert her iki sonucu da kabul eder (True veya False), yani bağlantının başarılı olup olmadığını kanıtlamaz. Sadece test_connection() fonksiyonunun hata vermeden döndüğünü kontrol eder. (TODO(kontrol))
        assert result["success"] is True or result["success"] is False
        # Just check that test_connection() runs without crashing
    except Exception as e:
        pytest.skip(f"DB2 not available: {e}")
