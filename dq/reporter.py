"""
Reporter — CheckResult listesini formatlanmış çıktıya çevirir.

Desteklenen formatlar:
  - console : Renkli terminal çıktısı
  - json    : Makine okunabilir JSON
  - summary : Tek satır özet (CI/CD için)
"""

from __future__ import annotations
import warnings
warnings.warn(
    "reporter.py deprecated: reporter_v2.py kullan",
    DeprecationWarning,
    stacklevel=2,
)
import json
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from typing import TextIO

from dq.engine import CheckResult


# ── Terminal renk kodları (ANSI) ─────────────────────────────────────────────

_GREEN  = "\033[92m"
_RED    = "\033[91m"
_YELLOW = "\033[93m"
_RESET  = "\033[0m"
_BOLD   = "\033[1m"


def _colorize(text: str, color: str, *, force: bool = False) -> str:
    if not sys.stdout.isatty() and not force:
        return text
    return f"{color}{text}{_RESET}"


# ── Format fonksiyonları ──────────────────────────────────────────────────────

def console_report(results: list[CheckResult], out: TextIO = sys.stdout) -> None:
    """Renkli, okunabilir terminal raporu."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"\n{_BOLD}DataSoda — {now}{_RESET}", file=out)
    print("─" * 52, file=out)

    for r in results:
        icon  = "✓" if r.passed else "✗"
        color = _GREEN if r.passed else _RED
        label = _colorize(f"{icon} {r.status}", color)
        print(f"  {label}  {r.name}", file=out)
        print(f"         değer={r.value!r}  beklenen={r.expected!r}", file=out)
        if r.message:
            print(f"         {_colorize(r.message, _YELLOW)}", file=out)

    passed = sum(r.passed for r in results)
    total  = len(results)
    color  = _GREEN if passed == total else _RED
    print("─" * 52, file=out)
    print(f"  {_colorize(f'{passed}/{total} geçti', color)}\n", file=out)


def json_report(results: list[CheckResult]) -> str:
    """JSON string döndürür — dosyaya yazma veya API'ye gönderme için."""
    payload = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total":  len(results),
            "passed": sum(r.passed for r in results),
            "failed": sum(not r.passed for r in results),
        },
        "checks": [asdict(r) for r in results],
    }
    return json.dumps(payload, indent=2, default=str)


def summary_report(results: list[CheckResult]) -> str:
    """Tek satır özet — CI pipeline log'ları için."""
    passed = sum(r.passed for r in results)
    total  = len(results)
    status = "OK" if passed == total else "FAIL"
    return f"DataSoda {status}: {passed}/{total} checks passed"


# ── Kolaylık fonksiyonu ───────────────────────────────────────────────────────

def report(results: list[CheckResult],
           format: str = "console",
           output_path: str | None = None) -> int:
    """
    Sonuçları istenen formatta yazar.

    Returns:
        0 → tüm check'ler geçti
        1 → en az bir check başarısız
    """
    if format == "console":
        console_report(results)

    elif format == "json":
        text = json_report(results)
        if output_path:
            with open(output_path, "w") as f:
                f.write(text)
        else:
            print(text)

    elif format == "summary":
        print(summary_report(results))

    else:
        raise ValueError(f"Bilinmeyen format: '{format}'. Geçerliler: console, json, summary")

    return 0 if all(r.passed for r in results) else 1
