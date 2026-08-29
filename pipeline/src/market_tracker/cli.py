from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from .alpaca import AlpacaClient
from .calculations import build_market_snapshot
from .calendar import latest_completed_market_date
from .codec import parse_ledger, parse_report, parse_snapshot
from .config import (
    DEFAULT_DIVIDEND_STOCKS,
    DEFAULT_ETP_BASKET,
    DEFAULT_MARKET_ETFS,
    PipelineConfig,
    SecurityDefinition,
)
from .contracts import json_schemas
from .demo import build_demo_documents
from .io import read_json, write_json
from .preflight import inspect_preflight
from .universe import load_or_refresh_universe, write_universe_csv, fetch_sp500_universe
from .validation import validate_json_contract, validate_report


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("date must use YYYY-MM-DD") from exc


def _write_documents(
    output_dir: Path,
    snapshot: object,
    ledger: object,
    report: object,
    *,
    report_only: bool = False,
) -> Path:
    report_date = report.metadata.market_date  # type: ignore[attr-defined]
    if not report_only:
        write_json(output_dir / "artifacts" / report_date.isoformat() / "market-snapshot.json", snapshot)  # type: ignore[arg-type]
        write_json(output_dir / "artifacts" / report_date.isoformat() / "evidence-ledger.json", ledger)  # type: ignore[arg-type]
    report_path = output_dir / "reports" / f"{report_date.isoformat()}.json"
    write_json(report_path, report)  # type: ignore[arg-type]
    write_json(
        output_dir / "reports" / "latest.json",
        {"marketDate": report_date.isoformat(), "path": f"reports/{report_date.isoformat()}.json"},
    )
    return report_path


