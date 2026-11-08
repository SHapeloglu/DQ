"""
Veri kontratları — veri üreticisi ile tüketicisi arasındaki yazılı anlaşma.

Kontrat, bir veri kaynağı hakkında üç tür kural barındırır:
  1. schema   : kolon adı + beklenen tip
  2. checks   : 1. katmandaki Check nesneleri (kalite kuralları)
  3. freshness: verinin ne kadar taze olması gerektiği

TOML örneği (contract.toml):
─────────────────────────────
[contract]
name    = "orders_v1"
owner   = "data-team"
version = "1.0"

[[contract.schema]]
column = "id"
type   = "integer"
nullable = false
unique   = true

[[contract.schema]]
column = "amount"
type   = "float"
nullable = false

[[contract.checks]]
name   = "Satır sayısı > 0"
query  = "SELECT COUNT(*) FROM source"
assert = "greater_than"
value  = 0

[contract.freshness]
column    = "created_at"          # zaman damgası kolonu
max_hours = 24                    # 24 saatten eski veri ihlal sayılır

[contract.row_count]
min = 1                           # bu sayidan az satir varsa ihlal
max = 1000000                     # bu sayidan cok satir varsa ihlal (opsiyonel)
─────────────────────────────
"""

from __future__ import annotations
import tomllib
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

from dq.engine import Check
from dq.config import _parse_check        # check parser'ı yeniden kullan


# ── Kontrat veri yapıları ────────────────────────────────────────────────────

@dataclass
class ColumnSpec:
    """
    Kontratta beklenen tek bir kolon.
    `nullable=False` ise kolonda NULL olmamalı. `unique=True` ise kolondaki değerler tekrarsız olmalı.
    `type` alanı yalnız bilgi amaçlıdır: tip kontrolü şu an yapılmıyor (DİKKAT).
    """
    column:   str
    type:     str           # "integer" | "float" | "string" | "boolean" | "timestamp"
    nullable: bool = True
    unique:   bool = False


@dataclass
class FreshnessSpec:
    """Verinin tazelik kuralı: `column` zaman damgası kolonu, `max_hours` en fazla kaç saat eski olabileceği."""
    column:    str
    max_hours: float


@dataclass
class RowCountSpec:
    """Satır sayısı sınırları. `min` ve `max` boş (None) olabilir; boş olan sınır kontrol edilmez. Sınırlar dahildir."""
    min: int | None = None
    max: int | None = None


@dataclass
class DataContract:
    """
    Bir veri kaynağının tam kontratı: isim, sahip, sürüm ve kural grupları (schema, checks, freshness, row_count).
    Dosyadan `load_contract()` ile okunur; `ContractValidator` ile doğrulanır.
    """
    name:      str
    owner:     str
    version:   str
    schema:    list[ColumnSpec]    = field(default_factory=list)
    checks:    list[Check]         = field(default_factory=list)
    freshness: FreshnessSpec | None = None
    row_count: RowCountSpec | None = None


# ── Doğrulama sonuçları ──────────────────────────────────────────────────────

@dataclass
class ContractViolation:
    """
    Kontrat doğrulamasında yapılan tek bir kontrolün sonucu.
    `rule` kontrol türünü (schema, check, freshness, row_count) gösterir. `passed` False ise ihlal vardır; `detail` insan okunur açıklamadır.
    """
    rule:    str      # "schema" | "check" | "freshness"
    detail:  str
    passed:  bool


@dataclass
class ContractResult:
    """Bir kontratın tüm doğrulama sonuçlarının toplamı."""
    contract_name: str
    violations:    list[ContractViolation]

    @property
    def passed(self) -> bool:
        """Tüm kontroller geçtiyse True; tek bir ihlal bile varsa False döner."""
        return all(v.passed for v in self.violations)

    @property
    def status(self) -> str:
        """Sonucu okunabilir metin olarak verir: "PASS" veya "FAIL"."""
        return "PASS" if self.passed else "FAIL"


# ── Kontrat yükleyici ─────────────────────────────────────────────────────────

def load_contract(path: str | Path) -> DataContract:
    """
    TOML kontrat dosyasını okur ve `DataContract` nesnesi döndürür. `[contract]` bölümü zorunludur; yoksa KeyError fırlatılır.
    `owner` yoksa "unknown", `version` yoksa "0.1" kullanılır. Check'ler `dq.config._parse_check` ile ayrıştırılır.
    """
    with open(path, "rb") as f:
        raw = tomllib.load(f)

    c = raw["contract"]

    schema = [
        ColumnSpec(
            column   = col["column"],
            type     = col["type"],
            nullable = col.get("nullable", True),
            unique   = col.get("unique", False),
        )
        for col in c.get("schema", [])
    ]

    checks = [_parse_check(ch) for ch in c.get("checks", [])]

    freshness = None
    if "freshness" in c:
        f = c["freshness"]
        freshness = FreshnessSpec(column=f["column"], max_hours=f["max_hours"])

    row_count = None
    if "row_count" in c:
        rc = c["row_count"]
        row_count = RowCountSpec(min=rc.get("min"), max=rc.get("max"))

    return DataContract(
        name      = c["name"],
        owner     = c.get("owner", "unknown"),
        version   = c.get("version", "0.1"),
        schema    = schema,
        checks    = checks,
        freshness = freshness,
        row_count = row_count,
    )


