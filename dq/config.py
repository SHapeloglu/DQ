"""
Config parser — TOML dosyasını veya Python dict'i Check listesine çevirir.

TOML örneği (checks.toml):
─────────────────────────────────────────────
[source]
type     = "postgres"
host     = "localhost"
port     = 5432
database = "mydb"
user     = "admin"
password = "secret"

[[checks]]
name     = "Siparişler boş olmamalı"
query    = "SELECT COUNT(*) FROM orders"
assert   = "greater_than"
value    = 0
tags     = ["critical"]

[[checks]]
name     = "Null müşteri oranı < %5"
query    = "SELECT COUNT(*) * 100.0 / COUNT(1) FROM orders WHERE customer_id IS NULL"
assert   = "less_than"
value    = 5.0
tags     = ["quality"]
─────────────────────────────────────────────
"""

from __future__ import annotations
import os
import tomllib                        # Python 3.11+ yerleşik; 3.10 için: pip install tomli
from pathlib import Path
from typing import Any

from dq.engine import (
    Check,
    less_than, greater_than, between, equals,
    row_count_at_least, row_count_between, is_not_null, referential_integrity,
    completeness_ratio, statistical_anomaly, schema_drift, schema_check, duplicate_row, custom_sql, volume_anomaly, zscore_anomaly,
)
from dq.connectors import build_connector


# Desteklenen assertion adları → fabrika fonksiyonları
_ASSERTION_MAP = {
    "less_than":           lambda v: less_than(v),
    "greater_than":        lambda v: greater_than(v),
    "between":             lambda v: between(v[0], v[1]),
    "equals":              lambda v: equals(v),
    "row_count_at_least":  lambda v: row_count_at_least(v),
    "is_not_null":         lambda _: is_not_null,
    "row_count_between":   lambda v: row_count_between(v[0], v[1]),
    "referential_integrity": lambda v: referential_integrity(v[0], v[1]),
    "completeness_ratio":    lambda v: completeness_ratio(float(v)),
    "statistical_anomaly":   lambda v: statistical_anomaly(float(v)),
    "schema_drift":          lambda v: schema_drift(int(v)),
    "schema_check":          lambda v: schema_check(v if isinstance(v, dict) else {}),
    "duplicate_row":          lambda v: duplicate_row(int(v) if v is not None else 0),
    "custom_sql":             lambda v: custom_sql(v),
    "volume_anomaly":         lambda v: volume_anomaly(float(v) if v is not None else 50.0),
    "zscore_anomaly":         lambda v: zscore_anomaly(str(v) if not isinstance(v, str) else v, store=None, max_zscore=3.0),
}


def _parse_check(raw: dict[str, Any]) -> Check:
    assertion_name = raw["assert"]
    assertion_val  = raw.get("value")

    factory = _ASSERTION_MAP.get(assertion_name)
    if factory is None:
        raise ValueError(
            f"Bilinmeyen assertion: '{assertion_name}'. "
            f"Geçerliler: {list(_ASSERTION_MAP)}"
        )

    assertion_fn = factory(assertion_val)

    return Check(
        name      = raw["name"],
        query     = raw["query"],
        assertion = assertion_fn,
        expected  = f"{assertion_name}({assertion_val})",
        tags      = raw.get("tags", []),
    )


class SodaConfig:
    """
    Tek giriş noktası: TOML dosyası veya Python dict'ten
    connector + check listesi üretir.
    """

    def __init__(self, raw: dict[str, Any]):
        self._raw = raw

    # ── Yükleyiciler ──────────────────────────────────────────────────────

    # ── Env variable çözümleyici ──────────────────────────────────────────
    @staticmethod
    def _resolve_env_vars(raw: dict) -> dict:
        """[source] bloğundaki credentials'ı çözer.
        Öncelik sırası:
          1. DQ_{TYPE}_{FIELD} env variable (override)
          2. TOML'daki 'secret:<KEY>' prefix → secrets_loader.get_secret(KEY)
          3. TOML'daki değer olduğu gibi kullanılır
        """
        try:
            from secrets_loader import get_secret
        except ImportError:
            get_secret = lambda k, d="": os.getenv(k, d)
        src = raw.get("source", {})
        db_type = src.get("type", "").upper()
        # secret: prefix çözümle
        for field in ("user", "password", "host", "port", "database"):
            val = src.get(field)
            if isinstance(val, str) and val.startswith("secret:"):
                secret_key = val[len("secret:"):]
                src[field] = get_secret(secret_key, "")
        # DQ_{TYPE}_{FIELD} env override (eskiden gelen davranış korunur)
        for field in ("user", "password", "host", "port", "database"):
            env_key = f"DQ_{db_type}_{field.upper()}"
            val = os.getenv(env_key)
            if val is not None:
                src[field] = int(val) if field == "port" else val
        raw["source"] = src
        return raw

    @classmethod
    def from_toml(cls, path: str | Path) -> "SodaConfig":
        with open(path, "rb") as f:
            raw = tomllib.load(f)
        return cls(cls._resolve_env_vars(raw))

    @classmethod
    def from_dict(cls, data: dict) -> "SodaConfig":
        return cls(data)

    # ── Üreticiler ────────────────────────────────────────────────────────

    def build_connector(self):
        source_cfg = dict(self._raw["source"])   # kopyala, pop'dan etkilenmesin
        return build_connector(source_cfg)

    def build_checks(self) -> list[Check]:
        return [_parse_check(c) for c in self._raw.get("checks", [])]
