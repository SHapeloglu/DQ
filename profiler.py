"""
profiler.py — veri profiling motoru.

Katman 2: get_columns()  — hızlı kolon listesi
Katman 3: profile_source() — detaylı istatistikler

Her ikisi de aynı connector mimarisini kullanır,
dış bağımlılık yok.
"""

from __future__ import annotations
import json
from datetime import datetime, timezone
from typing import Any


# ── Katman 2: Hızlı kolon çekme ──────────────────────────────────────────────

def get_columns(connector) -> list[str]:
    """
    Tablonun kolon adlarını döndürür.
    LIMIT 0 ile veri çekmeden sadece şema okunur.
    """
    try:
        with connector as conn:
            rows = conn.execute("SELECT * FROM source LIMIT 1")
            if rows:
                return list(rows[0].keys())
            return []
    except Exception as e:
        return []


# ── Katman 3: Detaylı profil ──────────────────────────────────────────────────

NUMERIC_TYPES = {"int", "integer", "float", "double", "decimal",
                 "numeric", "real", "bigint", "smallint", "tinyint"}

STRING_TYPES  = {"varchar", "char", "text", "string", "nvarchar", "nchar"}

DATE_TYPES    = {"date", "datetime", "timestamp", "time"}


def _detect_type(values: list) -> str:
    """Örnek değerlere bakarak kolon tipini tahmin eder."""
    non_null = [v for v in values if v is not None]
    if not non_null:
        return "unknown"

    for v in non_null[:10]:
        try:
            float(v)
            return "numeric"
        except (TypeError, ValueError):
            pass

    for v in non_null[:10]:
        s = str(v)
        if len(s) >= 8 and ("-" in s or "/" in s or ":" in s):
            return "date"

    return "string"


def profile_column(conn, column: str, table: str = "source") -> dict[str, Any]:
    """
    Tek bir kolon için istatistik hesaplar.
    Tip tespitine göre farklı sorgular çalıştırır.
    """
    result = {
        "column":        column,
        "row_count":     0,
        "null_count":    0,
        "null_pct":      0.0,
        "distinct_count": 0,
        "type":          "unknown",
        "min":           None,
        "max":           None,
        "avg":           None,
        "min_length":    None,
        "max_length":    None,
    }

    try:
        # Temel istatistikler
        rows = conn.execute(f"""
            SELECT
                COUNT(*) as row_count,
                COUNT("{column}") as non_null_count,
                COUNT(*) - COUNT("{column}") as null_count
            FROM {table}
        """)
        if rows:
            r = rows[0]
            result["row_count"]   = int(r.get("row_count") or 0)
            result["null_count"]  = int(r.get("null_count") or 0)
            total = result["row_count"]
            result["null_pct"] = round(
                result["null_count"] * 100.0 / total if total > 0 else 0, 2
            )

        # Distinct sayısı
        rows = conn.execute(
            f'SELECT COUNT(DISTINCT "{column}") as dc FROM {table}'
        )
        if rows:
            result["distinct_count"] = int(rows[0].get("dc") or 0)

        # Tip tespiti için örnek değerler
        sample = conn.execute(
            f'SELECT "{column}" FROM {table} WHERE "{column}" IS NOT NULL LIMIT 20'
        )
        values = [r[column] for r in sample] if sample else []
        col_type = _detect_type(values)
        result["type"] = col_type

        # Tipe göre ek istatistikler
        if col_type == "numeric":
            rows = conn.execute(f"""
                SELECT
                    MIN(CAST("{column}" AS FLOAT)) as min_val,
                    MAX(CAST("{column}" AS FLOAT)) as max_val,
                    AVG(CAST("{column}" AS FLOAT)) as avg_val
                FROM {table}
                WHERE "{column}" IS NOT NULL
            """)
            if rows:
                r = rows[0]
                result["min"] = r.get("min_val")
                result["max"] = r.get("max_val")
                result["avg"] = round(float(r.get("avg_val") or 0), 2)

        elif col_type == "string":
            rows = conn.execute(f"""
                SELECT
                    MIN(LENGTH("{column}")) as min_len,
                    MAX(LENGTH("{column}")) as max_len
                FROM {table}
                WHERE "{column}" IS NOT NULL
            """)
            if rows:
                r = rows[0]
                result["min_length"] = r.get("min_len")
                result["max_length"] = r.get("max_len")

        elif col_type == "date":
            rows = conn.execute(f"""
                SELECT
                    MIN("{column}") as min_date,
                    MAX("{column}") as max_date
                FROM {table}
                WHERE "{column}" IS NOT NULL
            """)
            if rows:
                r = rows[0]
                result["min"] = str(r.get("min_date") or "")
                result["max"] = str(r.get("max_date") or "")

    except Exception as e:
        result["error"] = str(e)

    return result


