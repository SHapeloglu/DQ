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
        """`with` bloğuna girerken çağrılır. Bağlantıyı açar ve nesnenin kendisini döndürür."""
        self.connect()
        return self

    def __exit__(self, *_):
        """`with` bloğu bittiğinde (hata olsa bile) çağrılır. Bağlantıyı kapatır."""
        self.close()


# ── PostgreSQL ──────────────────────────────────────────────────────────────

class PostgresConnector(BaseConnector):
    """PostgreSQL veritabanına bağlanan connector. Sorgu sonuçlarını sütun adlı sözlükler olarak verir."""
    def __init__(self, host: str, port: int, database: str,
                 user: str, password: str):
        """
        Bağlantı bilgilerini saklar, ama henüz bağlanmaz. Bağlantı `connect()` ile açılır.
        Şifre burada tutulur; loglara ya da hata mesajlarına yazılmamalıdır.
        """
        self.dsn = dict(host=host, port=port, dbname=database,
                        user=user, password=password)
        self._conn = None

    def connect(self):
        """
        PostgreSQL bağlantısını açar. psycopg2 kütüphanesi yoksa Python hatası oluşur.
        Kütüphaneyi dosyanın en üstünde değil, burada içeri aktarırız; böylece yalnız bu kaynak kullanılınca gerekir.
        """
        import psycopg2
        import psycopg2.extras
        self._conn = psycopg2.connect(**self.dsn)

    def execute(self, query: str) -> list[dict]:
        """
        Verilen SQL sorgusunu çalıştırır. Dönen satırları `{sütun: değer}` sözlüklerinden oluşan liste olarak verir.
        Bağlantı açık değilse hata verir.
        """
        import psycopg2.extras
        with self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query)
            return [dict(r) for r in cur.fetchall()]

    def close(self):
        """Veritabanı bağlantısını kapatır. Bağlantı hiç açılmadıysa bir şey yapmaz."""
        if self._conn:
            self._conn.close()


# ── BigQuery ────────────────────────────────────────────────────────────────

class BigQueryConnector(BaseConnector):
    """Google BigQuery'ye bağlanan connector. Proje ve veri seti adını saklar; kimlik bilgileri Google kütüphanesinin ortam ayarlarından okunur."""
    def __init__(self, project: str, dataset: str):
        """BigQuery proje ve veri seti adlarını saklar. Bağlantı henüz açılmaz, `connect()` çağrılmalıdır."""
        self.project = project
        self.dataset = dataset
        self._client = None

    def connect(self):
        """BigQuery istemcisini (client) oluşturur. Kimlik doğrulama ortam değişkenlerinden (servis hesabı vb.) yapılır."""
        from google.cloud import bigquery
        self._client = bigquery.Client(project=self.project)

    def execute(self, query: str) -> list[dict]:
        """SQL sorgusunu BigQuery'de çalıştırır ve sonuç satırlarını sözlük listesi olarak döndürür. Sorgu bitene kadar bekler."""
        rows = self._client.query(query).result()
        return [dict(r) for r in rows]

    def close(self):
        """BigQuery istemcisini kapatır. İstemci yoksa bir şey yapmaz."""
        if self._client:
            self._client.close()


# ── CSV / dosya tabanlı ─────────────────────────────────────────────────────

