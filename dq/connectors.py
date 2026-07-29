"""
Connector katmanı — her veri kaynağı bu arayüzü uygular.
Yeni bir kaynak eklemek için sadece BaseConnector'ı kalıt al.
"""
from abc import ABC, abstractmethod



# ── Custom Exceptions ───────────────────────────────────────────────────────

class DQConnectionError(Exception):
    """Raised when connector fails to connect."""
    pass


class DQCheckError(Exception):
    """Raised when check execution fails."""
    pass

from typing import Dict, List, Any, Optional, Union


class BaseConnector(ABC):
    """Tüm connector'ların uyması gereken arayüz."""

    @abstractmethod
    def connect(self) -> None:
        """Bağlantıyı aç."""

    @abstractmethod
    def execute(self, query: str) -> list[dict[str, Any]]:
        """Sorgu çalıştır, satırları dict listesi olarak döndür."""

    @abstractmethod
    def close(self) -> None:
        """Bağlantıyı kapat."""

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *_):
        self.close()


# ── PostgreSQL ──────────────────────────────────────────────────────────────

class PostgresConnector(BaseConnector):
    def __init__(self, host: str, port: int, database: str,
                 user: str, password: str):
        self.dsn = dict(host=host, port=port, dbname=database,
                        user=user, password=password)
        self._conn = None

    def connect(self):
        import psycopg2
        import psycopg2.extras
        self._conn = psycopg2.connect(**self.dsn)

    def execute(self, query: str) -> list[dict]:
        import psycopg2.extras
        with self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query)
            return [dict(r) for r in cur.fetchall()]

    def close(self):
        if self._conn:
            self._conn.close()


# ── BigQuery ────────────────────────────────────────────────────────────────

class BigQueryConnector(BaseConnector):
    def __init__(self, project: str, dataset: str):
        self.project = project
        self.dataset = dataset
        self._client = None

    def connect(self):
        from google.cloud import bigquery
        self._client = bigquery.Client(project=self.project)

    def execute(self, query: str) -> list[dict]:
        rows = self._client.query(query).result()
        return [dict(r) for r in rows]

    def close(self):
        if self._client:
            self._client.close()


# ── CSV / dosya tabanlı ─────────────────────────────────────────────────────

class CsvConnector(BaseConnector):
    """DuckDB ile CSV/Parquet/JSON okur — SQL destekli."""

    def __init__(self, path: str):
        self.path = path
        self._conn = None

    def connect(self):
        import duckdb
        self._conn = duckdb.connect()
        # Dosyayı 'tablo' olarak kaydet
        self._conn.execute(f"CREATE VIEW source AS SELECT * FROM read_csv_auto('{self.path}')")

    def execute(self, query: str) -> list[dict]:
        result = self._conn.execute(query).fetchdf()
        return result.to_dict(orient="records")

    def close(self):
        if self._conn:
            self._conn.close()


# ── MySQL ────────────────────────────────────────────────────────────────────