def profile_source(connector, source_id: int, db_conn) -> dict:
    """
    Tüm kolonları profiller, sonuçları DB'ye kaydeder.

    Returns:
        {"source_id": 1, "columns": [...], "profiled_at": "..."}
    """
    columns_data = []

    try:
        with connector as conn:
            # Kolon listesini al
            sample = conn.execute("SELECT * FROM source LIMIT 1")
            if not sample:
                return {"error": "Tablo boş"}

            columns = list(sample[0].keys())

            # Her kolon için profil çalıştır
            for col in columns:
                col_profile = profile_column(conn, col)
                columns_data.append(col_profile)

    except Exception as e:
        return {"error": str(e)}

    # DB'ye kaydet
    profiled_at = datetime.now(timezone.utc).isoformat()
    try:
        with db_conn.cursor() as cur:
            # Önce eski profil verilerini sil
            cur.execute(
                "DELETE FROM column_profiles WHERE source_id = %s",
                (source_id,)
            )
            # Yeni profil verilerini ekle
            for col in columns_data:
                cur.execute("""
                    INSERT INTO column_profiles
                        (source_id, column_name, col_type, row_count,
                         null_count, null_pct, distinct_count,
                         min_val, max_val, avg_val,
                         min_length, max_length, profiled_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (
                    source_id,
                    col["column"],
                    col["type"],
                    col["row_count"],
                    col["null_count"],
                    col["null_pct"],
                    col["distinct_count"],
                    str(col["min"]) if col["min"] is not None else None,
                    str(col["max"]) if col["max"] is not None else None,
                    col["avg"],
                    col["min_length"],
                    col["max_length"],
                    profiled_at,
                ))
        db_conn.commit()
    except Exception as e:
        return {"error": f"DB kayıt hatası: {e}",
                "columns": columns_data}

    return {
        "source_id":   source_id,
        "profiled_at": profiled_at,
        "columns":     columns_data,
    }


# ── Kural önerileri ───────────────────────────────────────────────────────────

def suggest_rules(columns_data: list[dict], conn=None) -> list[dict]:
    """
    Profil sonuçlarına bakarak kural önerileri üretir.
    Wizard'a beslenir.

    conn verilirse (rule_library erişimi için), istatistiksel önerilerin
    yanına biriken kütüphaneden gelen önerileri de ekler ve varsa
    eşleşen istatistiksel öneriye library_pattern_id'yi iliştirir.
    """
    suggestions = _statistical_suggestions(columns_data)

    if conn is not None:
        library_suggestions = get_library_suggestions(columns_data, conn)
        suggestions = _merge_suggestions(suggestions, library_suggestions)

    return suggestions


def _statistical_suggestions(columns_data: list[dict]) -> list[dict]:
    """Eski suggest_rules() mantığının aynısı - sadece o anki profile bakar."""
    suggestions = []

    for col in columns_data:
        name    = col["column"]
        ctype   = col["type"]
        null_pct = col.get("null_pct", 0)
        distinct = col.get("distinct_count", 0)
        row_count = col.get("row_count", 0)

        # Null kontrolü
        if null_pct == 0:
            suggestions.append({
                "column":      name,
                "type":        "null",
                "title":       f"{name} hiç boş olmamalı",
                "assert_type": "equals",
                "assert_value": "0",
                "reason":      "Şu an hiç null yok — bu kuralı koruyalım",
                "confidence":  "high",
                "library_pattern_id": None,
            })
        elif null_pct < 5:
            suggestions.append({
                "column":      name,
                "type":        "null",
                "title":       f"{name} null oranı < %5",
                "assert_type": "less_than",
                "assert_value": "5",
                "reason":      f"Şu an %{null_pct} null var",
                "confidence":  "medium",
                "library_pattern_id": None,
            })

        # Değer aralığı (numeric)
        if ctype == "numeric" and col.get("min") is not None:
            mn = float(col["min"])
            mx = float(col["max"])
            if mn != mx:
                padding_low  = max(0, mn * 0.8) if mn > 0 else mn * 1.2
                padding_high = mx * 1.2
                suggestions.append({
                    "column":      name,
                    "type":        "range",
                    "title":       f"{name} makul aralıkta olmalı",
                    "assert_type": "between",
                    "assert_value": f"[{round(padding_low,2)}, {round(padding_high,2)}]",
                    "reason":      f"Mevcut: min={mn}, max={mx}",
                    "confidence":  "medium",
                    "library_pattern_id": None,
                })

        # Duplicate kontrolü (id benzeri kolonlar)
        if distinct == row_count and row_count > 0:
            suggestions.append({
                "column":      name,
                "type":        "duplicate",
                "title":       f"{name} benzersiz olmalı",
                "assert_type": "equals",
                "assert_value": "0",
                "reason":      "Şu an tüm değerler benzersiz",
                "confidence":  "high",
                "library_pattern_id": None,
            })

    return suggestions


# ── Rule Library: desen çıkarma + biriken öneriler ──────────────────────────

# suggest_rules()'daki "type" alani ile rule_library.rule_type arasindaki eslesme
SUGGESTION_TYPE_TO_RULE_TYPE = {
    "null":      "not_null",
    "duplicate": "unique",
    "range":     "range",
}
_RULE_TYPE_TO_SUGGESTION_TYPE = {v: k for k, v in SUGGESTION_TYPE_TO_RULE_TYPE.items()}


def normalize_column_pattern(column_name: str) -> str:
    """
    Kolon adını genellenebilir bir desene indirger.
    "customer_email" -> "*email*", "employee_id" -> "*_id", digerleri oldugu gibi.
    """
    n = column_name.lower().strip()
    if n == "id" or n.endswith("_id"):
        return "*_id"
    if "email" in n:
        return "*email*"
    if n.endswith("_date") or n.endswith("_at") or "date" in n:
        return "*_date"
    if "name" in n:
        return "*name*"
    return n


def fingerprint_query(query: str, assert_type: str) -> str:
    """
    Ham SQL check'inden (checks.toml veya wizard) rule_type cikarir.
    Wizard'in kendi urettigi SQL kaliplariyla birebir eslesecek sekilde yazildi.
    """
    q = (query or "").lower()

    if "count(distinct" in q:
        return "unique"
    if "is null" in q and "count(*)" in q:
        return "not_null"
    if assert_type == "between":
        return "range"
    if ("max(" in q or "datediff" in q or "timestampdiff" in q) and assert_type in (
        "less_than", "greater_than",
    ):
        return "freshness"
    if q.strip().startswith("select count(*)") and " where " not in q:
        return "row_count"
    return "custom"


def record_rule_usage(conn, column_name: str, column_type: str, rule_type: str,
                       rule_definition: dict, source_format: str = "sql") -> None:
    """
    Bir check kaydedildiginde (SQL veya TOML fark etmez) rule_library'yi besler.
    Ayni desen+rule_type zaten varsa sadece times_used++ / last_used_at guncellenir.
    """
    if rule_type == "custom":
        return  # genellenemeyen kurallari kutuphaneye yazmiyoruz

    pattern = normalize_column_pattern(column_name)
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO rule_library
                (column_name_pattern, column_type, rule_type, rule_definition,
                 source_format, times_used, last_used_at)
            VALUES (%s, %s, %s, %s, %s, 1, NOW())
            ON DUPLICATE KEY UPDATE
                times_used    = times_used + 1,
                last_used_at  = NOW(),
                column_type   = VALUES(column_type)
        """, (pattern, column_type, rule_type, json.dumps(rule_definition), source_format))
    conn.commit()


