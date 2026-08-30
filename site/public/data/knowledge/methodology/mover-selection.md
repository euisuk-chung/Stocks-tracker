---
type: Attested Computation
title: 특징주 선정 방법
description: 등락률 순위와 거래량 이상치를 이용한 심층 종목 선정
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
web_route: /wiki/concepts/methodology/mover-selection/
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

상승률 상위 10개와 하락률 상위 10개를 먼저 정한 뒤 `abs(등락률) × max(거래량 배수, 1)` 점수로 방향별 심층 종목 3개를 선택합니다.

계산 정의는 Python 코드에 있고 회귀 테스트로 검증합니다.[^calculation-code][^calculation-tests]

# 해석 경계

이 값은 시장을 관찰하기 위한 분류이며 매수·매도 신호가 아닙니다.

[^calculation-code]: Deterministic calculation code
[^calculation-tests]: Calculation regression tests
