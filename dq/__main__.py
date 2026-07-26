"""
DataSoda — ana giriş noktası.

─── Python API ile kullanım ───────────────────────────────────────────────────

    from dq import run, Check
    from dq.connectors import CsvConnector
    from dq.engine import greater_than, less_than

    connector = CsvConnector("orders.csv")

    results = run(
        connector=connector,
        checks=[
            Check(
                name="Satır sayısı > 0",
                query="SELECT COUNT(*) FROM source",
                assertion=greater_than(0),
                expected="greater_than(0)",
            ),
            Check(
                name="Null oran < %5",
                query="SELECT COUNT(*)*100.0/COUNT(1) FROM source WHERE id IS NULL",
                assertion=less_than(5),
                expected="less_than(5)",
            ),
        ],
    )

─── TOML dosyası ile kullanım ─────────────────────────────────────────────────

    from dq import run_from_toml

    run_from_toml("checks.toml")

─── CLI kullanım ──────────────────────────────────────────────────────────────

    python -m dq checks.toml
    python -m dq checks.toml --format json --output results.json
    python -m dq checks.toml --tags critical

"""

from __future__ import annotations
import sys
from typing import Any

from dq.engine import Check, CheckEngine
from dq.reporter import report
from dq.config import SodaConfig


def run(
    connector,
    checks: list[Check],
    tags: list[str] | None = None,
    format: str = "console",
    output_path: str | None = None,
) -> int:
    """
    Python API giriş noktası.

    Returns:
        0 → başarı, 1 → en az bir check başarısız
    """
    engine = CheckEngine(connector)
    engine.add_many(checks)
    results = engine.run(tags=tags)
    return report(results, format=format, output_path=output_path)


def run_from_toml(
    path: str,
    tags: list[str] | None = None,
    format: str = "console",
    output_path: str | None = None,
) -> int:
    """TOML dosyasından yükleyip çalıştır."""
    config    = SodaConfig.from_toml(path)
    connector = config.build_connector()
    checks    = config.build_checks()
    return run(connector, checks, tags=tags, format=format, output_path=output_path)


def run_from_dict(
    data: dict[str, Any],
    tags: list[str] | None = None,
    format: str = "console",
) -> int:
    """Python dict'ten yükleyip çalıştır."""
    config    = SodaConfig.from_dict(data)
    connector = config.build_connector()
    checks    = config.build_checks()
    return run(connector, checks, tags=tags, format=format)


# ── CLI ──────────────────────────────────────────────────────────────────────

def _cli():
    import argparse

    parser = argparse.ArgumentParser(prog="dq", description="Veri kalitesi kontrolü")
    parser.add_argument("config",  help="TOML config dosyası")
    parser.add_argument("--format", default="console", choices=["console", "json", "summary"])
    parser.add_argument("--output", default=None, help="JSON çıktı dosyası")
    parser.add_argument("--tags",   default=None, nargs="+", help="Filtrele: sadece bu etiketler")

    args = parser.parse_args()
    code = run_from_toml(args.config, tags=args.tags, format=args.format, output_path=args.output)
    sys.exit(code)


if __name__ == "__main__":
    _cli()