def record_suggestion_feedback(conn, pattern_id: int | None, column_name: str,
                                rule_type: str, accepted: bool) -> None:
    """
    Wizard'da bir oneri kabul/red edildiginde cagirilir.
    pattern_id biliniyorsa dogrudan o satiri gunceller; bilinmiyorsa
    (henuz kutuphanede olmayan bir istatistiksel oneriyse) get-or-create yapar.
    """
    with conn.cursor() as cur:
        if pattern_id:
            col = "times_accepted" if accepted else "times_rejected"
            cur.execute(f"UPDATE rule_library SET {col} = {col} + 1 WHERE id = %s", (pattern_id,))
        else:
            pattern = normalize_column_pattern(column_name)
            cur.execute("""
                INSERT INTO rule_library
                    (column_name_pattern, rule_type, source_format,
                     times_used, times_accepted, times_rejected, last_used_at)
                VALUES (%s, %s, 'wizard_manual', 0, %s, %s, NOW())
                ON DUPLICATE KEY UPDATE
                    times_accepted = times_accepted + VALUES(times_accepted),
                    times_rejected = times_rejected + VALUES(times_rejected),
                    last_used_at   = NOW()
            """, (pattern, rule_type, 1 if accepted else 0, 0 if accepted else 1))
    conn.commit()