class CsvConnector(BaseConnector):
    # TODO(kontrol): Bu açıklama Parquet/JSON diyor, ama `connect()` yalnız `read_csv_auto` kullanıyor. Parquet/JSON dosyası verilirse okuma hata verebilir; kod doğrulanmalı.
    """DuckDB ile CSV/Parquet/JSON okur — SQL destekli."""

    def __init__(self, path: str):
        """CSV, Parquet veya JSON dosyasının yolunu saklar. Dosya `connect()` içinde DuckDB'ye bağlanır."""
        self.path = path
        self._conn = None

    def connect(self):
        """
        DuckDB bağlantısı açar ve dosyayı `source` adlı bir görünüm (view) olarak kaydeder. Böylece sorgularda `FROM source` yazılabilir.
        Dosya `read_csv_auto` ile okunur; ayraç ve sütun türleri DuckDB tarafından otomatik tahmin edilir.
        """
        import duckdb
        self._conn = duckdb.connect()
        # Dosyayı 'tablo' olarak kaydet
        # DİKKAT: dosya yolu doğrudan SQL metnine ekleniyor. Yolda tek tırnak olursa sorgu bozulur; yol kullanıcıdan geliyorsa dikkatli olun.
        self._conn.execute(f"CREATE VIEW source AS SELECT * FROM read_csv_auto('{self.path}')")

    def execute(self, query: str) -> list[dict]:
        """SQL sorgusunu DuckDB'de çalıştırır. Sonucu pandas tablosuna çevirip satır sözlükleri listesi olarak döndürür."""
        result = self._conn.execute(query).fetchdf()
        return result.to_dict(orient="records")

    def close(self):
        """DuckDB bağlantısını kapatır. Bağlantı yoksa bir şey yapmaz."""
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
        """
        MySQL bağlantı ayarlarını hazırlar. `charset=utf8mb4` Türkçe ve emoji dahil her karakterin doğru saklanması içindir.
        `table` varsayılan olarak `source`; SQL'deki `FROM source` ifadesi bu tablo adıyla değiştirilir.
        """
        self.config = dict(
            host=host, port=int(port), db=database,
            user=user, password=password, charset="utf8mb4",
        )
        self.table = table
        self._conn = None

    def connect(self):
        """
        MySQL bağlantısını açar. pymysql kurulu değilse anlamlı bir ImportError verir.
        Bağlantı sonuçları DictCursor ile sözlük olarak alır.
        """
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
        # Tablo adı `source` değilse, sorgudaki `FROM source` yazımını gerçek tablo adıyla değiştiriyoruz.
        """
        SQL sorgusunu çalıştırır. Önce sorgudaki `FROM source` ifadesini, ayarlanmış gerçek tablo adıyla değiştirir.
        Sonuçları sözlük listesi olarak döndürür.
        """
        if self.table and self.table != "source":
            query = query.replace("FROM source", f"FROM {self.table}")
            query = query.replace("from source", f"from {self.table}")
        with self._conn.cursor() as cur:
            cur.execute(query)
            return [dict(r) for r in cur.fetchall()]

    def close(self):
        """MySQL bağlantısını kapatır. Bağlantı yoksa bir şey yapmaz."""
        if self._conn:
            self._conn.close()

    def test_connection(self) -> dict:
        """
        Bağlantıyı test eder: bağlanır, veritabanındaki tablo adlarını listeler ve kapatır.
        Başarılıysa `success=True` ve tablo listesi, hata olursa `success=False` ve hata metni döner. Hata fırlatmaz.
        """
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
        """
        Oracle bağlantı ayarlarını saklar. `service` (servis adı) veya `sid` ile bağlanılabilir; ikisi de boşsa sid='XE' kullanılır.
        `service_name` ve `service` aynı değeri tutar; eski ayar adlarıyla uyumluluk için iki isim de vardır.
        """
        self.host         = host
        self.port         = int(port)
        self.service_name = service_name or service
        # Geriye dönük uyumluluk için `service` alanı da aynı değeri taşır.
        self.service      = self.service_name
        self.sid          = sid
        self.user     = user
        self.password = password
        self.table    = table
        self._conn    = None

    def connect(self):
        """
        Oracle bağlantısını açar. Önce bağlantı adresini (DSN) oluşturur: servis adı varsa onu, yoksa SID'i kullanır.
        cx_Oracle kurulu değilse ImportError verir. Oracle Instant Client'ın kurulu olması gerekir.
        """
        try:
            import cx_Oracle
        except ImportError:
            raise ImportError("pip install cx_Oracle")

        if self.service:
            # Oracle'da iki bağlantı türü var: servis adı (modern) ya da SID (eski). Servis adı varsa onu, yoksa SID'i kullanırız.
            dsn = cx_Oracle.makedsn(self.host, self.port,
                                    service_name=self.service)
        else:
            dsn = cx_Oracle.makedsn(self.host, self.port,
                                    sid=self.sid or "XE")

        self._conn = cx_Oracle.connect(
            user=self.user, password=self.password, dsn=dsn
        )

    def execute(self, query: str) -> list:
        # Tablo adı `source` değilse, sorgudaki `FROM source` yazımını gerçek tablo adıyla değiştiriyoruz.
        """
        SQL sorgusunu çalıştırır ve sonuçları sözlük listesi olarak döndürür. Sütun adları küçük harfe çevrilir; böylece diğer connector'larla aynı görünür.
        Başta `FROM source` değişimi MySQL ile aynı mantıktadır.
        """
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
        """Oracle bağlantısını kapatır. Bağlantı yoksa bir şey yapmaz."""
        if self._conn:
            self._conn.close()

    def test_connection(self) -> dict:
        """
        Bağlantıyı test eder: kullanıcının tablolarını (`user_tables`) listeler ve kapatır.
        Başarılıysa `success=True`, hata olursa `success=False` ve hata metni döner. Hata fırlatmaz.
        """
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
                # DİKKAT: şifre URI'ye olduğu gibi yazılıyor. Şifrede @, : veya / gibi özel karakter varsa adres bozulur (URL kodlaması yapılmaz).
                uri = f"mongodb://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
            else:
                uri = f"mongodb://{self.host}:{self.port}/{self.database}"
            
            # 5000 ms = 5 saniye. Sunucu bu sürede cevap vermezse hata verilir; sonsuza kadar beklenmez.
            self.client = MongoClient(uri, serverSelectionTimeoutMS=5000)
            self.db = self.client[self.database]
            # Test bağlantı
            # MongoClient ilk istekte bağlandığı için, bağlantıyı burada 'ping' ile gerçekten deniyoruz.
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

    # DİKKAT: Bu sınıfta `connect`, `close`, `execute`, `test_connection` metotları iki kez tanımlanmış.
    # Python'da sonraki tanım öncekini ezer; aşağıdaki kopya geçerlidir. Bu ilk `test_connection` içinde `return`den sonra ulaşılamayan kod var.
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
        """
        SQLAlchemy için bağlantı adresini (URL) hazırlar. İki yol vardır:
        1) `url` doğrudan verilir, 2) `dialect` ve host/kullanıcı gibi parçalar verilirse URL bunlardan oluşturulur.
        İkisi de yoksa ValueError fırlatılır.
        """
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
        """SQLAlchemy motorunu (engine) oluşturur ve bağlantıyı açar. sqlalchemy kurulu değilse ImportError verir."""
        try:
            from sqlalchemy import create_engine, text
            self._engine = create_engine(self.url)
            self._conn   = self._engine.connect()
        except ImportError:
            raise ImportError("pip install sqlalchemy")

    def execute(self, query: str) -> list:
        """
        SQL sorgusunu çalıştırır ve sonuçları sözlük listesi olarak döndürür. Sorgu `text()` ile sarılır; SQLAlchemy bunu ham SQL olarak işler.
        `FROM source` ifadesi ayarlanmış tablo adıyla değiştirilir.
        """
        from sqlalchemy import text

        # Tablo adı `source` değilse, sorgudaki `FROM source` yazımını gerçek tablo adıyla değiştiriyoruz.
        if self.table and self.table != "source":
            query = query.replace("FROM source", f"FROM {self.table}")
            query = query.replace("from source", f"from {self.table}")

        # `text()` sarmalayıcısı sorguyu SQLAlchemy'nin ham SQL olarak işlemesini sağlar.
        result = self._conn.execute(text(query))
        cols   = list(result.keys())
        return [dict(zip(cols, row)) for row in result.fetchall()]

    def close(self):
        """Bağlantıyı kapatır ve motoru (engine) serbest bırakır (dispose). İkisi de yoksa bir şey yapmaz."""
        if self._conn:
            self._conn.close()
        if self._engine:
            self._engine.dispose()

    def test_connection(self) -> dict:
        """
        Bağlantıyı test eder: `SELECT 1` çalıştırır ve kapatır.
        Başarılıysa `success=True`, URL'nin '@' sonrası kısmı (sunucu/veritabanı) ve dialect adı döner. Hata olursa `success=False` ve metin döner. Hata fırlatmaz.
        """
        try:
            self.connect()
            rows = self.execute("SELECT 1 as test")
            self.close()
            # Şifre ve kullanıcı adı yanıtta görünmesin diye URL'nin '@' öncesi kısmı atılır.
            return {"success": True, "url": self.url.split("@")[-1], "dialect": self.url.split("://")[0].split("+")[0]}
        except Exception as e:
            return {"success": False, "error": str(e)}


# ── Connector fabrikası ──────────────────────────────────────────────────────

# Kaynak tipi adından (TOML'daki `type`) connector sınıfına eşleşme tablosu. Yeni bir connector eklerseniz buraya da yazmalısınız.
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
    # DİKKAT: `pop` çağıranın sözlüğünden "type" anahtarını siler. Aynı sözlüğü ikinci kez kullanırsanız "type" yoktur.
    kind = config.pop("type")
    # Parola şifreli (enc:) saklanmış olabilir; bağlayıcıya her zaman çözülmüş değer gider.
    from sifre_kasasi import decrypt_config_password
    decrypt_config_password(config)
    cls = CONNECTOR_REGISTRY.get(kind)
    if cls is None:
        raise ValueError(f"Bilinmeyen connector tipi: '{kind}'. "
                         f"Desteklenenler: {list(CONNECTOR_REGISTRY)}")
    return cls(**config)
