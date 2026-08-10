"""
database.py — MySQL bağlantısı ve tablo şeması.

Kurulum:
    pip install pymysql python-dotenv
"""

from __future__ import annotations
import os
import pymysql
import pymysql.cursors
from dotenv import load_dotenv
from secrets_loader import get_secret

load_dotenv()

DB_CONFIG = {
    "host":     get_secret("DB_HOST", "localhost"),
    "port":     int(get_secret("DB_PORT", "3306")),
    "user":     get_secret("DB_USER", "root"),
    "password": get_secret("DB_PASSWORD", "root"),
    "db":       get_secret("DB_NAME", "dq"),
    "charset":  "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
}


import threading
from queue import Queue, Empty

class _DBPool:
    """Thread-safe MySQL bağlantı havuzu."""
    def __init__(self, config: dict, size: int = 5):
        self._config = config
        self._pool: Queue = Queue(maxsize=size)
        self._lock = threading.Lock()
        for _ in range(size):
            self._pool.put(self._new_conn())

    def _new_conn(self):
        return pymysql.connect(**self._config)

    def get(self):
        try:
            conn = self._pool.get_nowait()
            conn.ping(reconnect=True)
            return conn
        except Empty:
            return self._new_conn()

    def release(self, conn):
        try:
            self._pool.put_nowait(conn)
        except Exception:
            conn.close()

_pool: _DBPool | None = None
_pool_lock = threading.Lock()

def _get_pool() -> _DBPool:
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:
                _pool = _DBPool(DB_CONFIG, size=5)
    return _pool

def get_conn():
    """Havuzdan bağlantı döndürür; yoksa yeni açar."""
    return _get_pool().get()

def release_conn(conn):
    """Bağlantıyı havuza iade eder."""
    _get_pool().release(conn)


def init_db():
    """Tabloları oluşturur — uygulama başlarken çağrılır."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            # ── Sources ──────────────────────────────────────────────────────
            cur.execute("""
                CREATE TABLE IF NOT EXISTS sources (
                    id          INT AUTO_INCREMENT PRIMARY KEY,
                    name        VARCHAR(100) NOT NULL,
                    type        VARCHAR(20)  NOT NULL,  -- csv, postgres, mysql, bigquery
                    config      JSON         NOT NULL,  -- bağlantı detayları
                    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
            """)

            # ── Checks ───────────────────────────────────────────────────────
            cur.execute("""
                CREATE TABLE IF NOT EXISTS checks (
                    id          INT AUTO_INCREMENT PRIMARY KEY,
                    source_id   INT          NOT NULL,
                    name        VARCHAR(200) NOT NULL,
                    query       TEXT         NOT NULL,
                    assert_type VARCHAR(50)  NOT NULL,  -- greater_than, less_than, between, equals
                    assert_value VARCHAR(100) NOT NULL,  -- "0", "5.0", "[1.0, 10000.0]"
                    tags        VARCHAR(200),            -- "critical,finance"
                    is_active   TINYINT(1) DEFAULT 1,
                    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE CASCADE
                )
            """)

            # ── Runs ─────────────────────────────────────────────────────────
            cur.execute("""
                CREATE TABLE IF NOT EXISTS runs (
                    id          INT AUTO_INCREMENT PRIMARY KEY,
                    source_id   INT,
                    dag_id      VARCHAR(100),
                    task_id     VARCHAR(100),
                    run_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
                    total       INT DEFAULT 0,
                    passed      INT DEFAULT 0,
                    failed      INT DEFAULT 0,
                    status      VARCHAR(20) DEFAULT 'unknown'
                )
            """)

            # ── Run Results ──────────────────────────────────────────────────
            cur.execute("""
                CREATE TABLE IF NOT EXISTS run_results (
                    id          INT AUTO_INCREMENT PRIMARY KEY,
                    run_id      INT NOT NULL,
                    check_id    INT,
                    check_name  VARCHAR(200),
                    passed      TINYINT(1),
                    value_actual VARCHAR(100),
                    expected    VARCHAR(100),
                    message     TEXT,
                    FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE CASCADE
                )
            """)

            # ── Column Profiles ───────────────────────────────────────────────
            cur.execute("""
                CREATE TABLE IF NOT EXISTS column_profiles (
                    id             INT AUTO_INCREMENT PRIMARY KEY,
                    source_id      INT NOT NULL,
                    column_name    VARCHAR(100) NOT NULL,
                    col_type       VARCHAR(20),
                    row_count      INT DEFAULT 0,
                    null_count     INT DEFAULT 0,
                    null_pct       FLOAT DEFAULT 0,
                    distinct_count INT DEFAULT 0,
                    min_val        VARCHAR(100),
                    max_val        VARCHAR(100),
                    avg_val        FLOAT,
                    min_length     INT,
                    max_length     INT,
                    profiled_at    DATETIME,
                    is_pii         TINYINT(1) DEFAULT 0,
                    pii_type       VARCHAR(50),
                    business_name  VARCHAR(100),
                    description    TEXT,
                    owner          VARCHAR(100),
                    tags           VARCHAR(255),
                    FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE CASCADE
                )
            """)

            # ── Rule Library (biriken kural kütüphanesi) ───────────────────────
            cur.execute("""
                CREATE TABLE IF NOT EXISTS rule_library (
                    id                   INT AUTO_INCREMENT PRIMARY KEY,
                    column_name_pattern  VARCHAR(100) NOT NULL,  -- "email", "*_id", "*_date" gibi normalize desen
                    column_type          VARCHAR(20),
                    rule_type            VARCHAR(50)  NOT NULL,  -- not_null, unique, freshness, range, ratio, row_count, custom
                    rule_definition      JSON,                   -- assert_type/assert_value sablonu
                    source_format        VARCHAR(20)  DEFAULT 'sql',  -- sql | toml_contract | wizard_manual
                    times_used           INT DEFAULT 0,
                    times_accepted       INT DEFAULT 0,
                    times_rejected       INT DEFAULT 0,
                    last_used_at         DATETIME,
                    created_at           DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE KEY uq_pattern (column_name_pattern, rule_type)
                )
            """)

        conn.commit()
        print("✓ Veritabanı tabloları hazır")
    finally:
        conn.close()