def get_library_suggestions(columns_data: list[dict], conn) -> list[dict]:
    """
    Tüm kolonlar için tek sorguda rule_library'den öneri çeker (N+1 fix).
    """
    if not columns_data:
        return []

    col_map: dict[str, str] = {}
    for col in columns_data:
        name = col["column"]
        col_map[normalize_column_pattern(name)] = name
        col_map[name.lower()] = name

    patterns = list(col_map.keys())
    placeholders = ", ".join(["%s"] * len(patterns))

    suggestions = []
    with conn.cursor() as cur:
        cur.execute(f"""
            SELECT id, column_name_pattern, rule_type, times_used, times_accepted, times_rejected
            FROM rule_library
            WHERE column_name_pattern IN ({placeholders})
            ORDER BY times_used DESC
        """, patterns)
        rows = cur.fetchall()

    for row in rows:
        total_feedback = row["times_accepted"] + row["times_rejected"]
        accept_rate = (row["times_accepted"] / total_feedback) if total_feedback else None
        if accept_rate is not None and accept_rate < 0.3 and total_feedback >= 3:
            continue
        name = col_map.get(row["column_name_pattern"], row["column_name_pattern"])
        sugg_type = _RULE_TYPE_TO_SUGGESTION_TYPE.get(row["rule_type"], row["rule_type"])
        confidence = "high" if row["times_used"] >= 5 else "medium"
        rate_text = f", kabul oranı %{round(accept_rate*100)}" if accept_rate is not None else ""
        suggestions.append({
            "column":      name,
            "type":        sugg_type,
            "title":       f"{name} — kütüphaneden öneri ({row['rule_type']})",
            "assert_type": "equals",
            "assert_value": "0",
            "reason":      f"Bu desen {row['times_used']} kez kullanıldı{rate_text}",
            "confidence":  confidence,
            "library_pattern_id": row["id"],
        })
    return suggestions

def _merge_suggestions(stat_suggestions: list[dict], library_suggestions: list[dict]) -> list[dict]:
    """
    Ayni (column, type) hem istatistiksel hem kutuphane onerisinde varsa,
    istatistiksel olani kutuphane id'siyle guclendirip tekrar eklemeyi engeller.
    """
    stat_by_key = {(s["column"], s["type"]): s for s in stat_suggestions}
    merged = list(stat_suggestions)

    for lib in library_suggestions:
        key = (lib["column"], lib["type"])
        if key in stat_by_key:
            existing = stat_by_key[key]
            existing["library_pattern_id"] = lib["library_pattern_id"]
            existing["reason"] += f" · {lib['reason']}"
            if lib["confidence"] == "high":
                existing["confidence"] = "high"
        else:
            merged.append(lib)

    return merged
