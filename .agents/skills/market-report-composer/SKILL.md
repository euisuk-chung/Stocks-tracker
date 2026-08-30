---
name: market-report-composer
description: Compose, rebuild, or review the Korean beginner-facing US market daily report when the work must turn validated market data and evidence into one clear lead story, a scan-friendly section order, and a publishable report without inventing causes or investment advice.
---

# Market Report Composer

Create a daily report that a beginner can summarize in one sentence after a five-to-ten-minute read. Treat the validated `MarketSnapshot` as the only numeric source and the `EvidenceLedger` as the only source for causal explanations.

## Required inputs

- The immutable MarketSnapshot for the completed US trading date.
- The normalized EvidenceLedger with registered `claimId` and `sourceId` values.
- The current DailyReport contract and the previous validated report only when a state comparison is needed.

Prior reports and OKF pages are navigation memory, not evidence for the current market date. Never infer a current cause from a recurring theme name.

## Compose the message

1. Identify the widest verified contrast in the snapshot: index size/style, sector breadth, or unusually large stock-specific reactions.
2. Write a date-specific `leadStory.headline`. Do not use reusable headings such as “오늘 시장에서 놓치지 말아야 할 변화.”
3. Write `leadStory.takeaway` to answer “그래서 오늘은 어떤 날이었나?” in one sentence.
4. Add exactly three supporting points with roles `market`, `sector`, and `catalyst`.
   - `market` and `sector` figures must come only from the snapshot.
   - `catalyst` may state a cause only through valid ledger `claimIds`.
   - When evidence is insufficient, state how many deep-dive names have no confirmed single catalyst instead of inventing one.
5. Add one to three `nextWatch` items. Phrase them as facts or uncertainties to verify on the next trading day, never as predictions or trade instructions.

Read [references/report-contract.md](references/report-contract.md) before creating or changing report JSON. Read [references/editorial-sequence.md](references/editorial-sequence.md) when arranging, reviewing, or implementing the web report.

## Preserve the reading sequence

Use this information order:

1. Lead story and its three supports.
2. Market map: index ETFs, Nasdaq regime, and sector heatmap as one chapter.
3. Evidence-backed themes, zero to three.
4. Top ten gainers and top ten decliners.
5. Compact deep-dive overview grouped by confirmed catalyst versus no confirmed single catalyst.
6. Six detailed stock notes and charts.
7. Next-session verification items.
8. Sources, QA, and links to evergreen learning material.

Keep evergreen ETF family comparisons, glossary explanations, and methodology in the knowledge wiki. The daily report may link to them or show one contextually relevant note, but must not repeat the full guide every day.

## Review and publish

- The orchestrator remains the sole writer. Research and review agents stay read-only.
- Run `fact_checker`, `blog_quality_reviewer`, and `humanify_reviewer` against the complete report after the lead story and ordering are final.
- `fact_checker` must verify every lead figure and every lead or next-watch `claimId`.
- `blog_quality_reviewer` must verify that the headline, supporting points, themes, and deep dives tell the same story without repetition.
- Validate the report contract and OKF bundle before publication. A failed report or knowledge gate leaves the previous publication live.
- Never add buy, sell, hold, target-price, position-size, or forecast language.

