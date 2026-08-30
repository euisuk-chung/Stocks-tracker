from __future__ import annotations

import os
import re
import shutil
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import yaml

from .io import read_json, write_json


OKF_VERSION = "0.2"
GENERATED_DIRECTORIES = ("daily", "symbols", "themes", "instruments", "glossary", "methodology")
GENERATED_FILES = ("index.md", "log.md", "catalog.json")
VALID_STATUSES = {"draft", "stable", "deprecated"}
MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
FOOTNOTE = re.compile(r"\[\^([^\]]+)\]")
REPOSITORY_URL = "https://github.com/euisuk-chung/Stocks-tracker"


def _iso_datetime(value: object) -> str:
    text = str(value)
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"OKF timestamps require an explicit UTC offset: {text}")
    return text


def _yaml_frontmatter(values: dict[str, Any]) -> str:
    rendered = yaml.safe_dump(
        values,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
        width=100,
    ).strip()
    return f"---\n{rendered}\n---\n"


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8", newline="\n")


def _write_concept(path: Path, frontmatter: dict[str, Any], body: str) -> None:
    _write_text(path, f"{_yaml_frontmatter(frontmatter)}\n{body}")


def _reset_generated_content(output_root: Path) -> None:
    resolved = output_root.resolve()
    if output_root.name != "knowledge" or resolved == Path(resolved.anchor):
        raise ValueError("OKF output directory must be a non-root directory named 'knowledge'")
    output_root.mkdir(parents=True, exist_ok=True)
    for directory_name in GENERATED_DIRECTORIES:
        target = output_root / directory_name
        if target.exists():
            shutil.rmtree(target)
    for filename in GENERATED_FILES:
        target = output_root / filename
        if target.exists():
            target.unlink()


def _load_publishable_reports(report_paths: Iterable[Path]) -> list[tuple[Path, dict[str, Any]]]:
    reports: list[tuple[Path, dict[str, Any]]] = []
    for path in report_paths:
        raw = read_json(path)
        metadata = raw.get("metadata")
        qa = raw.get("qa")
        if not isinstance(metadata, dict) or not isinstance(qa, dict):
            raise ValueError(f"Report is missing metadata or qa: {path}")
        if qa.get("publishable") is not True:
            raise ValueError(f"Knowledge may only be compiled from publishable reports: {path}")
        market_date = str(metadata.get("marketDate", ""))
        if path.stem != market_date:
            raise ValueError(f"Report filename and metadata.marketDate differ: {path}")
        _iso_datetime(metadata.get("generatedAt"))
        reports.append((path, raw))
    if not reports:
        raise ValueError("At least one publishable report is required to compile knowledge")
    return sorted(reports, key=lambda item: str(item[1]["metadata"]["marketDate"]))


def _concept_record(
    *,
    concept_id: str,
    concept_type: str,
    title: str,
    description: str,
    path: str,
    route: str,
    tags: list[str],
    **extensions: Any,
) -> dict[str, Any]:
    return {
        "id": concept_id,
        "type": concept_type,
        "title": title,
        "description": description,
        "path": path,
        "route": route,
        "tags": tags,
        "status": "stable",
        "trust": "machine-confirmed",
        **extensions,
    }


