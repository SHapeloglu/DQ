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


def row_condition(condition: str) -> Callable:
    """
    Belirtilen WHERE koşulunu sağlamayan satır sayısını döner.
    SQL: SELECT COUNT(*) FROM {tablo} WHERE NOT ({condition})
    Dönen değer: 0 olmalı (hiç ihlal yoksa geçer).
    Not: query alanına WHERE filtresi dahil SQL yazılır; assert_value koşul stringidir.
    """
    return lambda v: int(v) == 0
def duplicate_row(threshold: int = 0) -> Callable:
    """
    Tekrar eden satır tespiti.

    SQL: SELECT COUNT(*) - COUNT(DISTINCT kolon1, kolon2, ...)  veya
         SELECT COUNT(*) FROM (SELECT ... GROUP BY ... HAVING COUNT(*)>1)
    Dönen değer: tekrar eden satır sayısı — threshold'u aşmamalı (genellikle 0).
    """
    return lambda v: int(v) <= threshold


def zscore_anomaly(metric_name: str, store, max_zscore: float = 3.0, min_samples: int = 5) -> Callable:
    import math
    def _check(v) -> bool:
        values = store.get_recent_values(metric_name, n=100)
        if len(values) < min_samples:
            return True
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        std = math.sqrt(variance)
        if std == 0:
            return True
        z = abs(float(v) - mean) / std
        return z <= max_zscore
    return _check


def cross_table_check(connector_b, query_b: str, comparator: str = "equals", tolerance: float = 0.0) -> Callable:
    """
    İki farklı kaynaktan skaler değer karşılaştırır.
    connector_b: ikinci kaynağın connector nesnesi
    query_b:     ikinci kaynakta çalıştırılacak SQL
    comparator:  equals | less_than | greater_than | within_pct
    tolerance:   within_pct için yüzde tolerans (ör. 5.0 → %5)
    Ana sorgu (query_a) CheckEngine üzerinden çalışır; bu assertion value_a alır.
    """
    def _check(value_a) -> bool:
        with connector_b as conn:
            rows = conn.execute(query_b)
            if not rows:
                return False
            value_b = next(iter(rows[0].values()))
        a, b = float(value_a), float(value_b)
        if comparator == "equals":
            return a == b
        if comparator == "less_than":
            return a < b
        if comparator == "greater_than":
            return a > b
        if comparator == "within_pct":
            if b == 0:
                return a == 0
            return abs(a - b) / abs(b) * 100 <= tolerance
        return False
    return _check




def distribution_check(expected_mean: float, expected_std: float, tolerance_pct: float = 10.0) -> Callable:
    """
    Kolon dağılımını beklenen ortalama ve standart sapmaya göre kontrol eder.
    SQL: SELECT AVG(kolon), STDDEV(kolon) FROM tablo  — virgülle ayrılmış iki değer döndürmeli
         VEYA sadece AVG döndürüyorsa expected_std=None ile sadece ortalama kontrol edilir.
    Dönen değer: 'avg,std' formatında string veya tek sayısal değer (sadece avg kontrolü).
    tolerance_pct: izin verilen sapma yüzdesi (ör. 10.0 → %10)
    """
    def _check(v) -> bool:
        if v is None:
            return False
        s = str(v)
        if "," in s:
            parts = s.split(",")
            actual_mean = float(parts[0])
            actual_std = float(parts[1])
            mean_ok = abs(actual_mean - expected_mean) / (abs(expected_mean) or 1) * 100 <= tolerance_pct
            std_ok = abs(actual_std - expected_std) / (abs(expected_std) or 1) * 100 <= tolerance_pct
            return mean_ok and std_ok
        else:
            actual_mean = float(s)
            return abs(actual_mean - expected_mean) / (abs(expected_mean) or 1) * 100 <= tolerance_pct
    return _check


