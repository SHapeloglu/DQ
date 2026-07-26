"""
dashboard.py — tek komutla çalışan terminal dashboard.

Kullanım:
    dq dashboard checks.toml
    dq dashboard checks.toml --watch          # her 30s yenile
    dq dashboard checks.toml --watch --every 60
    dq dashboard contract.toml --mode contract
    dq dashboard checks.toml --tags critical

Kurulum:
    pip install rich
"""

from __future__ import annotations
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# rich import — yoksa açıklayıcı hata ver
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.columns import Columns
    from rich.text import Text
    from rich.live import Live
    from rich import box
except ImportError:
    print("Hata: 'rich' kütüphanesi kurulu değil.")
    print("Çözüm: pip install rich")
    sys.exit(1)


console = Console()


# ── Yardımcılar ───────────────────────────────────────────────────────────────

def _status_text(passed: bool, label: str = "") -> Text:
    if passed:
        return Text(f"✓ {label or 'PASS'}", style="bold green")
    return Text(f"✗ {label or 'FAIL'}", style="bold red")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


# ── Check sonuçları tablosu ───────────────────────────────────────────────────

def _check_table(results) -> Table:
    table = Table(
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
        title="[bold]Kalite Kontrolleri[/bold]",
        title_justify="left",
        expand=True,
    )
    table.add_column("Check",    style="white",  no_wrap=True)
    table.add_column("Durum",    justify="center", no_wrap=True)
    table.add_column("Değer",    justify="right", style="dim")
    table.add_column("Beklenen", justify="left",  style="dim")
    table.add_column("Etiket",   justify="left",  style="dim cyan")

    for r in results:
        table.add_row(
            r.name,
            _status_text(r.passed),
            str(r.value) if r.value is not None else "—",
            str(r.expected),
            ", ".join(getattr(r, "tags", [])) or "—",
            end_section=False,
        )

    return table


# ── Anomali tablosu ───────────────────────────────────────────────────────────

def _anomaly_table(results) -> Table:
    table = Table(
        box=box.ROUNDED,
        show_header=True,
        header_style="bold magenta",
        title="[bold]Anomali Tespiti[/bold]",
        title_justify="left",
        expand=True,
    )
    table.add_column("Metrik",   style="white",  no_wrap=True)
    table.add_column("Durum",    justify="center", no_wrap=True)
    table.add_column("Değer",    justify="right")
    table.add_column("Alt",      justify="right", style="dim")
    table.add_column("Üst",      justify="right", style="dim")
    table.add_column("Skor",     justify="right", style="dim")
    table.add_column("Yöntem",   style="dim cyan")

    for r in results:
        table.add_row(
            r.metric_name,
            _status_text(not r.is_anomaly, "OK" if not r.is_anomaly else "ANOMALİ"),
            str(r.current),
            str(r.lower_bound) if r.lower_bound is not None else "—",
            str(r.upper_bound) if r.upper_bound is not None else "—",
            str(r.score),
            r.method,
        )

    return table


# ── Kontrat tablosu ───────────────────────────────────────────────────────────

def _contract_table(result) -> Table:
    table = Table(
        box=box.ROUNDED,
        show_header=True,
        header_style="bold yellow",
        title=f"[bold]Veri Kontratı — {result.contract_name}[/bold]",
        title_justify="left",
        expand=True,
    )
    table.add_column("Kural",  style="white",  no_wrap=True)
    table.add_column("Tip",    justify="center", style="dim cyan")
    table.add_column("Durum",  justify="center")
    table.add_column("Detay",  style="dim")

    for v in result.violations:
        table.add_row(
            v.detail.split(":")[0],
            v.rule,
            _status_text(v.passed),
            v.detail,
        )

    return table


# ── Özet panel ────────────────────────────────────────────────────────────────