def _daily_concept(
    report_path: Path,
    report: dict[str, Any],
    output_root: Path,
) -> tuple[Path, dict[str, Any]]:
    metadata = report["metadata"]
    market_date = str(metadata["marketDate"])
    year, month, _ = market_date.split("-")
    concept_id = f"daily/{year}/{month}/{market_date}"
    concept_path = output_root / f"{concept_id}.md"
    report_relative = Path(os.path.relpath(report_path.resolve(), concept_path.parent.resolve())).as_posix()
    sources = [
        {
            "id": "report-json",
            "resource": report_relative,
            "title": f"{market_date} validated DailyReport JSON",
        }
    ]
    for source in report.get("sources", []):
        sources.append(
            {
                "id": str(source["sourceId"]),
                "resource": str(source["url"]),
                "title": str(source["title"]),
            }
        )
    movers = list(report.get("movers", []))
    symbols = [str(item["symbol"]) for item in movers]
    themes = list(report.get("themes", []))
    lead_story = report.get("leadStory", {})
    lead_headline = str(lead_story.get("headline") or "미국시장 일일 보고서")
    lead_takeaway = str(
        lead_story.get("takeaway")
        or report.get("marketPulse", ["미국시장 일일 보고서"])[0]
    )
    frontmatter = {
        "type": "Daily Market Report",
        "title": f"{market_date} 미국시장 특징주 보고서",
        "description": lead_takeaway,
        "resource": report_relative,
        "tags": ["us-market", "sp500", "nasdaq", "daily-report"],
        "status": "stable",
        "market_date": market_date,
        "snapshot_hash": str(metadata["snapshotHash"]),
        "symbols": symbols,
        "theme_ids": [str(theme["themeId"]) for theme in themes],
        "web_route": f"/reports/{market_date}/",
        "generated": {"by": "process:market-lens-okf-export", "at": str(metadata["generatedAt"])},
        "verified": [
            {"by": "process:daily-report-validator", "at": str(metadata["generatedAt"])},
            {"by": "market-lens-fact-checker/1.0", "at": str(metadata["generatedAt"])},
        ],
        "sources": sources,
    }
    gainer_lines = []
    loser_lines = []
    for mover in movers:
        line = (
            f"* [{mover['symbol']}](/symbols/{mover['symbol']}.md) — "
            f"{float(mover['marketData']['changePct']):+.2f}%"
            f"{' · 심층분석' if mover.get('deepDive') else ''}"
        )
        (gainer_lines if mover["direction"] == "gainer" else loser_lines).append(line)
    theme_lines = [
        f"* [{theme['title']}](/themes/{theme['themeId']}.md) — {theme['summary']}"
        for theme in themes
    ] or ["* 근거 기준을 통과한 별도 테마가 없습니다."]
    source_lines = [
        f"* [{source['title']}]({source['url']}) — {source['publisher']}"
        for source in report.get("sources", [])
    ] or ["* 별도 외부 출처가 없습니다."]
    support_lines = [
        f"* **{str(item.get('role', 'context'))}** — {item.get('text', '')}"
        for item in lead_story.get("supportingPoints", [])
    ]
    body = "\n".join(
        [
            "# 오늘의 결론",
            "",
            f"## {lead_headline}",
            "",
            lead_takeaway,
            "",
            *support_lines,
            "",
            "이 페이지는 검증 완료 JSON에서 생성됐습니다.[^report-json]",
            "",
            "# 상승 특징주",
            "",
            *gainer_lines,
            "",
            "# 하락 특징주",
            "",
            *loser_lines,
            "",
            "# 주요 테마",
            "",
            *theme_lines,
            "",
            "# 외부 근거",
            "",
            *source_lines,
            "",
            "# 관련 방법론",
            "",
            "* [특징주 선정 방법](/methodology/mover-selection.md)",
            "* [1개월·2개월 이동평균선](/methodology/moving-averages.md)",
            "* [Nasdaq 국면 판정](/methodology/nasdaq-regime.md)",
            "",
            "[^report-json]: 검증 완료 DailyReport JSON",
        ]
    )
    _write_concept(concept_path, frontmatter, body)
    record = _concept_record(
        concept_id=concept_id,
        concept_type="Daily Market Report",
        title=frontmatter["title"],
        description=frontmatter["description"],
        path=f"{concept_id}.md",
        route=frontmatter["web_route"],
        tags=frontmatter["tags"],
        marketDate=market_date,
        symbols=symbols,
        themeIds=frontmatter["theme_ids"],
        updatedAt=str(metadata["generatedAt"]),
    )
    return concept_path, record


