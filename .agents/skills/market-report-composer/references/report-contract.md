# DailyReport message contract

The report keeps all deterministic market and evidence fields and adds two editorial structures.

## `leadStory`

```json
{
  "headline": "대형주는 버텼지만 중소형주·기술주는 더 약했다",
  "takeaway": "지수 전체보다 업종과 개별 종목 간 차이가 컸던 날입니다.",
  "supportingPoints": [
    { "role": "market", "text": "...", "claimIds": [] },
    { "role": "sector", "text": "...", "claimIds": [] },
    { "role": "catalyst", "text": "...", "claimIds": ["claim-001"] }
  ]
}
```

Contract rules:

- `headline` and `takeaway` must be non-empty and must not contain advice.
- `supportingPoints` contains exactly one each of `market`, `sector`, and `catalyst`.
- Snapshot-only observations use an empty `claimIds` array.
- Any causal or event explanation must contain registered ledger claim IDs.
- Do not repeat the Nasdaq regime wording already shown in the market map unless the regime change is itself the lead.

## `nextWatch`

```json
{
  "title": "금리 기대가 성장주 변동성으로 이어지는지",
  "description": "QQQ와 금리 민감 업종의 후속 반응을 다음 거래일 데이터로 확인합니다.",
  "symbols": ["QQQ"],
  "claimIds": ["claim-008"]
}
```

Contract rules:

- Include one to three items.
- Use `확인`, `후속 공시`, `후속 반응`, or equivalent observational language.
- Do not state that a price will rise, fall, outperform, or reach a target.
- `symbols` may be empty for market-wide checks.
- Event-derived items must preserve their ledger claim IDs.

## Validation invariants

- All referenced claim IDs exist in the EvidenceLedger.
- Lead figures are copied from MarketSnapshot.
- Every report retains exactly 20 movers and six deep dives.
- Unsupported deep dives keep the exact statement `확인된 단일 촉매 없음`.
- The report remains marked educational-only and passes all three reviewer gates.

