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