def _symbol_concepts(
    reports: list[tuple[Path, dict[str, Any]]],
    output_root: Path,
) -> list[dict[str, Any]]:
    occurrences: dict[str, list[dict[str, Any]]] = defaultdict(list)
    names: dict[str, str] = {}
    sectors: dict[str, str] = {}
    for _, report in reports:
        market_date = str(report["metadata"]["marketDate"])
        for mover in report.get("movers", []):
            symbol = str(mover["symbol"])
            market_data = mover["marketData"]
            names[symbol] = str(market_data.get("name") or symbol)
            sectors[symbol] = str(market_data.get("sector") or "미분류")
            occurrences[symbol].append(
                {
                    "marketDate": market_date,
                    "direction": str(mover["direction"]),
                    "rank": int(mover["rank"]),
                    "changePct": float(market_data["changePct"]),
                    "deepDive": bool(mover["deepDive"]),
                    "summary": str(mover["summary"]),
                    "claimIds": [str(item) for item in mover.get("claimIds", [])],
                    "reportRoute": f"/reports/{market_date}/",
                }
            )
    records: list[dict[str, Any]] = []
    latest_generated_at = str(reports[-1][1]["metadata"]["generatedAt"])
    for symbol in sorted(occurrences):
        items = sorted(occurrences[symbol], key=lambda item: item["marketDate"], reverse=True)
        source_entries = [
            {
                "id": f"report-{item['marketDate']}",
                "resource": f"/daily/{item['marketDate'][:4]}/{item['marketDate'][5:7]}/{item['marketDate']}.md",
                "title": f"{item['marketDate']} 미국시장 특징주 보고서",
            }
            for item in items
        ]
        frontmatter = {
            "type": "Security",
            "title": f"{symbol} · {names[symbol]}",
            "description": f"{symbol}이 특징주로 등장한 검증 보고서 타임라인",
            "resource": f"urn:market-lens:security:{symbol}",
            "tags": ["security", "sp500", sectors[symbol].lower().replace(" ", "-")],
            "status": "stable",
            "symbol": symbol,
            "sector": sectors[symbol],
            "web_route": f"/wiki/symbols/{symbol}/",
            "generated": {"by": "process:market-lens-okf-export", "at": latest_generated_at},
            "verified": {"by": "process:knowledge-validator", "at": latest_generated_at},
            "sources": source_entries,
        }
        lines = [f"# {symbol} 특징주 기록", "", f"{names[symbol]} · {sectors[symbol]}", "", "# 타임라인", ""]
        for item in items:
            direction = "상승" if item["direction"] == "gainer" else "하락"
            lines.extend(
                [
                    f"## {item['marketDate']}",
                    "",
                    f"* {direction} {item['rank']}위 · {item['changePct']:+.2f}%"
                    f"{' · 심층분석' if item['deepDive'] else ''}",
                    f"* {item['summary']}",
                    f"* [당일 보고서](/daily/{item['marketDate'][:4]}/{item['marketDate'][5:7]}/{item['marketDate']}.md)[^report-{item['marketDate']}]",
                    "",
                ]
            )
        for item in items:
            lines.append(f"[^report-{item['marketDate']}]: {item['marketDate']} 검증 완료 보고서")
        concept_id = f"symbols/{symbol}"
        _write_concept(output_root / f"{concept_id}.md", frontmatter, "\n".join(lines))
        records.append(
            _concept_record(
                concept_id=concept_id,
                concept_type="Security",
                title=frontmatter["title"],
                description=frontmatter["description"],
                path=f"{concept_id}.md",
                route=frontmatter["web_route"],
                tags=frontmatter["tags"],
                symbol=symbol,
                sector=sectors[symbol],
                occurrences=items,
                updatedAt=latest_generated_at,
            )
        )
    return records


