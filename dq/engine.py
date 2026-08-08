"""
Check motoru — veri kalitesi kurallarını tanımlar ve çalıştırır.

İki yoldan kural oluşturulabilir:
  1. Python API   : Check(...) nesnesi doğrudan
  2. Config parser: TOML/dict'ten otomatik
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable


# ── Sonuç nesnesi ────────────────────────────────────────────────────────────

@dataclass
class CheckResult:
    name: str
    passed: bool
    value: Any          # ölçülen değer
    expected: Any       # beklenen değer / eşik
    message: str = ""

    @property
    def status(self) -> str:
        return "PASS" if self.passed else "FAIL"


# ── Check tanımı ─────────────────────────────────────────────────────────────

@dataclass
class Check:
    """
    Tek bir veri kalitesi kuralı.

    Args:
        name:      İnsan okunabilir isim
        query:     Çalıştırılacak SQL (skaler değer döndürmeli)
        assertion: Dönen değeri alan, True/False döndüren fonksiyon
        expected:  Raporlarda gösterilecek beklenti açıklaması
    """
    name: str
    query: str
    assertion: Callable[[Any], bool]
    expected: Any = "assertion == True"
    tags: list[str] = field(default_factory=list)


# ── Yerleşik assertion'lar (sık kullanılan desenler) ─────────────────────────

def is_not_null(value) -> bool:
    return value is not None and value != 0

def less_than(threshold: float) -> Callable:
    return lambda v: float(v) < threshold

def greater_than(threshold: float) -> Callable:
    return lambda v: float(v) > threshold

def between(low: float, high: float) -> Callable:
    return lambda v: low <= float(v) <= high

def equals(expected) -> Callable:
    return lambda v: v == expected

def row_count_at_least(n: int) -> Callable:
    return lambda v: int(v) >= n
def row_count_between(min_n: int, max_n: int) -> Callable:
    return lambda v: min_n <= int(v) <= max_n
def not_empty(value) -> bool:
    return value is not None and str(value).strip() != ""
def accepted_values(allowed: list) -> Callable:
    return lambda v: v in allowed
def regex_match(pattern: str) -> Callable:
    import re
    return lambda v: bool(re.match(pattern, str(v))) if v is not None else False
def freshness_hours(max_hours: float) -> Callable:
    from datetime import datetime, timezone
    def _check(v) -> bool:
        if v is None:
            return False
        if isinstance(v, str):
            v = datetime.fromisoformat(v)
        now = datetime.now(timezone.utc)
        v_aware = v.replace(tzinfo=timezone.utc) if v.tzinfo is None else v
        return (now - v_aware).total_seconds() / 3600 <= max_hours
    return _check


def referential_integrity(ref_table: str, ref_column: str) -> Callable:
    """
    SQL: SELECT COUNT(*) FROM tablo WHERE kolon NOT IN (SELECT ref_kolon FROM ref_tablo)
    Dönen değer 0 ise integrity sağlam.
    """
    return lambda v: int(v) == 0

def completeness_ratio(min_ratio: float) -> Callable:
    """
    SQL: SELECT (COUNT(*) - COUNT(kolon)) / COUNT(*) — null oranı
    min_ratio=0.95 → en az %95 dolu olmalı (null oranı <= 0.05)
    """
    return lambda v: round(float(v), 10) <= round(1.0 - min_ratio, 10)

def statistical_anomaly(max_zscore: float) -> Callable:
    """
    SQL: SELECT ABS(AVG(kolon) - <beklenen>) / STDDEV(kolon)
    Dönen z-score değeri eşiği aşmamalı.
    """
    return lambda v: float(v) <= max_zscore

def schema_drift(expected_count: int) -> Callable:
    """
    SQL: SELECT COUNT(*) FROM information_schema.columns WHERE table_name=... AND table_schema=...
    Beklenen kolon sayısıyla karşılaştırır.
    """
    return lambda v: int(v) == expected_count

def schema_check(expected_columns: dict) -> Callable:
    """
    Kolon varlığı + tip kontrolü.

    SQL: SELECT column_name, data_type
         FROM information_schema.columns
         WHERE table_name=... AND table_schema=...

    Dönen değer JSON string — her satır {"column_name": ..., "data_type": ...}
    expected_columns: {"kolon_adi": "beklenen_tip", ...}  tip None ise sadece varlık kontrol edilir.
    """
    import json

    def _check(v) -> bool:
        if v is None:
            return False
        if isinstance(v, str):
            try:
                rows = json.loads(v)
            except Exception:
                return False
        else:
            rows = v

        actual = {r["column_name"].lower(): r["data_type"].lower() for r in rows}
        for col, expected_type in expected_columns.items():
            col_lower = col.lower()
            if col_lower not in actual:
                return False
            if expected_type is not None:
                if expected_type.lower() not in actual[col_lower]:
                    return False
        return True

    return _check



def custom_sql(expected) -> Callable:
    """
    Kullanıcı tanımlı SQL assertion.

    Sorgu skaler bir değer döndürmeli; dönen değer expected ile karşılaştırılır.
    expected: sayısal eşik (int/float) → dönen değer == expected
              tuple (low, high) → low <= değer <= high
              None → değer None değilse geçer
    """
    def _check(v) -> bool:
        if expected is None:
            return v is not None
        if isinstance(expected, (list, tuple)) and len(expected) == 2:
            return float(expected[0]) <= float(v) <= float(expected[1])
        return float(v) == float(expected)
    return _check


def volume_anomaly(max_pct_change: float = 50.0, baseline: float | None = None) -> Callable:
    """
    Satır sayısı değişim anomalisi.

    SQL: SELECT COUNT(*) FROM tablo
    Dönen değer mevcut satır sayısı.

    baseline verilmişse: abs(current - baseline) / baseline * 100 <= max_pct_change
    baseline verilmemişse: değer > 0 ise geçer (ilk ölçüm)

    Örnek: volume_anomaly(max_pct_change=30, baseline=10000)
    """
    def _check(v) -> bool:
        current = float(v)
        if baseline is None:
            return current > 0
        if baseline == 0:
            return current == 0
        pct_change = abs(current - baseline) / baseline * 100
        return pct_change <= max_pct_change
    return _check

def duplicate_row(threshold: int = 0) -> Callable:
    """
    Tekrar eden satır tespiti.

    SQL: SELECT COUNT(*) - COUNT(DISTINCT kolon1, kolon2, ...)  veya
         SELECT COUNT(*) FROM (SELECT ... GROUP BY ... HAVING COUNT(*)>1)
    Dönen değer: tekrar eden satır sayısı — threshold'u aşmamalı (genellikle 0).
    """
    return lambda v: int(v) <= threshold

# ── Check engine ─────────────────────────────────────────────────────────────

class CheckEngine:
    """
    Connector üzerinde check listesini sırayla çalıştırır.

    Kullanım:
        engine = CheckEngine(connector)
        engine.add(Check(...))
        results = engine.run()
    """

    def __init__(self, connector):
        self.connector = connector
        self._checks: list[Check] = []

    def add(self, check: Check) -> "CheckEngine":
        self._checks.append(check)
        return self   # zincirleme: engine.add(...).add(...)

    def add_many(self, checks: list[Check]) -> "CheckEngine":
        self._checks.extend(checks)
        return self

    def run(self, tags: list[str] | None = None) -> list[CheckResult]:
        """
        Tüm check'leri çalıştır.

        Args:
            tags: Belirtilirse sadece bu etiketlere sahip check'ler çalışır.
        """
        targets = self._checks
        if tags:
            targets = [c for c in targets if any(t in c.tags for t in tags)]

        results = []
        with self.connector as conn:
            for check in targets:
                result = self._run_one(conn, check)
                results.append(result)
        return results

    def _run_one(self, conn, check: Check) -> CheckResult:
        try:
            rows = conn.execute(check.query)
            # Skaler değer: tek satır tek sütun beklenir
            if not rows:
                raise ValueError("Sorgu hiç satır döndürmedi")
            first_row = rows[0]
            value = next(iter(first_row.values()))  # ilk sütun değeri

            passed = check.assertion(value)
            return CheckResult(
                name=check.name,
                passed=passed,
                value=value,
                expected=check.expected,
            )
        except Exception as exc:
            return CheckResult(
                name=check.name,
                passed=False,
                value=None,
                expected=check.expected,
                message=f"Hata: {exc}",
            )
