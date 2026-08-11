"""
dq_operator.py — Apache Airflow 2.7.x için DQ operatörü.

Kurulum:
    pip install dq  # veya dq klasörünü PYTHONPATH'e ekle

DAG örneği:
─────────────────────────────────────────────────────────────────
from airflow import DAG
from airflow.utils.dates import days_ago
from dq.airflow import DQOperator

with DAG(
    dag_id="orders_quality",
    schedule_interval="@daily",
    start_date=days_ago(1),
    catchup=False,
) as dag:

    check = DQOperator(
        task_id="check_orders",
        config="checks.toml",           # TOML dosya yolu
        tags=["critical"],              # opsiyonel filtre
        push_to_xcom=True,              # sonuçları XCom'a yaz
        fail_on_error=True,             # check başarısız → task başarısız
        api_url="http://dq-api:8000",   # opsiyonel: FastAPI'ya da gönder
    )
─────────────────────────────────────────────────────────────────
"""

from __future__ import annotations
import json
from typing import Any

from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults
from dq.contracts import load_contract, ContractValidator
from dq.config import SodaConfig
from dq.engine import CheckEngine
from dq.anomaly import AnomalyDetector
from dq.metrics import MetricStore
from secrets_loader import get_secret


class DQOperator(BaseOperator):
    """
    DQ veri kalitesi kontrollerini Airflow task'ı olarak çalıştırır.

    Args:
        config:        TOML config dosyası yolu (checks.toml veya contract.toml)
        mode:          "checks" (varsayılan) veya "contract"
        tags:          Sadece bu etiketleri çalıştır (None = hepsi)
        push_to_xcom:  Sonuçları XCom'a yaz (varsayılan: True)
        fail_on_error: Herhangi bir check başarısız olursa task'ı da başarısız say
        api_url:       DQ FastAPI adresi — varsa sonuçları buraya da gönderir
        api_token:     API bearer token (opsiyonel)
    """

    # Airflow UI'da sarı renkle gösterilir
    ui_color = "#f0c060"
    ui_fgcolor = "#000000"

    template_fields = ("config", "api_url")   # Jinja şablonu destekler

    @apply_defaults
    def __init__(
        self,
        config: str,
        mode: str = "checks",
        tags: list[str] | None = None,
        push_to_xcom: bool = True,
        fail_on_error: bool = True,
        api_url: str | None = None,
        api_token: str | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.config       = config
        self.mode         = mode
        self.tags         = tags
        self.push_to_xcom = push_to_xcom
        self.fail_on_error = fail_on_error
        self.api_url      = api_url
        self.api_token    = api_token

    def execute(self, context: dict[str, Any]) -> dict:
        """Airflow tarafından çağrılır."""
        self.log.info("DQ başlıyor — config: %s, mode: %s", self.config, self.mode)

        # ── Çalıştır ──────────────────────────────────────────────────────────
        results = self._run_checks()

        # ── Logla ─────────────────────────────────────────────────────────────
        self._log_results(results)

        # ── Sonuçları serileştir ───────────────────────────────────────────────
        payload = self._serialize(results, context)

        # ── XCom'a yaz ────────────────────────────────────────────────────────
        if self.push_to_xcom:
            context["ti"].xcom_push(key="dq_results", value=payload)
            self.log.info("Sonuçlar XCom'a yazıldı (key: dq_results)")

        # ── API'ya gönder ──────────────────────────────────────────────────────
        if self.api_url:
            self._push_to_api(payload)

        # ── Başarısız check varsa task'ı da başarısız say ─────────────────────
        if self.fail_on_error:
            failed = [r for r in results if not getattr(r, "passed", True)]
            if failed:
                names = ", ".join(r.name if hasattr(r, "name")
                                  else r.metric_name for r in failed)
                raise ValueError(f"DQ başarısız — {len(failed)} check kaldı: {names}")

        return payload

    # ── İç metodlar ───────────────────────────────────────────────────────────

    def _run_checks(self):
        if self.mode == "contract":
            import tomllib
            with open(self.config, "rb") as f:
                raw = tomllib.load(f)
            contract  = load_contract(self.config)
            cfg       = SodaConfig(raw)
            connector = cfg.build_connector()
            validator = ContractValidator(connector)
            result    = validator.validate(contract)
            return result.violations
        else:  # checks
            cfg       = SodaConfig.from_toml(self.config)
            connector = cfg.build_connector()
            checks    = cfg.build_checks()
            if self.tags:
                checks = [c for c in checks
                          if any(t in c.tags for t in self.tags)]
            engine = CheckEngine(connector)
            engine.add_many(checks)
            results = engine.run()

            # ── Anomali tespiti (MetricStore geçmişine dayalı) ────────────────
            try:
                dsn = get_secret("METRICS_PG_DSN")
                store = MetricStore(backend="postgres", dsn=dsn) if dsn else MetricStore()
                detector = AnomalyDetector(store, threshold=3.0, history_days=30)
                anomaly_results = detector.detect_all(results)
                failed_anomalies = [a for a in anomaly_results if a.is_anomaly]
                if failed_anomalies:
                    self.log.warning(
                        "Anomali tespiti: %d anormal metrik bulundu",
                        len(failed_anomalies),
                    )
                    for a in failed_anomalies:
                        self.log.warning("  ANOMALY: %s — skor=%.2f, yöntem=%s, mesaj=%s",
                                         a.metric_name, a.score, a.method, a.message)
            except Exception as exc:
                self.log.warning("AnomalyDetector çalıştırılamadı: %s", exc)

            return results
    def _log_results(self, results) -> None:
        for r in results:
            name   = getattr(r, "name", None) or getattr(r, "metric_name", "?")
            passed = getattr(r, "passed", None)
            if passed is None:
                passed = not getattr(r, "is_anomaly", False)

            status = "PASS" if passed else "FAIL"
            value  = getattr(r, "value", getattr(r, "current", "—"))
            self.log.info("[%s] %s — değer: %s", status, name, value)

    def _serialize(self, results, context: dict) -> dict:
        """Airflow XCom ve API için JSON-safe dict üretir."""
        from datetime import datetime, timezone
        from dataclasses import asdict

        items = []
        for r in results:
            try:
                d = asdict(r)
            except Exception:
                d = r.__dict__.copy()
            # callable alanları temizle (assertion fonksiyonu vs)
            d = {k: v for k, v in d.items() if not callable(v)}
            items.append(d)

        return {
            "dag_id":    context["dag"].dag_id,
            "task_id":   context["task"].task_id,
            "run_id":    context["run_id"],
            "run_at":    datetime.now(timezone.utc).isoformat(),
            "config":    self.config,
            "mode":      self.mode,
            "results":   items,
            "summary": {
                "total":  len(results),
                "passed": sum(
                    1 for r in results
                    if getattr(r, "passed", not getattr(r, "is_anomaly", False))
                ),
            },
        }

    def _push_to_api(self, payload: dict) -> None:
        """Sonuçları DQ FastAPI'ya HTTP POST ile gönderir."""
        import urllib.request
        import urllib.error

        url     = f"{self.api_url.rstrip('/')}/api/runs"
        data    = json.dumps(payload).encode()
        headers = {"Content-Type": "application/json"}

        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"

        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                self.log.info("API yanıtı: %s", resp.status)
        except urllib.error.URLError as e:
            # API'ya ulaşamasa bile task'ı başarısız sayma
            self.log.warning("API'ya gönderilemedi (task devam eder): %s", e)
