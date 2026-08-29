from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from .calendar import is_trading_day, latest_completed_market_date
from .config import PipelineConfig


@dataclass(frozen=True, slots=True)
class PreflightResult:
    ready: bool
    market_date: date
    trading_day: bool
    credentials_present: bool
    universe_present: bool
    git_repository: bool
    git_dirty: bool
    duplicate_input: bool
    messages: tuple[str, ...]

    def to_dict(self) -> dict:
        return {
            "ready": self.ready,
            "marketDate": self.market_date.isoformat(),
            "tradingDay": self.trading_day,
            "credentialsPresent": self.credentials_present,
            "universePresent": self.universe_present,
            "gitRepository": self.git_repository,
            "gitDirty": self.git_dirty,
            "duplicateInput": self.duplicate_input,
            "messages": list(self.messages),
        }


def inspect_preflight(
    *,
    now: datetime,
    universe_csv: Path,
    repository: Path,
    existing_report: Path | None = None,
    expected_input_hash: str | None = None,
) -> PreflightResult:
    market_date = latest_completed_market_date(now)
    config = PipelineConfig.from_env(require_credentials=False)
    credentials_present = bool(config.alpaca_api_key and config.alpaca_secret_key)
    universe_present = universe_csv.is_file()
    git_repository = (repository / ".git").exists()
    git_dirty = False
    if git_repository:
        completed = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repository,
            text=True,
            capture_output=True,
            check=False,
        )
        git_dirty = bool(completed.stdout.strip())
    duplicate_input = False
    if existing_report and existing_report.is_file() and expected_input_hash:
        try:
            raw = json.loads(existing_report.read_text(encoding="utf-8"))
            duplicate_input = raw.get("metadata", {}).get("snapshotHash") == expected_input_hash
        except (json.JSONDecodeError, OSError):
            duplicate_input = False
    messages: list[str] = []
    if not credentials_present:
        messages.append("Alpaca credentials are missing")
    if not universe_present:
        messages.append("Universe CSV is missing")
    if not git_repository:
        messages.append("Repository is not a Git worktree")
    if git_dirty:
        messages.append("Git worktree contains changes")
    if duplicate_input:
        messages.append("A report with the same snapshot hash already exists")
    ready = (
        credentials_present
        and universe_present
        and git_repository
        and not git_dirty
        and not duplicate_input
    )
    return PreflightResult(
        ready=ready,
        market_date=market_date,
        trading_day=is_trading_day(market_date),
        credentials_present=credentials_present,
        universe_present=universe_present,
        git_repository=git_repository,
        git_dirty=git_dirty,
        duplicate_input=duplicate_input,
        messages=tuple(messages),
    )