def _theme_concepts(
    reports: list[tuple[Path, dict[str, Any]]],
    output_root: Path,
) -> list[dict[str, Any]]:
    themes: dict[str, list[dict[str, Any]]] = defaultdict(list)
    titles: dict[str, str] = {}
    latest_generated_at = str(reports[-1][1]["metadata"]["generatedAt"])
    security_symbols = {
        str(mover["symbol"])
        for _, report in reports
        for mover in report.get("movers", [])
    }
    fund_symbols = {
        str(item["symbol"])
        for item in [*reports[-1][1].get("marketEtfs", []), *reports[-1][1].get("incomeBasket", [])]
        if item.get("assetType") == "etf"
    }
    for _, report in reports:
        market_date = str(report["metadata"]["marketDate"])
        for theme in report.get("themes", []):
            theme_id = str(theme["themeId"])
            titles[theme_id] = str(theme["title"])
            themes[theme_id].append(
                {
                    "marketDate": market_date,
                    "summary": str(theme["summary"]),
                    "symbols": [str(item) for item in theme.get("symbols", [])],
                    "claimIds": [str(item) for item in theme.get("claimIds", [])],
                    "reportRoute": f"/reports/{market_date}/",
                }
            )
    records: list[dict[str, Any]] = []
    for theme_id in sorted(themes):
        items = sorted(themes[theme_id], key=lambda item: item["marketDate"], reverse=True)
        all_symbols = sorted({symbol for item in items for symbol in item["symbols"]})
        sources = [
            {
                "id": f"report-{item['marketDate']}",
                "resource": f"/daily/{item['marketDate'][:4]}/{item['marketDate'][5:7]}/{item['marketDate']}.md",
                "title": f"{item['marketDate']} 미국시장 특징주 보고서",
            }
            for item in items
        ]
        frontmatter = {
            "type": "Market Theme",
            "title": titles[theme_id],
            "description": f"검증 보고서에서 확인된 ‘{titles[theme_id]}’ 테마 타임라인",
            "resource": f"urn:market-lens:theme:{theme_id}",
            "tags": ["market-theme", *[symbol.lower() for symbol in all_symbols]],
            "status": "stable",
            "theme_id": theme_id,
            "symbols": all_symbols,
            "web_route": f"/wiki/themes/{theme_id}/",
            "generated": {"by": "process:market-lens-okf-export", "at": latest_generated_at},
            "verified": {"by": "process:knowledge-validator", "at": latest_generated_at},
            "sources": sources,
        }
        lines = [f"# {titles[theme_id]}", "", "# 관련 종목·상품", ""]
        for symbol in all_symbols:
            if symbol in security_symbols:
                lines.append(f"* [{symbol}](/symbols/{symbol}.md)")
            elif symbol in fund_symbols:
                lines.append(f"* [{symbol}](/instruments/{symbol}.md)")
            else:
                lines.append(f"* {symbol} — 현재 위키에 별도 개념 페이지가 없습니다.")
        lines.extend(["", "# 보고서별 기록", ""])
        for item in items:
            lines.extend(
                [
                    f"## {item['marketDate']}",
                    "",
                    item["summary"],
                    "",
                    f"[당일 보고서](/daily/{item['marketDate'][:4]}/{item['marketDate'][5:7]}/{item['marketDate']}.md)[^report-{item['marketDate']}]",
                    "",
                ]
            )
        for item in items:
            lines.append(f"[^report-{item['marketDate']}]: {item['marketDate']} 검증 완료 보고서")
        concept_id = f"themes/{theme_id}"
        _write_concept(output_root / f"{concept_id}.md", frontmatter, "\n".join(lines))
        records.append(
            _concept_record(
                concept_id=concept_id,
                concept_type="Market Theme",
                title=frontmatter["title"],
                description=frontmatter["description"],
                path=f"{concept_id}.md",
                route=frontmatter["web_route"],
                tags=frontmatter["tags"],
                themeId=theme_id,
                symbols=all_symbols,
                occurrences=items,
                updatedAt=latest_generated_at,
            )
        )
    return records


def _instrument_concepts(latest: dict[str, Any], output_root: Path) -> list[dict[str, Any]]:
    latest_generated_at = str(latest["metadata"]["generatedAt"])
    securities: dict[str, dict[str, Any]] = {}
    for item in [*latest.get("marketEtfs", []), *latest.get("incomeBasket", [])]:
        if item.get("assetType") == "etf":
            securities[str(item["symbol"])] = item
    records: list[dict[str, Any]] = []
    for symbol, item in sorted(securities.items()):
        concept_id = f"instruments/{symbol}"
        frontmatter = {
            "type": "Fund",
            "title": f"{symbol} · {item.get('name') or symbol}",
            "description": f"{symbol}의 시장 역할과 검증 보고서 관찰 기록",
            "resource": f"urn:market-lens:fund:{symbol}",
            "tags": ["fund", "etf", symbol.lower()],
            "status": "stable",
            "symbol": symbol,
            "web_route": f"/wiki/concepts/{concept_id}/",
            "generated": {"by": "process:market-lens-okf-export", "at": latest_generated_at},
            "verified": {"by": "process:knowledge-validator", "at": latest_generated_at},
            "sources": [
                {
                    "id": f"report-{latest['metadata']['marketDate']}",
                    "resource": f"/daily/{latest['metadata']['marketDate'][:4]}/{latest['metadata']['marketDate'][5:7]}/{latest['metadata']['marketDate']}.md",
                    "title": f"{latest['metadata']['marketDate']} 미국시장 특징주 보고서",
                }
            ],
        }
        body = "\n".join(
            [
                f"# {symbol}",
                "",
                f"{item.get('name') or symbol}은 일일 시장·입문 바스켓에서 추적하는 ETF입니다.",
                "",
                "# 최근 관찰",
                "",
                f"* 기준일: {latest['metadata']['marketDate']}",
                f"* 종가: ${float(item['close']):,.2f}",
                f"* 등락률: {float(item['changePct']):+.2f}%",
                "",
                "최근 가격은 상품의 장기 성격이나 적합성을 뜻하지 않습니다. 운용사 공식 자료의 지수, 보수, 분배 정책을 별도로 확인해야 합니다.",
            ]
        )
        _write_concept(output_root / f"{concept_id}.md", frontmatter, body)
        records.append(
            _concept_record(
                concept_id=concept_id,
                concept_type="Fund",
                title=frontmatter["title"],
                description=frontmatter["description"],
                path=f"{concept_id}.md",
                route=frontmatter["web_route"],
                tags=frontmatter["tags"],
                symbol=symbol,
                latestObservation={
                    "marketDate": str(latest["metadata"]["marketDate"]),
                    "close": float(item["close"]),
                    "changePct": float(item["changePct"]),
                },
                updatedAt=latest_generated_at,
            )
        )
    return records


