"""
toml_import.py — TOML dosyasını parse edip DB'ye kaydeder.
"""

from __future__ import annotations
import json
import re

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib  # type: ignore
    except ImportError:
        raise ImportError("pip install tomli")


def parse_toml(content: bytes) -> dict:
    """TOML bytes'ını dict'e çevirir."""
    return tomllib.loads(content.decode("utf-8"))


_COLUMN_PATTERNS = [
    re.compile(r"\bWHERE\s+(\w+)\s+IS\s+NULL\b", re.I),
    re.compile(r"COUNT\(DISTINCT\s+(\w+)\)", re.I),
    re.compile(r"\bWHERE\s+(\w+)\s*[<>=]", re.I),
]


def _extract_column_from_query(query: str) -> str | None:
    """Ham SQL'den best-effort kolon adı çıkarır (rule_library için)."""
    for pattern in _COLUMN_PATTERNS:
        m = pattern.search(query or "")
        if m:
            return m.group(1)
    return None


def toml_to_db(raw: dict, conn) -> dict:
    """
    TOML dict'ini sources + checks tablolarına kaydeder.

    Returns:
        {"source_id": 1, "check_count": 4}
    """
    source_raw = raw.get("source", {})
    checks_raw = raw.get("checks", [])

    if not source_raw:
        raise ValueError("TOML'da [source] bölümü bulunamadı")

    source_type   = source_raw.get("type", "csv")
    source_config = {k: v for k, v in source_raw.items() if k != "type"}
    source_name   = source_config.get("path", source_type).split("/")[-1]

    with conn.cursor() as cur:
        # Source kaydet
        cur.execute(
            "INSERT INTO sources (name, type, config) VALUES (%s, %s, %s)",
            (source_name, source_type, json.dumps(source_config)),
        )
        source_id = cur.lastrowid

        # Check'leri kaydet
        from profiler import fingerprint_query, record_rule_usage

        for c in checks_raw:
            assert_val = c.get("value", 0)
            # between için liste → JSON string
            if isinstance(assert_val, list):
                assert_val_str = json.dumps(assert_val)
            else:
                assert_val_str = str(assert_val)

            tags_str = ",".join(c.get("tags", []))

            cur.execute("""
                INSERT INTO checks
                    (source_id, name, query, assert_type, assert_value, tags)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                source_id,
                c["name"],
                c["query"],
                c["assert"],
                assert_val_str,
                tags_str,
            ))

            # Rule library'yi besle (best-effort - kolon cikarilamazsa atlanir)
            col_name = _extract_column_from_query(c["query"])
            if col_name:
                rule_type = fingerprint_query(c["query"], c["assert"])
                record_rule_usage(
                    conn, col_name, "", rule_type,
                    {"assert_type": c["assert"], "assert_value": assert_val_str},
                    source_format="toml",
                )

    conn.commit()
    return {"source_id": source_id, "check_count": len(checks_raw)}


def db_to_engine_config(source_id: int, conn) -> dict:
    """
    DB'den source + check'leri okuyup DQ Engine formatına çevirir.
    Airflow operatörü bunu kullanır.
    """
    with conn.cursor() as cur:
        # Source
        cur.execute("SELECT * FROM sources WHERE id = %s", (source_id,))
        source = cur.fetchone()
        if not source:
            raise ValueError(f"Source bulunamadı: {source_id}")

        config = json.loads(source["config"])
        config["type"] = source["type"]

        # Checks
        cur.execute(
            "SELECT * FROM checks WHERE source_id = %s AND is_active = 1",
            (source_id,)
        )
        checks = cur.fetchall()

    return {"source": config, "checks": checks}
