"""
MetricStore — check sonuçlarının ölçülen değerlerini zaman serisi olarak saklar.

Depolama: SQLite (dışarıdan bağımlılık yok).
Her kayıt: (metric_name, value, run_at) üçlüsüdür.

Kullanım:
    store = MetricStore("dq_metrics.db")
    store.record("siparis_sayisi", 1420)
    history = store.history("siparis_sayisi", days=30)
"""

from __future__ import annotations
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path


CREATE_SQL = """
CREATE TABLE IF NOT EXISTS metrics (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL,
    value       REAL,
    run_at      TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_metrics_name ON metrics(name);
CREATE INDEX IF NOT EXISTS idx_metrics_run_at ON metrics(run_at);
"""


class MetricStore:
    """Hafif SQLite tabanlı metrik deposu."""

    def __init__(self, db_path: str | Path = "dq_metrics.db"):
        self.db_path = str(db_path)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.executescript(CREATE_SQL)
        self._conn.commit()

    # ── Yazma ────────────────────────────────────────────────────────────────

    def record(self, name: str, value: float | None) -> None:
        """Tek bir metrik değerini şu anki zamana kaydeder."""
        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            "INSERT INTO metrics (name, value, run_at) VALUES (?, ?, ?)",
            (name, value, now),
        )
        self._conn.commit()

    def record_results(self, results) -> None:
        """CheckResult / AnomalyResult listesini toplu kaydeder."""
        now = datetime.now(timezone.utc).isoformat()
        rows = [(r.name, float(r.value) if r.value is not None else None, now)
                for r in results]
        self._conn.executemany(
            "INSERT INTO metrics (name, value, run_at) VALUES (?, ?, ?)", rows
        )
        self._conn.commit()

    # ── Okuma ─────────────────────────────────────────────────────────────────

    def history(self, name: str, days: int = 30) -> list[dict]:
        """
        Son N günün kayıtlarını döndürür.

        Returns:
            [{"run_at": "...", "value": 123.4}, ...]  (eskiden yeniye sıralı)
        """
        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        cur = self._conn.execute(
            "SELECT run_at, value FROM metrics "
            "WHERE name = ? AND run_at >= ? ORDER BY run_at ASC",
            (name, since),
        )
        return [{"run_at": row[0], "value": row[1]} for row in cur.fetchall()]

    def known_metrics(self) -> list[str]:
        """Veritabanındaki tüm benzersiz metrik isimlerini döndürür."""
        cur = self._conn.execute("SELECT DISTINCT name FROM metrics ORDER BY name")
        return [row[0] for row in cur.fetchall()]

    def close(self) -> None:
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
