"""
MetricStore — check sonuçlarını zaman serisi olarak saklar.

Backend:
    sqlite  (default) — dışarıdan bağımlılık yok, dev/cache için
    postgres          — merkezi dwh_health_log şeması, production için

Kullanım:
    # SQLite (mevcut davranış)
    store = MetricStore()

    # Postgres
    store = MetricStore(backend="postgres", dsn="postgresql://user:pass@host:5432/dbname")

    store.record("siparis_sayisi", 1420)
    history = store.history("siparis_sayisi", days=30)
"""
from __future__ import annotations
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Literal


# ── SQLite DDL ────────────────────────────────────────────────────────────────

_SQLITE_DDL = """
CREATE TABLE IF NOT EXISTS metrics (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    name    TEXT    NOT NULL,
    value   REAL,
    run_at  TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_metrics_name   ON metrics(name);
CREATE INDEX IF NOT EXISTS idx_metrics_run_at ON metrics(run_at);
"""

# ── Postgres DDL ──────────────────────────────────────────────────────────────

_PG_DDL = """
CREATE SCHEMA IF NOT EXISTS dwh_health_log;
CREATE TABLE IF NOT EXISTS dwh_health_log.dq_metrics (
    id      BIGSERIAL PRIMARY KEY,
    name    TEXT    NOT NULL,
    value   DOUBLE PRECISION,
    run_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_dq_metrics_name   ON dwh_health_log.dq_metrics(name);
CREATE INDEX IF NOT EXISTS idx_dq_metrics_run_at ON dwh_health_log.dq_metrics(run_at);
"""


class MetricStore:
    """
    Çift backend destekli metrik deposu.
    SQLite → dev/local cache
    Postgres → merkezi production kaydı
    """

    def __init__(
        self,
        backend: Literal["sqlite", "postgres"] = "sqlite",
        db_path: str | Path = "dq_metrics.db",
        dsn: str | None = None,
    ) -> None:
        self.backend = backend

        if backend == "postgres":
            if not dsn:
                raise ValueError("Postgres backend için dsn zorunludur.")
            self._init_postgres(dsn)
        else:
            self._init_sqlite(db_path)

    # ── Init ─────────────────────────────────────────────────────────────────

    def _init_sqlite(self, db_path: str | Path) -> None:
        self._conn = sqlite3.connect(str(db_path))
        self._conn.executescript(_SQLITE_DDL)
        self._conn.commit()
        self._pg_conn = None

    def _init_postgres(self, dsn: str) -> None:
        try:
            import psycopg2
            import psycopg2.extras
        except ImportError:
            raise ImportError("pip install psycopg2-binary")
        self._pg_conn = psycopg2.connect(dsn)
        self._conn = None
        with self._pg_conn.cursor() as cur:
            cur.execute(_PG_DDL)
        self._pg_conn.commit()

    # ── Yazma ────────────────────────────────────────────────────────────────

    def record(self, name: str, value: float | None) -> None:
        """Tek bir metrik değerini kaydeder."""
        now = datetime.now(timezone.utc).isoformat()
        if self.backend == "postgres":
            with self._pg_conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO dwh_health_log.dq_metrics (name, value, run_at)"
                    " VALUES (%s, %s, %s)",
                    (name, value, now),
                )
            self._pg_conn.commit()
        else:
            self._conn.execute(
                "INSERT INTO metrics (name, value, run_at) VALUES (?, ?, ?)",
                (name, value, now),
            )
            self._conn.commit()

    def record_results(self, results: list) -> None:
        """CheckResult / AnomalyResult listesini toplu kaydeder."""
        now = datetime.now(timezone.utc).isoformat()
        rows = [
            (r.name, float(r.value) if r.value is not None else None, now)
            for r in results
        ]
        if self.backend == "postgres":
            with self._pg_conn.cursor() as cur:
                cur.executemany(
                    "INSERT INTO dwh_health_log.dq_metrics (name, value, run_at)"
                    " VALUES (%s, %s, %s)",
                    rows,
                )
            self._pg_conn.commit()
        else:
            self._conn.executemany(
                "INSERT INTO metrics (name, value, run_at) VALUES (?, ?, ?)",
                rows,
            )
            self._conn.commit()

    # ── Okuma ────────────────────────────────────────────────────────────────

    def history(self, name: str, days: int = 30) -> list[dict]:
        """Son N günün kayıtlarını döndürür (eskiden yeniye)."""
        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        if self.backend == "postgres":
            with self._pg_conn.cursor() as cur:
                cur.execute(
                    "SELECT run_at, value FROM dwh_health_log.dq_metrics"
                    " WHERE name = %s AND run_at >= %s ORDER BY run_at ASC",
                    (name, since),
                )
                return [{"run_at": str(r[0]), "value": r[1]} for r in cur.fetchall()]
        else:
            cur = self._conn.execute(
                "SELECT run_at, value FROM metrics"
                " WHERE name = ? AND run_at >= ? ORDER BY run_at ASC",
                (name, since),
            )
            return [{"run_at": row[0], "value": row[1]} for row in cur.fetchall()]

    def known_metrics(self) -> list[str]:
        """Tüm benzersiz metrik isimlerini döndürür."""
        if self.backend == "postgres":
            with self._pg_conn.cursor() as cur:
                cur.execute(
                    "SELECT DISTINCT name FROM dwh_health_log.dq_metrics ORDER BY name"
                )
                return [r[0] for r in cur.fetchall()]
        else:
            cur = self._conn.execute(
                "SELECT DISTINCT name FROM metrics ORDER BY name"
            )
            return [row[0] for row in cur.fetchall()]

    # ── Lifecycle ────────────────────────────────────────────────────────────

    def close(self) -> None:
        if self._conn:
            self._conn.close()
        if self._pg_conn:
            self._pg_conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
