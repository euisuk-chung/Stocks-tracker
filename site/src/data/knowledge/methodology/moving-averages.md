---
type: Attested Computation
title: 1개월·2개월 이동평균선
description: 20거래일과 40거래일 종가 평균, 기울기와 이격률 계산
tags:
- methodology
- deterministic
- market-data
status: stable
runtime: python
parameters:
- name: market_date
  type: date
  required: true
computation: https://github.com/euisuk-chung/Stocks-tracker/blob/main/pipeline/src/market_tracker/calculations.py
executor:
  resource: https://github.com/euisuk-chung/Stocks-tracker/blob/main/README.md
  receipt:
  - market_date
  - input_hash
  - market_snapshot
attester:
  resource: https://github.com/euisuk-chung/Stocks-tracker/blob/main/pipeline/tests/test_calculations.py
web_route: /wiki/concepts/methodology/moving-averages/
generated:
  by: market-lens-methodology/1.0
  at: '2026-08-30T00:00:00+00:00'
verified:
  by: process:market-tracker-tests
  at: '2026-08-30T00:00:00+00:00'
sources:
- id: calculation-code
  resource: https://github.com/euisuk-chung/Stocks-tracker/blob/main/pipeline/src/market_tracker/calculations.py
  title: Deterministic calculation code
- id: calculation-tests
  resource: https://github.com/euisuk-chung/Stocks-tracker/blob/main/pipeline/tests/test_calculations.py
  title: Calculation regression tests
---

# Computation

최근 20개와 40개 종가의 산술평균을 각각 계산합니다. 5거래일 전 평균과 비교해 기울기를, 현재 종가와 비교해 이격률을 계산합니다.

계산 정의는 Python 코드에 있고 회귀 테스트로 검증합니다.[^calculation-code][^calculation-tests]

# 해석 경계

이 값은 시장을 관찰하기 위한 분류이며 매수·매도 신호가 아닙니다.

[^calculation-code]: Deterministic calculation code
[^calculation-tests]: Calculation regression tests