def _static_concepts(output_root: Path) -> list[dict[str, Any]]:
    generated_at = "2026-08-30T00:00:00+00:00"
    concepts = [
        {
            "id": "glossary/volume-multiple",
            "type": "Financial Concept",
            "title": "거래량 배수",
            "description": "당일 거래량을 직전 20거래일 평균 거래량과 비교한 값",
            "tags": ["glossary", "volume"],
            "body": "# 정의\n\n거래량 배수는 당일 거래량을 직전 20거래일 평균 거래량으로 나눈 값입니다. 2배라면 평소보다 거래가 활발했다는 뜻이지만 방향이나 원인을 단독으로 설명하지는 못합니다.\n",
        },
        {
            "id": "glossary/moving-average",
            "type": "Financial Concept",
            "title": "이동평균선",
            "description": "일정 기간 종가의 평균을 이어 가격 흐름을 부드럽게 본 선",
            "tags": ["glossary", "moving-average"],
            "body": "# 정의\n\n이동평균선은 일정 기간의 종가 평균을 날짜별로 이어 만든 선입니다. 이 서비스는 1개월선에 20거래일, 2개월선에 40거래일을 사용하며 교차 하나만으로 매매 신호를 단정하지 않습니다.\n",
        },
        {
            "id": "glossary/expense-ratio",
            "type": "Financial Concept",
            "title": "ETF 총보수",
            "description": "ETF 운용 과정에서 자산에서 지속적으로 차감되는 연간 비용 비율",
            "tags": ["glossary", "etf", "fee"],
            "body": "# 정의\n\n총보수는 ETF를 운용하면서 펀드 자산에서 지속적으로 차감되는 비용 비율입니다. 같은 지수를 추종하는 상품을 장기 보유할 때는 유동성, 가격, 구조와 함께 비교할 항목입니다.\n",
        },
    ]
    records: list[dict[str, Any]] = []
    for concept in concepts:
        frontmatter = {
            "type": concept["type"],
            "title": concept["title"],
            "description": concept["description"],
            "tags": concept["tags"],
            "status": "stable",
            "web_route": f"/wiki/concepts/{concept['id']}/",
            "generated": {"by": "market-lens-editor/1.0", "at": generated_at},
            "verified": {"by": "process:knowledge-validator", "at": generated_at},
        }
        _write_concept(output_root / f"{concept['id']}.md", frontmatter, concept["body"])
        records.append(
            _concept_record(
                concept_id=concept["id"],
                concept_type=concept["type"],
                title=concept["title"],
                description=concept["description"],
                path=f"{concept['id']}.md",
                route=frontmatter["web_route"],
                tags=concept["tags"],
                updatedAt=generated_at,
            )
        )

    methodology = [
        (
            "moving-averages",
            "1개월·2개월 이동평균선",
            "20거래일과 40거래일 종가 평균, 기울기와 이격률 계산",
            "최근 20개와 40개 종가의 산술평균을 각각 계산합니다. 5거래일 전 평균과 비교해 기울기를, 현재 종가와 비교해 이격률을 계산합니다.",
        ),
        (
            "mover-selection",
            "특징주 선정 방법",
            "등락률 순위와 거래량 이상치를 이용한 심층 종목 선정",
            "상승률 상위 10개와 하락률 상위 10개를 먼저 정한 뒤 `abs(등락률) × max(거래량 배수, 1)` 점수로 방향별 심층 종목 3개를 선택합니다.",
        ),
        (
            "nasdaq-regime",
            "Nasdaq 국면 판정",
            "QQQ와 1개월·2개월 이동평균선으로 강세·중립·약세를 구분",
            "QQQ 종가, 20거래일선, 40거래일선의 순서와 두 선의 5거래일 기울기를 결정론적으로 조합합니다. 조건이 한쪽으로 정렬되지 않으면 중립입니다.",
        ),
    ]
    calculation_url = f"{REPOSITORY_URL}/blob/main/pipeline/src/market_tracker/calculations.py"
    test_url = f"{REPOSITORY_URL}/blob/main/pipeline/tests/test_calculations.py"
    for slug, title, description, computation_text in methodology:
        concept_id = f"methodology/{slug}"
        frontmatter = {
            "type": "Attested Computation",
            "title": title,
            "description": description,
            "tags": ["methodology", "deterministic", "market-data"],
            "status": "stable",
            "runtime": "python",
            "parameters": [{"name": "market_date", "type": "date", "required": True}],
            "computation": calculation_url,
            "executor": {
                "resource": f"{REPOSITORY_URL}/blob/main/README.md",
                "receipt": ["market_date", "input_hash", "market_snapshot"],
            },
            "attester": {"resource": test_url},
            "web_route": f"/wiki/concepts/{concept_id}/",
            "generated": {"by": "market-lens-methodology/1.0", "at": generated_at},
            "verified": {"by": "process:market-tracker-tests", "at": generated_at},
            "sources": [
                {"id": "calculation-code", "resource": calculation_url, "title": "Deterministic calculation code"},
                {"id": "calculation-tests", "resource": test_url, "title": "Calculation regression tests"},
            ],
        }
        body = "\n".join(
            [
                "# Computation",
                "",
                computation_text,
                "",
                "계산 정의는 Python 코드에 있고 회귀 테스트로 검증합니다.[^calculation-code][^calculation-tests]",
                "",
                "# 해석 경계",
                "",
                "이 값은 시장을 관찰하기 위한 분류이며 매수·매도 신호가 아닙니다.",
                "",
                "[^calculation-code]: Deterministic calculation code",
                "[^calculation-tests]: Calculation regression tests",
            ]
        )
        _write_concept(output_root / f"{concept_id}.md", frontmatter, body)
        records.append(
            _concept_record(
                concept_id=concept_id,
                concept_type="Attested Computation",
                title=title,
                description=description,
                path=f"{concept_id}.md",
                route=frontmatter["web_route"],
                tags=frontmatter["tags"],
                updatedAt=generated_at,
            )
        )
    return records


