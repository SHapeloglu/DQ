"""
reporter_v2.py — 1. katman reporter'ını anomali ve kontrat çıktısıyla genişletir.

Eski reporter'ı bozmaz; yeni fonksiyonlar ek olarak gelir.
"""

from __future__ import annotations
import json
import sys
from datetime import datetime, timezone
from typing import TextIO

from dq.anomaly import AnomalyResult
from dq.contracts import ContractResult, ContractViolation

_GREEN  = "\033[92m"
_RED    = "\033[91m"
_YELLOW = "\033[93m"
_CYAN   = "\033[96m"
_RESET  = "\033[0m"
_BOLD   = "\033[1m"


def _c(text, color):
    if not sys.stdout.isatty():
        return text
    return f"{color}{text}{_RESET}"


# ── Anomali raporu ────────────────────────────────────────────────────────────

def anomaly_console_report(results: list[AnomalyResult],
                           out: TextIO = sys.stdout) -> None:
    print(f"\n{_BOLD}Anomali Tespiti{_RESET}", file=out)
    print("─" * 52, file=out)

    for r in results:
        icon  = "⚠" if r.is_anomaly else "✓"
        color = _RED if r.is_anomaly else _GREEN
        label = _c(f"{icon} {r.status}", color)
        print(f"  {label}  {r.metric_name}", file=out)
        print(f"         değer={r.current!r}  "
              f"alt={r.lower_bound!r}  üst={r.upper_bound!r}", file=out)
        print(f"         yöntem={r.method}  skor={r.score}  {r.message}", file=out)

    flagged = sum(r.is_anomaly for r in results)
    color   = _RED if flagged else _GREEN
    print("─" * 52, file=out)
    print(f"  {_c(f'{flagged}/{len(results)} anomali', color)}\n", file=out)


def anomaly_json(results: list[AnomalyResult]) -> dict:
    from dataclasses import asdict
    return {
        "run_at":    datetime.now(timezone.utc).isoformat(),
        "anomalies": [asdict(r) for r in results],
        "summary": {
            "total":   len(results),
            "flagged": sum(r.is_anomaly for r in results),
        },
    }


# ── Kontrat raporu ────────────────────────────────────────────────────────────

def contract_console_report(result: ContractResult,
                            out: TextIO = sys.stdout) -> None:
    print(f"\n{_BOLD}Veri Kontratı — {result.contract_name}{_RESET}", file=out)
    print("─" * 52, file=out)

    for v in result.violations:
        icon  = "✓" if v.passed else "✗"
        color = _GREEN if v.passed else _RED
        tag   = _c(f"[{v.rule}]", _CYAN)
        print(f"  {_c(icon, color)}  {tag}  {v.detail}", file=out)

    color = _GREEN if result.passed else _RED
    print("─" * 52, file=out)
    print(f"  Kontrat: {_c(result.status, color)}\n", file=out)


def contract_json(result: ContractResult) -> dict:
    return {
        "contract":   result.contract_name,
        "status":     result.status,
        "passed":     result.passed,
        "violations": [
            {"rule": v.rule, "detail": v.detail, "passed": v.passed}
            for v in result.violations
        ],
    }


# ── Birleşik rapor ────────────────────────────────────────────────────────────

def full_report(
    metric_store=None,  # MetricStore instance — verilirse sonuçlar kaydedilir
    check_results=None,
    anomaly_results: list[AnomalyResult] | None = None,
    contract_results: list[ContractResult] | None = None,
    format: str = "console",
    output_path: str | None = None,
) -> int:
    """
    Tüm sonuçları tek seferde raporlar.

    Returns:
        0 → her şey geçti
        1 → en az bir sorun var
    """
    has_failure = False

    # MetricStore kaydı
    if metric_store is not None:
        if check_results:
            metric_store.record_results(check_results)
        if anomaly_results:
            metric_store.record_results(anomaly_results)

    if format == "console":
        if check_results:
            from dq.reporter import console_report
            console_report(check_results)
            if not all(r.passed for r in check_results):
                has_failure = True

        if anomaly_results:
            anomaly_console_report(anomaly_results)
            if any(r.is_anomaly for r in anomaly_results):
                has_failure = True

        if contract_results:
            for cr in contract_results:
                contract_console_report(cr)
                if not cr.passed:
                    has_failure = True

    elif format == "json":
        payload: dict = {"run_at": datetime.now(timezone.utc).isoformat()}

        if check_results:
            from dataclasses import asdict
            payload["checks"] = [asdict(r) for r in check_results]
            if not all(r.passed for r in check_results):
                has_failure = True

        if anomaly_results:
            payload["anomalies"] = anomaly_json(anomaly_results)
            if any(r.is_anomaly for r in anomaly_results):
                has_failure = True

        if contract_results:
            payload["contracts"] = [contract_json(r) for r in contract_results]
            if any(not r.passed for r in contract_results):
                has_failure = True

        text = json.dumps(payload, indent=2, default=str)
        if output_path:
            with open(output_path, "w") as f:
                f.write(text)
        else:
            print(text)

    return 1 if has_failure else 0