class MySQLConnector(BaseConnector):
    """
    pymysql tabanlı MySQL connector.

    TOML örneği:
        [source]
        type     = "mysql"
        host     = "host.docker.internal"
        port     = 3306
        database = "mydb"
        user     = "root"
        password = "root"
        table    = "orders"
    """

    def __init__(self, host: str, port: int = 3306,
                 database: str = "", user: str = "root",
                 password: str = "", table: str = "source"):
        self.config = dict(
            host=host, port=int(port), db=database,
            user=user, password=password, charset="utf8mb4",
        )
        self.table = table
        self._conn = None

    def connect(self):
        try:
            import pymysql
            import pymysql.cursors
        except ImportError:
            raise ImportError("pip install pymysql")
        self._conn = pymysql.connect(
            **self.config,
            cursorclass=pymysql.cursors.DictCursor,
        )

    def execute(self, query: str) -> list:
        if self.table and self.table != "source":
            query = query.replace("FROM source", f"FROM {self.table}")
            query = query.replace("from source", f"from {self.table}")
        with self._conn.cursor() as cur:
            cur.execute(query)
            return [dict(r) for r in cur.fetchall()]

    def close(self):
        if self._conn:
            self._conn.close()

    def test_connection(self) -> dict:
        try:
            self.connect()
            db = self.config["db"]
            tables = self.execute(
                f"SELECT table_name FROM information_schema.tables "
                f"WHERE table_schema = '{db}'"
            )
            self.close()
            return {
                "success": True,
                "database": db,
                "tables": [t.get("table_name") or t.get("TABLE_NAME") for t in tables],
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


# ── Oracle ───────────────────────────────────────────────────────────────────

class OracleConnector(BaseConnector):
    """
    cx_Oracle tabanlı Oracle connector.

    Kurulum:
        pip install cx_Oracle
        # Oracle Instant Client kurulu olmalı

    TOML örneği:
        [source]
        type     = "oracle"
        host     = "localhost"
        port     = 1521
        service  = "FREEPDB1"   # veya sid = "XE"
        user     = "system"
        password = "oracle"
        table    = "orders"
    """

    def __init__(self, host: str, port: int = 1521,
                 service: str = "", service_name: str = "", sid: str = "",
                 user: str = "system", password: str = "",
                 table: str = "source"):
        self.host         = host
        self.port         = int(port)
        self.service_name = service_name or service
        self.service      = self.service_name
        self.sid          = sid
        self.user     = user
        self.password = password
        self.table    = table
        self._conn    = None

    def connect(self):
        try:
            import cx_Oracle
        except ImportError:
            raise ImportError("pip install cx_Oracle")

        if self.service:
            dsn = cx_Oracle.makedsn(self.host, self.port,
                                    service_name=self.service)
        else:
            dsn = cx_Oracle.makedsn(self.host, self.port,
                                    sid=self.sid or "XE")

        self._conn = cx_Oracle.connect(
            user=self.user, password=self.password, dsn=dsn
        )

    def execute(self, query: str) -> list:
        if self.table and self.table != "source":
            query = query.replace("FROM source", f"FROM {self.table}")
            query = query.replace("from source", f"from {self.table}")

        cursor = self._conn.cursor()
        cursor.execute(query)
        cols = [d[0].lower() for d in cursor.description]
        rows = cursor.fetchall()
        cursor.close()
        return [dict(zip(cols, row)) for row in rows]

    def close(self):
        if self._conn:
            self._conn.close()

    def test_connection(self) -> dict:
        try:
            self.connect()
            rows = self.execute(
                "SELECT table_name FROM user_tables ORDER BY table_name"
            )
            self.close()
            return {
                "success": True,
                "user": self.user,
                "tables": [r.get("table_name") for r in rows],
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

class MongoConnector(BaseConnector):
    """MongoDB connector for DQ checks."""

    def __init__(self, host: str, port: int = 27017, database: str = "test",
                 username: Optional[str] = None, password: Optional[str] = None,
                 **kwargs):
        """
        Initialize MongoDB connector.

        Args:
            host: MongoDB host
            port: MongoDB port (default 27017)
            database: Database name
            username: Optional authentication username
            password: Optional authentication password
        """
        self.host = host
        self.port = port
        self.database = database
        self.username = username
        self.password = password
        self.client = None
        self.db = None

    def connect(self) -> None:
        """Establish MongoDB connection."""
        try:
            from pymongo import MongoClient
            
            if self.username and self.password:
                uri = f"mongodb://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
            else:
                uri = f"mongodb://{self.host}:{self.port}/{self.database}"
            
            self.client = MongoClient(uri, serverSelectionTimeoutMS=5000)
            self.db = self.client[self.database]
            # Test bağlantı
            self.client.admin.command('ping')
        except ImportError:
            raise DQConnectionError("pymongo not installed. Run: pip install pymongo")
        except Exception as e:
            raise DQConnectionError(f"MongoDB connection failed: {e}")

    def close(self) -> None:
        """Close MongoDB connection."""
        if self.client:
            self.client.close()
            self.client = None
            self.db = None

    def execute(self, query):
        """Execute MongoDB query (aggregation pipeline or find)."""
        if not self.db:
            raise DQCheckError("MongoDB not connected. Call connect() first.")
        
        if isinstance(query, str):
            raise DQCheckError("MongoDB requires dict query, not string.")
        
        if not isinstance(query, dict):
            raise DQCheckError(f"Query must be dict, got {type(query)}")
        
        collection_name = query.get("collection")
        if not collection_name:
            raise DQCheckError("Query dict must contain 'collection' key")
        
        collection = self.db.get(collection_name, {}) if isinstance(self.db, dict) else self.db[collection_name]
        
        # Pipeline-based (aggregation)
        if "pipeline" in query:
            pipeline = query["pipeline"]
            try:
                result = list(collection.aggregate(pipeline))
                return result
            except Exception as e:
                raise DQCheckError(f"MongoDB aggregation failed: {e}")
        
        # Find-based (simple filter)
        elif "filter" in query:
            filter_dict = query["filter"]
            try:
                result = list(collection.find(filter_dict))
                # ObjectId objects cannot be JSON serialized; convert to string
                for doc in result:
                    if "_id" in doc and hasattr(doc["_id"], "__str__"):
                        doc["_id"] = str(doc["_id"])
                return result
            except Exception as e:
                raise DQCheckError(f"MongoDB find failed: {e}")
        
        else:
            raise DQCheckError("Query dict must contain 'pipeline' or 'filter' key")

    def test_connection(self) -> bool:
        """Test MongoDB connection."""
        try:
            self.connect()
            self.close()
            return True
        except DQConnectionError:
            return False

        try:
            from pymongo import MongoClient
            
            if self.username and self.password:
                uri = f"mongodb://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
            else:
                uri = f"mongodb://{self.host}:{self.port}/{self.database}"
            
            self.client = MongoClient(uri, serverSelectionTimeoutMS=5000)
            self.db = self.client[self.database]
            # Test bağlantı
            self.client.admin.command('ping')
        except ImportError:
            raise DQConnectionError("pymongo not installed. Run: pip install pymongo")
        except Exception as e:
            raise DQConnectionError(f"MongoDB connection failed: {e}")

    def close(self) -> None:
        """Close MongoDB connection."""
        if self.client:
            self.client.close()
            self.client = None
            self.db = None

    def execute(self, query: Union[str, Dict[str, Any]]) -> Union[str, dict, list]:
        """
        Execute MongoDB query (aggregation pipeline or find).
        
        Args:
            query: Dict with 'collection' + 'pipeline' or 'filter'
                   Example: {"collection": "users", "pipeline": [...]}
                   Or: {"collection": "users", "filter": {"status": "active"}}
        
        Returns:
            Query result as dict or list
        """
        if not self.db:
            raise DQCheckError("MongoDB not connected. Call connect() first.")
        
        if isinstance(query, str):
            raise DQCheckError("MongoDB requires dict query, not string.")
        
        if not isinstance(query, dict):
            raise DQCheckError(f"Query must be dict, got {type(query)}")
        
        collection_name = query.get("collection")
        if not collection_name:
            raise DQCheckError("Query dict must contain 'collection' key")
        
        collection = self.db.get(collection_name, {}) if isinstance(self.db, dict) else self.db[collection_name]
        
        # Pipeline-based (aggregation)
        if "pipeline" in query:
            pipeline = query["pipeline"]
            try:
                result = list(collection.aggregate(pipeline))
                return result
            except Exception as e:
                raise DQCheckError(f"MongoDB aggregation failed: {e}")
        
        # Find-based (simple filter)
        elif "filter" in query:
            filter_dict = query["filter"]
            try:
                result = list(collection.find(filter_dict))
                # ObjectId objects cannot be JSON serialized; convert to string
                for doc in result:
                    if "_id" in doc and hasattr(doc["_id"], "__str__"):
                        doc["_id"] = str(doc["_id"])
                return result
            except Exception as e:
                raise DQCheckError(f"MongoDB find failed: {e}")
        
        else:
            raise DQCheckError("Query dict must contain 'pipeline' or 'filter' key")

    def test_connection(self) -> bool:
        """Test MongoDB connection."""
        try:
            self.connect()
            self.close()
            return True
        except DQConnectionError:
            return False

# ── SqlAlchemy (evrensel connector) ──────────────────────────────────────────

class SqlAlchemyConnector(BaseConnector):
    """
    SQLAlchemy tabanlı evrensel connector.
    SQLite, MSSQL, Snowflake, Redshift, Teradata vb. her şey desteklenir.

    Kurulum:
        pip install sqlalchemy
        pip install pyodbc          # MSSQL için
        pip install snowflake-sqlalchemy  # Snowflake için

    TOML örneği:
        [source]
        type = "sqlalchemy"
        url  = "mssql+pyodbc://user:pass@server/db?driver=ODBC+Driver+17"
        table = "orders"

        # SQLite için:
        url = "sqlite:///mydb.sqlite"

        # Snowflake için:
        url = "snowflake://user:pass@account/db/schema"
    """

    def __init__(
        self,
        url: str | None = None,
        table: str = "source",
        dialect: str | None = None,
        host: str | None = None,
        port: int | None = None,
        database: str | None = None,
        user: str | None = None,
        password: str | None = None,
    ):
        if url:
            self.url = url
        elif dialect:
            from sqlalchemy.engine import URL
            self.url = str(URL.create(
                drivername=dialect,
                username=user or None,
                password=password or None,
                host=host or None,
                port=int(port) if port else None,
                database=database,
            ))
        else:
            raise ValueError("url veya dialect parametresi zorunludur")
        self.table = table
        self._conn = None
        self._engine = None

    def connect(self):
        try:
            from sqlalchemy import create_engine, text
            self._engine = create_engine(self.url)
            self._conn   = self._engine.connect()
        except ImportError:
            raise ImportError("pip install sqlalchemy")

    def execute(self, query: str) -> list:
        from sqlalchemy import text

        if self.table and self.table != "source":
            query = query.replace("FROM source", f"FROM {self.table}")
            query = query.replace("from source", f"from {self.table}")

        result = self._conn.execute(text(query))
        cols   = list(result.keys())
        return [dict(zip(cols, row)) for row in result.fetchall()]

    def close(self):
        if self._conn:
            self._conn.close()
        if self._engine:
            self._engine.dispose()

    def test_connection(self) -> dict:
        try:
            self.connect()
            rows = self.execute("SELECT 1 as test")
            self.close()
            return {"success": True, "url": self.url.split("@")[-1], "dialect": self.url.split("://")[0].split("+")[0]}
        except Exception as e:
            return {"success": False, "error": str(e)}


# ── Connector fabrikası ──────────────────────────────────────────────────────

CONNECTOR_REGISTRY: dict[str, type[BaseConnector]] = {
    "postgres":   PostgresConnector,
    "bigquery":   BigQueryConnector,
    "mysql":      MySQLConnector,
    "csv":        CsvConnector,
    "oracle":     OracleConnector,
    "sqlalchemy": SqlAlchemyConnector,
    "mongo": MongoConnector,
}


def build_connector(config: dict) -> BaseConnector:
    """
    Config dict'ten doğru connector'ı üretir.

    Örnek:
        build_connector({"type": "postgres", "host": "localhost", ...})
    """
    kind = config.pop("type")
    cls = CONNECTOR_REGISTRY.get(kind)
    if cls is None:
        raise ValueError(f"Bilinmeyen connector tipi: '{kind}'. "
                         f"Desteklenenler: {list(CONNECTOR_REGISTRY)}")
    return cls(**config)