def _write_indexes(output_root: Path, records: list[dict[str, Any]], dates: list[str]) -> None:
    groups = [
        ("일일 보고서", "daily"),
        ("종목", "symbols"),
        ("시장 테마", "themes"),
        ("ETF·ETP", "instruments"),
        ("금융 용어", "glossary"),
        ("계산 방법", "methodology"),
    ]
    root_lines = [
        _yaml_frontmatter({"okf_version": OKF_VERSION}).rstrip(),
        "",
        "# 마켓 렌즈 지식 위키",
        "",
        "검증된 미국시장 보고서를 사람과 에이전트가 함께 탐색할 수 있게 구성한 OKF Bundle입니다.",
        "",
        "# 지식 영역",
        "",
    ]
    for title, directory in groups:
        count = sum(1 for record in records if record["id"].startswith(f"{directory}/"))
        root_lines.append(f"* [{title}]({directory}/) — {count}개 개념")
    root_lines.extend(
        [
            "",
            "# 원본과 신뢰 경계",
            "",
            "* `../reports/*.json`이 검증 가능한 발행 원본입니다.",
            "* 이 위키는 원본에서 파생되며 새로운 시장 주장의 독립 증거로 사용할 수 없습니다.",
            "* `verified`가 `process:` 또는 에이전트로만 구성된 문서는 machine-confirmed입니다.",
        ]
    )
    _write_text(output_root / "index.md", "\n".join(root_lines))

    for title, directory in groups:
        entries = [record for record in records if record["id"].startswith(f"{directory}/")]
        lines = [f"# {title}", ""]
        for record in sorted(entries, key=lambda item: item["title"]):
            relative = Path(record["path"]).relative_to(directory).as_posix()
            lines.append(f"* [{record['title']}]({relative}) - {record['description']}")
        _write_text(output_root / directory / "index.md", "\n".join(lines))

    log_lines = ["# Knowledge Bundle Update Log", ""]
    for market_date in sorted(dates, reverse=True):
        log_lines.extend(
            [
                f"## {market_date}",
                "",
                f"* **Compilation**: Added or refreshed the [{market_date} daily report](/daily/{market_date[:4]}/{market_date[5:7]}/{market_date}.md) and its linked concepts.",
                "",
            ]
        )
    _write_text(output_root / "log.md", "\n".join(log_lines))


