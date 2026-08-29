from datetime import date, datetime
from zoneinfo import ZoneInfo

from market_tracker.calendar import is_trading_day, latest_completed_market_date


def test_latest_completed_session_before_and_after_close() -> None:
    ny = ZoneInfo("America/New_York")
    assert latest_completed_market_date(datetime(2026, 8, 28, 15, 59, tzinfo=ny)) == date(2026, 8, 27)
    assert latest_completed_market_date(datetime(2026, 8, 28, 16, 0, tzinfo=ny)) == date(2026, 8, 28)


def test_weekend_and_observed_holiday_are_not_trading_days() -> None:
    assert not is_trading_day(date(2026, 8, 29))
    assert not is_trading_day(date(2026, 7, 3))  # July 4 falls on Saturday.
    assert latest_completed_market_date(
        datetime(2026, 7, 6, 7, 0, tzinfo=ZoneInfo("America/New_York"))
    ) == date(2026, 7, 2)


def test_dst_conversion_uses_new_york_market_time() -> None:
    seoul = ZoneInfo("Asia/Seoul")
    # 07:00 KST during US daylight saving time is 18:00 ET on the prior date.
    assert latest_completed_market_date(datetime(2026, 8, 29, 7, 0, tzinfo=seoul)) == date(2026, 8, 28)