def trend_check(metric_name: str, store, window: int = 7, max_pct_change: float = 20.0, direction: str = "any") -> Callable:
    """
    MetricStore geçmişinde trend karşılaştırması.
    Son `window` ölçüm ortalaması ile önceki `window` ölçüm ortalamasını karşılaştırır.
    direction: 'any' (her yön), 'up' (artış kötü), 'down' (düşüş kötü)
    max_pct_change: izin verilen maksimum değişim yüzdesi
    Yetersiz geçmişte her zaman PASS döner.
    """
    def _check(v) -> bool:
        values = store.get_recent_values(metric_name, n=window * 2)
        if len(values) < window * 2:
            return True  # yetersiz geçmiş
        prev_window = values[:window]
        curr_window = values[window:]
        prev_avg = sum(prev_window) / len(prev_window)
        curr_avg = sum(curr_window) / len(curr_window)
        if prev_avg == 0:
            return curr_avg == 0
        pct_change = (curr_avg - prev_avg) / abs(prev_avg) * 100
        if direction == "up":
            return pct_change <= max_pct_change
        if direction == "down":
            return pct_change >= -max_pct_change
        return abs(pct_change) <= max_pct_change
    return _check


def custom_script_assertion(code: str, function_name: str = "check"):
    """
    Kullanıcı tarafından yüklenen custom Python assertion.
    
    AST ile güvenlik kontrolü: os, subprocess, sys, open, eval, exec vb. import'ları reddeder.
    Kısıtlı __builtins__ (len, str, int, float, bool, abs, min, max, isinstance vb.) ile çalışır.
    """
    import ast
    import math
    
    # ── AST validation ──────────────────────────────────────────────────────
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        raise ValueError(f"Syntax hatası: {e}")
    
    # Tehlikeli imports ve fonksiyonlar
    FORBIDDEN_IMPORTS = {"os", "subprocess", "sys", "shutil", "pathlib", "socket", "urllib", "requests"}
    FORBIDDEN_NAMES = {"eval", "exec", "compile", "__import__", "open", "input", "print"}
    
    for node in ast.walk(tree):
        # Import kontrolleri
        if isinstance(node, ast.Import):
            for alias in node.names:
                module = alias.name.split('.')[0]
                if module in FORBIDDEN_IMPORTS:
                    raise ValueError(f"Yasaklı import: {module}")
        
        if isinstance(node, ast.ImportFrom):
            module = node.module.split('.')[0] if node.module else ""
            if module in FORBIDDEN_IMPORTS:
                raise ValueError(f"Yasaklı import: {module}")
        
        # Function call kontrolleri
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id in FORBIDDEN_NAMES:
                    raise ValueError(f"Yasaklı fonksiyon: {node.func.id}")
    
    # ── Güvenli execution ───────────────────────────────────────────────────
    safe_builtins = {
        'len': len, 'str': str, 'int': int, 'float': float, 'bool': bool,
        'abs': abs, 'min': min, 'max': max, 'sum': sum, 'round': round,
        'isinstance': isinstance, 'type': type, 'range': range,
        'list': list, 'dict': dict, 'set': set, 'tuple': tuple,
        'sorted': sorted, 'reversed': reversed, 'enumerate': enumerate,
        'zip': zip, 'map': map, 'filter': filter, 'any': any, 'all': all,
        'math': math,  # statistical functions için
    }
    
    namespace = {'__builtins__': safe_builtins}
    
    try:
        exec(code, namespace)
    except Exception as e:
        raise ValueError(f"Kod çalıştırılırken hata: {e}")
    
    # ── Fonksiyon çıkarımı ──────────────────────────────────────────────────
    if function_name not in namespace:
        raise ValueError(f"Fonksiyon '{function_name}' kodda tanımlanmamış")
    
    user_fn = namespace[function_name]
    if not callable(user_fn):
        raise ValueError(f"'{function_name}' çağrılabilir değil")
    
    # ── Assertion fonksiyonu dön ────────────────────────────────────────────
    def assertion(value):
        try:
            result = user_fn(value)
            return bool(result)
        except Exception as e:
            # Execution sırasında hata → FAIL
            return False
    
    return assertion

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

        from concurrent.futures import ThreadPoolExecutor, as_completed
        import threading
        lock = threading.Lock()
        results = []
        with self.connector as conn:
            def _run_safe(check):
                with lock:
                    return self._run_one(conn, check)
            max_workers = min(4, len(targets)) if targets else 1
            with ThreadPoolExecutor(max_workers=max_workers) as pool:
                futures = {pool.submit(_run_safe, c): c for c in targets}
                for fut in as_completed(futures):
                    results.append(fut.result())
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