# ── Kontrat doğrulayıcı ───────────────────────────────────────────────────────

# Tip eşleme: TOML tipi → Python kontrolü
# DİKKAT: `_TYPE_CHECK` ve `_SQL_TYPE_MAP` şu an hiçbir yerde kullanılmıyor. Tip kontrolü yapılmıyor.
_TYPE_CHECK = {
    "integer":   lambda v: isinstance(v, int),
    "float":     lambda v: isinstance(v, (int, float)),
    "string":    lambda v: isinstance(v, str),
    "boolean":   lambda v: isinstance(v, bool),
    "timestamp": lambda v: isinstance(v, str),   # ISO string veya datetime
}

# SQL → Python tip karşılıkları (connector'dan gelen sütun tipi için)
_SQL_TYPE_MAP = {
    "int":       "integer",
    "int4":      "integer",
    "int8":      "integer",
    "bigint":    "integer",
    "numeric":   "float",
    "float":     "float",
    "float8":    "float",
    "double":    "float",
    "varchar":   "string",
    "text":      "string",
    "bool":      "boolean",
    "timestamp": "timestamp",
    "timestamptz": "timestamp",
}


class ContractValidator:
    """
    DataContract'ı bir connector üzerinde doğrular.

    Kullanım:
        validator = ContractValidator(connector)
        result = validator.validate(contract)
    """

    def __init__(self, connector):
        """Doğrulayıcıyı bir connector ile oluşturur. Bağlantı burada açılmaz; `validate()` içinde açılır."""
        self.connector = connector

    def validate(self, contract: DataContract) -> ContractResult:
        """
        Kontratın dört kuralını (schema, check, freshness, row_count) tek bir bağlantı üzerinde sırayla çalıştırır.
        Bağlantı `with` ile açılıp kapanır. Her kural kendi hatasını yakalar; bir kural hata verse bile diğerleri çalışır.
        Dönüş: `ContractResult`.
        """
        violations: list[ContractViolation] = []

        with self.connector as conn:
            violations += self._check_schema(conn, contract)
            violations += self._check_checks(conn, contract)
            violations += self._check_freshness(conn, contract)
            violations += self._check_row_count(conn, contract)

        return ContractResult(
            contract_name = contract.name,
            violations    = violations,
        )

    # ── Schema doğrulama ──────────────────────────────────────────────────────

    def _check_schema(self, conn, contract: DataContract) -> list[ContractViolation]:
        """
        Kolonların varlığını, (nullable=False ise) NULL olmadığını ve (unique=True ise) tekrarsız olduğunu kontrol eder. Tip kontrolü YAPILMAZ.
        Kolon listesi `SELECT * FROM source LIMIT 1` sorgusundan alınır; sorgu başarısız olursa kolon listesi boş kalır ve tüm kolonlar 'bulunamadı' olur.
        """
        if not contract.schema:
            return []

        # Mevcut kolonları çek (DuckDB / Postgres her ikisinde de çalışır)
        try:
            rows = conn.execute("SELECT * FROM source LIMIT 1")
        except Exception:
            rows = conn.execute("SELECT * FROM (SELECT 1) t LIMIT 0")

        actual_columns = set(rows[0].keys()) if rows else set()

        results = []
        for spec in contract.schema:
            if spec.column not in actual_columns:
                results.append(ContractViolation(
                    rule   = "schema",
                    detail = f"Kolon bulunamadı: '{spec.column}'",
                    passed = False,
                ))
                continue

            # Nullable kontrolü: kolonda NULL var mı?
            if not spec.nullable:
                try:
                    null_rows = conn.execute(
                        f"SELECT COUNT(*) AS cnt FROM source WHERE \"{spec.column}\" IS NULL"
                    )
                    null_count = null_rows[0]["cnt"] if null_rows else 0
                    passed = null_count == 0
                    results.append(ContractViolation(
                        rule   = "schema",
                        detail = f"'{spec.column}' nullable=false, NULL sayısı: {null_count}",
                        passed = passed,
                    ))
                except Exception as e:
                    results.append(ContractViolation(
                        rule="schema", detail=f"'{spec.column}' NULL kontrolü hatası: {e}",
                        passed=False))
            else:
                results.append(ContractViolation(
                    rule   = "schema",
                    detail = f"'{spec.column}' mevcut",
                    passed = True,
                ))

            # Unique kontrolü: kolonda duplicate var mı?
            # `COUNT(*) - COUNT(DISTINCT kolon)` tekrar sayısını verir. COUNT(DISTINCT) NULL değerleri saymadığı için birden çok NULL 'tekrar' sayılmaz.
            if spec.unique:
                try:
                    dup_rows = conn.execute(
                        f'SELECT COUNT(*) - COUNT(DISTINCT "{spec.column}") AS dup_count '
                        f'FROM source'
                    )
                    dup_count = dup_rows[0]["dup_count"] if dup_rows else 0
                    passed = dup_count == 0
                    results.append(ContractViolation(
                        rule   = "schema",
                        detail = f"'{spec.column}' unique=true, duplicate sayısı: {dup_count}",
                        passed = passed,
                    ))
                except Exception as e:
                    results.append(ContractViolation(
                        rule="schema", detail=f"'{spec.column}' unique kontrolü hatası: {e}",
                        passed=False))

        return results

    # ── Check doğrulama (1. katman check'lerini tekrar kullan) ───────────────

    def _check_checks(self, conn, contract: DataContract) -> list[ContractViolation]:
        # TODO(kontrol): Bu import bu fonksiyonda kullanılmıyor; eski bir kalıntı olabilir.
        """
        Kontrattaki check'leri sırayla çalıştırır. Her check'in sorgusu çalışır, ilk sütunun değeri assertion ile değerlendirilir.
        Sorgu ya da assertion hata verirse o check FAIL sayılır; diğer check'ler yine çalışır.
        """
        from dq.engine import CheckEngine

        if not contract.checks:
            return []

        # Geçici bir engine oluştur — connector zaten açık
        violations = []
        for check in contract.checks:
            try:
                rows  = conn.execute(check.query)
                value = next(iter(rows[0].values())) if rows else None
                passed = check.assertion(value) if value is not None else False
                violations.append(ContractViolation(
                    rule   = "check",
                    detail = f"{check.name}: değer={value!r}, beklenen={check.expected!r}",
                    passed = passed,
                ))
            except Exception as e:
                violations.append(ContractViolation(
                    rule="check", detail=f"{check.name}: hata={e}", passed=False
                ))

        return violations

    # ── Tazelik doğrulama ─────────────────────────────────────────────────────

    def _check_freshness(self, conn, contract: DataContract) -> list[ContractViolation]:
        """
        En yeni zaman damgasını (`MAX(kolon)`) okur ve şu andan kaç saat önce olduğuna bakar. `max_hours` aşılırsa ihlal sayılır.
        Kolon boşsa ya da okunamazsa FAIL döner. Saat dilimi olmayan değerler UTC kabul edilir.
        """
        if not contract.freshness:
            return []

        spec = contract.freshness
        try:
            rows = conn.execute(
                f'SELECT MAX("{spec.column}") AS max_ts FROM source'
            )
            max_ts_str = rows[0]["max_ts"] if rows else None
            if max_ts_str is None:
                return [ContractViolation(
                    rule="freshness",
                    detail=f"'{spec.column}' kolonu boş veya NULL",
                    passed=False,
                )]

            # ISO string → datetime
            # 'Z' (UTC) sonekini fromisoformat'ın anlayacağı '+00:00' biçimine çeviriyoruz.
            max_ts = datetime.fromisoformat(str(max_ts_str).replace("Z", "+00:00"))
            # Zaman damgasında saat dilimi yoksa UTC olduğu varsayılır.
            if max_ts.tzinfo is None:
                max_ts = max_ts.replace(tzinfo=timezone.utc)

            age_hours = (datetime.now(timezone.utc) - max_ts).total_seconds() / 3600
            passed    = age_hours <= spec.max_hours

            return [ContractViolation(
                rule   = "freshness",
                detail = (f"Son veri: {max_ts.isoformat()}, "
                          f"yaş: {age_hours:.1f}h, limit: {spec.max_hours}h"),
                passed = passed,
            )]

        except Exception as e:
            return [ContractViolation(
                rule="freshness", detail=f"Tazelik kontrolü hatası: {e}", passed=False
            )]

    # ── Satır sayısı doğrulama ────────────────────────────────────────────────

    def _check_row_count(self, conn, contract: DataContract) -> list[ContractViolation]:
        """Tablodaki satır sayısını alır; `min` ve `max` sınırlarına göre ayrı ayrı sonuç üretir. Hata olursa tek bir FAIL sonucu döner."""
        if not contract.row_count:
            return []

        spec = contract.row_count
        try:
            rows = conn.execute("SELECT COUNT(*) AS cnt FROM source")
            count = rows[0]["cnt"] if rows else 0

            violations = []
            # Sınır 0 olabilir; bu yüzden 'if spec.min' yerine 'is not None' ile bakılır.
            if spec.min is not None:
                passed = count >= spec.min
                violations.append(ContractViolation(
                    rule   = "row_count",
                    detail = f"Satır sayısı: {count}, min: {spec.min}",
                    passed = passed,
                ))
            if spec.max is not None:
                passed = count <= spec.max
                violations.append(ContractViolation(
                    rule   = "row_count",
                    detail = f"Satır sayısı: {count}, max: {spec.max}",
                    passed = passed,
                ))
            return violations

        except Exception as e:
            return [ContractViolation(
                rule="row_count", detail=f"Satır sayısı kontrolü hatası: {e}", passed=False
            )]