def compile_knowledge_bundle(report_paths: Iterable[Path], output_root: Path) -> dict[str, Any]:
    reports = _load_publishable_reports(report_paths)
    _reset_generated_content(output_root)
    records: list[dict[str, Any]] = []
    for report_path, report in reports:
        _, record = _daily_concept(report_path, report, output_root)
        records.append(record)
    records.extend(_symbol_concepts(reports, output_root))
    records.extend(_theme_concepts(reports, output_root))
    records.extend(_instrument_concepts(reports[-1][1], output_root))
    records.extend(_static_concepts(output_root))
    records.sort(key=lambda item: (item["type"], item["id"]))
    market_dates = [str(report["metadata"]["marketDate"]) for _, report in reports]
    _write_indexes(output_root, records, market_dates)
    catalog = {
        "okfVersion": OKF_VERSION,
        "generatedAt": str(reports[-1][1]["metadata"]["generatedAt"]),
        "latestMarketDate": market_dates[-1],
        "concepts": records,
    }
    write_json(output_root / "catalog.json", catalog)
    errors = validate_knowledge_bundle(output_root)
    if errors:
        raise ValueError("Invalid OKF bundle:\n- " + "\n- ".join(errors))
    return catalog


def compile_knowledge_directory(reports_directory: Path, output_root: Path) -> dict[str, Any]:
    return compile_knowledge_bundle(sorted(reports_directory.glob("[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].json")), output_root)


def _split_frontmatter(path: Path) -> tuple[dict[str, Any] | None, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return None, text
    marker = text.find("\n---\n", 4)
    if marker < 0:
        raise ValueError("frontmatter closing delimiter is missing")
    raw_frontmatter = text[4:marker]
    parsed = yaml.safe_load(raw_frontmatter)
    if not isinstance(parsed, dict):
        raise ValueError("frontmatter must be a YAML mapping")
    return parsed, text[marker + 5 :]


def _validate_audit_entries(
    relative: str,
    field_name: str,
    value: object,
    errors: list[str],
) -> None:
    entries = value if isinstance(value, list) else [value]
    if value is None or not entries:
        errors.append(f"{relative}: {field_name} is required")
        return
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("by"), str) or not entry["by"].strip():
            errors.append(f"{relative}: every {field_name} entry requires a non-empty by")
            continue
        if not entry.get("at"):
            errors.append(f"{relative}: every {field_name} entry requires at")
            continue
        try:
            _iso_datetime(entry["at"])
        except ValueError as exc:
            errors.append(f"{relative}: {exc}")