def _summary_panel(check_results=None, anomaly_results=None,
                   contract_results=None) -> Panel:
    parts = []

    if check_results:
        passed = sum(r.passed for r in check_results)
        total  = len(check_results)
        color  = "green" if passed == total else "red"
        parts.append(f"[{color}]Kontroller: {passed}/{total}[/{color}]")

    if anomaly_results:
        flagged = sum(r.is_anomaly for r in anomaly_results)
        color   = "red" if flagged else "green"
        parts.append(f"[{color}]Anomali: {flagged}/{len(anomaly_results)}[/{color}]")

    if contract_results:
        failed = sum(not r.passed for r in contract_results)
        color  = "red" if failed else "green"
        parts.append(f"[{color}]Kontrat: {'FAIL' if failed else 'PASS'}[/{color}]")

    parts.append(f"[dim]{_now()}[/dim]")

    return Panel(
        "   •   ".join(parts),
        title="[bold]DataSoda[/bold]",
        border_style="bright_blue",
    )


# ── Tek çalıştırma ───────────────────────────────────────────────────────────

def _run_once(config_path: str, mode: str, tags: list[str] | None):
    """Config'i yükle, çalıştır, sonuçları döndür."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))

    check_results    = None
    anomaly_results  = None
    contract_results = None

    if mode == "contract":
        from dq.contracts import load_contract, ContractValidator
        from dq.config import SodaConfig

        contract  = load_contract(config_path)
        raw_cfg   = __import__("tomllib" if sys.version_info >= (3,11)
                               else "tomli", fromlist=["load"])
        with open(config_path, "rb") as f:
            raw = __import__("tomllib", fromlist=["load"]).load(f)

        from dq.config import SodaConfig
        cfg       = SodaConfig(raw)
        connector = cfg.build_connector() if "source" in raw else None

        if connector:
            validator        = ContractValidator(connector)
            contract_results = [validator.validate(contract)]

    else:  # mode == "checks"
        from dq.config import SodaConfig
        from dq.engine import CheckEngine

        cfg       = SodaConfig.from_toml(config_path)
        connector = cfg.build_connector()
        checks    = cfg.build_checks()

        if tags:
            checks = [c for c in checks if any(t in c.tags for t in tags)]

        engine        = CheckEngine(connector)
        engine.add_many(checks)
        check_results = engine.run()

    return check_results, anomaly_results, contract_results


# ── Dashboard render ─────────────────────────────────────────────────────────

def render(config_path: str, mode: str = "checks",
           tags: list[str] | None = None):
    """Tek seferlik dashboard render."""
    with console.status("[cyan]Çalıştırılıyor...[/cyan]"):
        check_r, anomaly_r, contract_r = _run_once(config_path, mode, tags)

    console.print()
    console.print(_summary_panel(check_r, anomaly_r, contract_r))

    if check_r:
        console.print(_check_table(check_r))
    if anomaly_r:
        console.print(_anomaly_table(anomaly_r))
    if contract_r:
        for cr in contract_r:
            console.print(_contract_table(cr))
    console.print()


def render_watch(config_path: str, mode: str = "checks",
                 tags: list[str] | None = None, every: int = 30):
    """Her N saniyede bir yenileyen canlı dashboard."""
    console.print(f"[dim]Her {every}s yenileniyor — çıkmak için Ctrl+C[/dim]\n")
    try:
        while True:
            console.clear()
            render(config_path, mode, tags)
            for remaining in range(every, 0, -1):
                console.print(
                    f"[dim]Sonraki yenileme: {remaining}s[/dim]",
                    end="\r"
                )
                time.sleep(1)
    except KeyboardInterrupt:
        console.print("\n[dim]Dashboard kapatıldı.[/dim]")


# ── CLI giriş noktası ────────────────────────────────────────────────────────

def dashboard_cli():
    import argparse

    parser = argparse.ArgumentParser(
        prog="dq dashboard",
        description="DataSoda terminal dashboard",
    )
    parser.add_argument("config",  help="TOML config veya kontrat dosyası")
    parser.add_argument("--mode",  default="checks",
                        choices=["checks", "contract"],
                        help="checks (varsayılan) veya contract")
    parser.add_argument("--watch", action="store_true",
                        help="Otomatik yenile")
    parser.add_argument("--every", type=int, default=30,
                        help="Yenileme aralığı (saniye, varsayılan: 30)")
    parser.add_argument("--tags",  nargs="+", default=None,
                        help="Sadece bu etiketleri çalıştır")

    args = parser.parse_args()

    if args.watch:
        render_watch(args.config, args.mode, args.tags, args.every)
    else:
        render(args.config, args.mode, args.tags)