def command_demo(args: argparse.Namespace) -> int:
    snapshot, ledger, report = build_demo_documents(args.market_date)
    errors = validate_report(report, snapshot, ledger)  # type: ignore[arg-type]
    if errors:
        print("Demo generation failed validation:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 2
    report_path = _write_documents(args.output_dir, snapshot, ledger, report, report_only=args.report_only)
    print(report_path)
    return 0


def _with_required_baskets(
    universe: tuple[SecurityDefinition, ...],
) -> tuple[SecurityDefinition, ...]:
    output = list(universe)
    existing = {item.symbol for item in output}
    etfs = set((*DEFAULT_MARKET_ETFS, *DEFAULT_ETP_BASKET))
    for symbol in dict.fromkeys((*DEFAULT_MARKET_ETFS, *DEFAULT_ETP_BASKET, *DEFAULT_DIVIDEND_STOCKS)):
        if symbol not in existing:
            output.append(
                SecurityDefinition(
                    symbol=symbol,
                    name=symbol,
                    sector="ETF" if symbol in etfs else "Dividend Basket",
                    asset_type="etf" if symbol in etfs else "stock",
                )
            )
            existing.add(symbol)
    return tuple(output)


def command_snapshot(args: argparse.Namespace) -> int:
    config = PipelineConfig.from_env(require_credentials=True)
    universe = _with_required_baskets(
        load_or_refresh_universe(args.universe_csv, force_refresh=args.refresh_universe)
    )
    symbols = tuple(item.symbol for item in universe)
    client = AlpacaClient(
        config.alpaca_api_key or "",
        config.alpaca_secret_key or "",
        base_url=config.alpaca_data_url,
        feed=config.feed,
        max_retries=config.max_retries,
        timeout_seconds=config.request_timeout_seconds,
        batch_size=config.request_batch_size,
    )
    bars = client.get_daily_bars(
        symbols,
        start=args.market_date - timedelta(days=130),
        end=args.market_date + timedelta(days=1),
    )
    snapshot = build_market_snapshot(
        bars,
        universe,
        market_date=args.market_date,
        captured_at=datetime.now(timezone.utc),
        top_count=config.top_count,
        deep_count=config.deep_dive_per_direction,
    )
    write_json(args.output, snapshot)
    print(args.output)
    return 0


def command_validate(args: argparse.Namespace) -> int:
    raw_snapshot = read_json(args.snapshot)
    raw_ledger = read_json(args.ledger)
    raw_report = read_json(args.report)
    structural = [
        *validate_json_contract(raw_snapshot, "snapshot"),
        *validate_json_contract(raw_ledger, "ledger"),
        *validate_json_contract(raw_report, "report"),
    ]
    try:
        snapshot = parse_snapshot(raw_snapshot)
        ledger = parse_ledger(raw_ledger)
        report = parse_report(raw_report)
        errors = [*structural, *validate_report(report, snapshot, ledger)]
    except (KeyError, TypeError, ValueError) as exc:
        errors = [*structural, f"contract decoding failed: {exc}"]
    if errors:
        for error in dict.fromkeys(errors):
            print(error, file=sys.stderr)
        return 2
    print("publishable")
    return 0


def command_schemas(args: argparse.Namespace) -> int:
    for filename, schema in json_schemas().items():
        write_json(args.output_dir / filename, schema)
    print(args.output_dir)
    return 0


def command_refresh_universe(args: argparse.Namespace) -> int:
    definitions = fetch_sp500_universe()
    write_universe_csv(args.output, definitions)
    print(f"{args.output} ({len(definitions)} securities)")
    return 0


def command_preflight(args: argparse.Namespace) -> int:
    result = inspect_preflight(
        now=datetime.now(timezone.utc),
        universe_csv=args.universe_csv,
        repository=args.repository,
        existing_report=args.existing_report,
        expected_input_hash=args.input_hash,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 0 if result.ready else 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="market-tracker")
    subparsers = parser.add_subparsers(dest="command", required=True)
    default_date = latest_completed_market_date(datetime.now(timezone.utc))

    demo = subparsers.add_parser("demo", aliases=["fixture"], help="Generate a deterministic publishable fixture")
    demo.add_argument("--market-date", type=_parse_date, default=default_date)
    demo.add_argument("--output-dir", type=Path, default=Path("build/demo"))
    demo.add_argument("--report-only", action="store_true", help="Write only reports/<date>.json and latest.json")
    demo.set_defaults(handler=command_demo)

    snapshot = subparsers.add_parser("snapshot", help="Build MarketSnapshot from Alpaca daily bars")
    snapshot.add_argument("--market-date", type=_parse_date, default=default_date)
    snapshot.add_argument("--universe-csv", type=Path, default=Path("pipeline/.cache/sp500.csv"))
    snapshot.add_argument("--refresh-universe", action="store_true")
    snapshot.add_argument("--output", type=Path, required=True)
    snapshot.set_defaults(handler=command_snapshot)

    validate = subparsers.add_parser("validate", help="Apply the final publication gate")
    validate.add_argument("--snapshot", type=Path, required=True)
    validate.add_argument("--ledger", type=Path, required=True)
    validate.add_argument("--report", type=Path, required=True)
    validate.set_defaults(handler=command_validate)

    schemas = subparsers.add_parser("schemas", help="Write JSON Schema contracts")
    schemas.add_argument("--output-dir", type=Path, required=True)
    schemas.set_defaults(handler=command_schemas)

    universe = subparsers.add_parser("refresh-universe", help="Refresh the cached S&P 500 constituent CSV")
    universe.add_argument("--output", type=Path, default=Path("pipeline/.cache/sp500.csv"))
    universe.set_defaults(handler=command_refresh_universe)

    preflight = subparsers.add_parser("preflight", help="Inspect credentials, calendar, Git, and duplicate state")
    preflight.add_argument("--universe-csv", type=Path, default=Path("pipeline/.cache/sp500.csv"))
    preflight.add_argument("--repository", type=Path, default=Path.cwd())
    preflight.add_argument("--existing-report", type=Path)
    preflight.add_argument("--input-hash")
    preflight.set_defaults(handler=command_preflight)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.handler(args))
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