def validate_knowledge_bundle(output_root: Path) -> list[str]:
    errors: list[str] = []
    root_index = output_root / "index.md"
    catalog_path = output_root / "catalog.json"
    catalog: dict[str, Any] | None = None
    catalog_paths: set[str] = set()
    if not root_index.is_file():
        errors.append("root index.md is missing")
    if not (output_root / "log.md").is_file():
        errors.append("root log.md is missing")
    if not catalog_path.is_file():
        errors.append("catalog.json is missing")
    else:
        loaded_catalog = read_json(catalog_path)
        if not isinstance(loaded_catalog, dict):
            errors.append("catalog.json must contain an object")
        else:
            catalog = loaded_catalog
            if catalog.get("okfVersion") != OKF_VERSION:
                errors.append("catalog okfVersion is unsupported")
            try:
                _iso_datetime(catalog.get("generatedAt"))
            except (TypeError, ValueError) as exc:
                errors.append(f"catalog generatedAt is invalid: {exc}")
            concepts = catalog.get("concepts")
            if not isinstance(concepts, list):
                errors.append("catalog concepts must be a list")
            else:
                concept_ids: list[str] = []
                for concept in concepts:
                    if not isinstance(concept, dict):
                        errors.append("catalog concepts must contain objects")
                        continue
                    concept_id = concept.get("id")
                    concept_path = concept.get("path")
                    if not isinstance(concept_id, str) or not concept_id.strip():
                        errors.append("every catalog concept requires an id")
                    else:
                        concept_ids.append(concept_id)
                    if not isinstance(concept_path, str) or not concept_path.strip():
                        errors.append(f"catalog concept {concept_id!r} requires a path")
                        continue
                    normalized_path = Path(concept_path)
                    if normalized_path.is_absolute() or ".." in normalized_path.parts:
                        errors.append(f"catalog concept {concept_id!r} has an unsafe path")
                        continue
                    catalog_paths.add(normalized_path.as_posix())
                    if not (output_root / normalized_path).is_file():
                        errors.append(f"catalog concept {concept_id!r} points to a missing file")
                if len(concept_ids) != len(set(concept_ids)):
                    errors.append("catalog concept ids must be unique")

    for path in sorted(output_root.rglob("*.md")):
        relative = path.relative_to(output_root).as_posix()
        try:
            frontmatter, body = _split_frontmatter(path)
        except (ValueError, yaml.YAMLError) as exc:
            errors.append(f"{relative}: invalid YAML frontmatter: {exc}")
            continue
        if path.name == "index.md":
            if path == root_index:
                if frontmatter != {"okf_version": OKF_VERSION}:
                    errors.append("root index.md must declare only okf_version 0.2")
            elif frontmatter is not None:
                errors.append(f"{relative}: nested index.md must not have frontmatter")
        elif path.name == "log.md":
            if frontmatter is not None:
                errors.append(f"{relative}: log.md must not have frontmatter")
        else:
            if frontmatter is None:
                errors.append(f"{relative}: concept frontmatter is missing")
                continue
            if not isinstance(frontmatter.get("type"), str) or not frontmatter["type"].strip():
                errors.append(f"{relative}: type is required")
            if not isinstance(frontmatter.get("title"), str) or not frontmatter["title"].strip():
                errors.append(f"{relative}: title is required by project policy")
            if frontmatter.get("status", "stable") not in VALID_STATUSES:
                errors.append(f"{relative}: status is invalid")
            _validate_audit_entries(relative, "generated", frontmatter.get("generated"), errors)
            _validate_audit_entries(relative, "verified", frontmatter.get("verified"), errors)
            stale_after = frontmatter.get("stale_after")
            if stale_after is not None:
                try:
                    _iso_datetime(stale_after)
                except ValueError as exc:
                    errors.append(f"{relative}: {exc}")
            sources = frontmatter.get("sources", [])
            if not isinstance(sources, list):
                errors.append(f"{relative}: sources must be a list")
                sources = []
            source_ids: list[str] = []
            for source in sources:
                if not isinstance(source, dict) or not source.get("resource"):
                    errors.append(f"{relative}: every source requires resource")
                    continue
                if source.get("id"):
                    source_ids.append(str(source["id"]))
            if len(source_ids) != len(set(source_ids)):
                errors.append(f"{relative}: source ids must be unique")
            used_footnotes = set(FOOTNOTE.findall(body))
            unknown_footnotes = used_footnotes - set(source_ids)
            if unknown_footnotes:
                errors.append(f"{relative}: footnotes reference unknown source ids: {', '.join(sorted(unknown_footnotes))}")

        for target_text in MARKDOWN_LINK.findall(body):
            target_text = target_text.split("#", 1)[0]
            if not target_text or target_text.startswith(("https://", "http://", "mailto:")):
                continue
            if target_text.startswith("/"):
                target = output_root / target_text.lstrip("/")
            else:
                target = path.parent / target_text
            if target.suffix == "":
                target = target / "index.md"
            if not target.exists():
                errors.append(f"{relative}: broken project link {target_text}")
    concept_paths = {
        path.relative_to(output_root).as_posix()
        for path in output_root.rglob("*.md")
        if path.name not in {"index.md", "log.md"}
    }
    if catalog is not None:
        for path in sorted(concept_paths - catalog_paths):
            errors.append(f"catalog is missing concept file {path}")
        for path in sorted(catalog_paths - concept_paths):
            errors.append(f"catalog lists a non-concept file {path}")
    return errors
