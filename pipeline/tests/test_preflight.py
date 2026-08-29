from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path

from market_tracker.preflight import inspect_preflight


def test_dirty_worktree_blocks_preflight(tmp_path: Path, monkeypatch) -> None:
    subprocess.run(["git", "init", "--quiet"], cwd=tmp_path, check=True)
    tracked = tmp_path / "tracked.txt"
    tracked.write_text("clean\n", encoding="utf-8")
    universe = tmp_path / "sp500.csv"
    universe.write_text("symbol,name,sector\nAAPL,Apple,Technology\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "--quiet", "-m", "init"],
        cwd=tmp_path,
        check=True,
    )
    tracked.write_text("dirty\n", encoding="utf-8")
    monkeypatch.setenv("ALPACA_API_KEY", "test-key")
    monkeypatch.setenv("ALPACA_SECRET_KEY", "test-secret")

    result = inspect_preflight(
        now=datetime(2026, 8, 29, 0, tzinfo=timezone.utc),
        universe_csv=universe,
        repository=tmp_path,
    )

    assert result.git_dirty is True
    assert result.ready is False
