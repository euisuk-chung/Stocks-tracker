from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timedelta, timezone

from market_tracker.demo import build_demo_documents
from market_tracker.evidence import normalize_ledger
from market_tracker.models import EvidenceItem, EvidenceLevel, EvidenceSource, ReportQa, ReviewVerdict, immutable_mapping
from market_tracker.validation import validate_ledger, validate_report


MARKET_DATE = date(2026, 8, 28)
NOW = datetime(2026, 8, 28, 20, tzinfo=timezone.utc)


def test_duplicate_sources_and_single_secondary_source_become_unknown() -> None:
    source_a = EvidenceSource("a", "Story", "Wire", "https://news.test/story?utm_source=x", NOW, NOW, False, "event")
    source_b = EvidenceSource("b", "Story copy", "Wire", "https://copy.test/story", NOW, NOW, False, "event")
    item = EvidenceItem(
        "claim", "AAPL", "claim", MARKET_DATE, MARKET_DATE, ("a", "b"),
        EvidenceLevel.SUPPORTED, "relevance", None, (),
    )
    ledger = normalize_ledger(market_date=MARKET_DATE, sources=(source_a, source_b), evidence=(item,), themes=())

    assert len(ledger.sources) == 1
    assert ledger.evidence[0].level == EvidenceLevel.UNKNOWN
    assert ledger.evidence[0].uncertainty


def test_same_independence_key_is_not_counted_as_two_sources() -> None:
    source_a = EvidenceSource(
        "a", "Original", "Outlet A", "https://a.test/story", NOW, NOW, False,
        independence_key="wire-story-1",
    )
    source_b = EvidenceSource(
        "b", "Syndicated", "Outlet B", "https://b.test/story", NOW, NOW, False,
        independence_key="wire-story-1",
    )
    item = EvidenceItem(
        "claim", "AAPL", "claim", MARKET_DATE, MARKET_DATE, ("a", "b"),
        EvidenceLevel.SUPPORTED, "relevance", None, (),
    )

    ledger = normalize_ledger(market_date=MARKET_DATE, sources=(source_a, source_b), evidence=(item,), themes=())

    assert ledger.evidence[0].level == EvidenceLevel.UNKNOWN


def test_source_outside_seven_day_window_is_rejected() -> None:
    snapshot, ledger, _ = build_demo_documents(MARKET_DATE)
    old_source = replace(ledger.sources[0], published_at=NOW - timedelta(days=8))
    invalid = replace(ledger, sources=(old_source, *ledger.sources[1:]))

    assert any("outside the 7-day" in error for error in validate_ledger(invalid, snapshot))


def test_unknown_claim_id_and_review_block_fail_publish_gate() -> None:
    snapshot, ledger, report = build_demo_documents(MARKET_DATE)
    bad_mover = replace(report.movers[0], claim_ids=("not-registered",))
    blocked_review = replace(report.reviews[1], verdict=ReviewVerdict.BLOCK)
    statuses = immutable_mapping({review.reviewer: review.verdict for review in (report.reviews[0], blocked_review, report.reviews[2])})
    bad_report = replace(
        report,
        movers=(bad_mover, *report.movers[1:]),
        reviews=(report.reviews[0], blocked_review, report.reviews[2]),
        qa=ReportQa(False, statuses, (), 1),
    )

    errors = validate_report(bad_report, snapshot, ledger)
    assert any("unknown claimIds" in error for error in errors)


def test_fact_checker_must_pass_even_when_qa_claims_publishable() -> None:
    snapshot, ledger, report = build_demo_documents(MARKET_DATE)
    revised = replace(report.reviews[0], verdict=ReviewVerdict.REVISE)
    statuses = immutable_mapping({review.reviewer: review.verdict for review in (revised, *report.reviews[1:])})
    bad_report = replace(report, reviews=(revised, *report.reviews[1:]), qa=ReportQa(True, statuses, (), 1))

    assert "qa.publishable does not match validation and review status" in validate_report(bad_report, snapshot, ledger)


def test_deep_dive_flags_must_match_immutable_snapshot() -> None:
    snapshot, ledger, report = build_demo_documents(MARKET_DATE)
    changed = replace(report.movers[0], deep_dive=False)
    bad_report = replace(report, movers=(changed, *report.movers[1:]))

    errors = validate_report(bad_report, snapshot, ledger)

    assert "report movers do not match snapshot rankings" in errors
    assert "report must identify exactly 6 deep-dive movers" in errors
