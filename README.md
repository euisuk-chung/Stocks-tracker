# 마켓 렌즈 — 미국시장 특징주 분석기

미국장 마감 데이터를 결정론적으로 계산하고, 근거 조사와 읽기 품질 검수만 Codex 서브에이전트에 맡기는 초보자용 일일 시장 리포트 프로젝트입니다. 최종 결과는 Astro 정적 사이트로 빌드되어 GitHub Pages에 배포됩니다.

## 처리 구조

```text
예약 작업 (평일 07:00 KST, 전용 worktree)
  ├─ Loop 0: 거래일·환경·Git·중복 점검
  ├─ Loop 1: Python → 불변 MarketSnapshot
  ├─ Loop 2: 조사 에이전트 3개 병렬 실행
  ├─ Loop 3: EvidenceLedger 정규화
  ├─ Loop 4: 오케스트레이터 단독 작성
  ├─ Loop 5: 검수 에이전트 3개 병렬 실행
  ├─ Loop 6: 최대 2회 수정·재검수
  └─ 최종 게이트 → reports 브랜치 → GitHub Pages
```

가격, 순위, 거래량, 이동평균선, Nasdaq 국면은 Python만 계산합니다. 여섯 서브에이전트는 읽기 전용이며 파일을 수정하지 않습니다. 조사 보완은 전체 실행 중 1회, 수정·재검수는 2회로 제한됩니다.

## 폴더 안내

- `pipeline/`: Alpaca 수집, 미국 거래일, 계산, 증거 정규화, JSON 계약과 발행 검증
- `.codex/agents/`: 조사 3개와 검수 3개의 프로젝트 에이전트 정의
- `.codex/ORCHESTRATION.md`: 단일 작성자 원칙과 유한 상태 머신
- `.codex/prompts/scheduled-daily-report.md`: 예약 작업이 실행할 전체 지시문
- `site/`: Astro + React + ECharts 블로그형 정적 사이트
- `scripts/publish-report.ps1`: 검증된 JSON만 `reports` 브랜치에 발행하는 도구
- `.github/workflows/deploy-pages.yml`: `main` 코드와 `reports` 데이터를 합쳐 Pages 배포

## 로컬 설치

요구 사항은 Python 3.11+, Node.js 22+, PowerShell 7.5+, Git입니다.

```powershell
python -m pip install -e "pipeline[dev]"
cd site
npm ci
```

`.env.example`을 저장소 루트의 `.env`로 복사해 값을 입력합니다. 파이프라인은 실행할 때 이 파일을 자동으로 읽으며, 이미 설정된 프로세스 환경 변수가 있으면 그 값을 우선합니다. `.env`는 Git에서 제외되며 커밋하거나 공유하지 않습니다.

```text
APCA_API_KEY_ID=...
APCA_API_SECRET_KEY=...
ALPACA_DATA_URL=https://data.alpaca.markets
ALPACA_FEED=iex
```

## 데이터 파이프라인

S&P 500 구성 종목은 공개 구성표에서 갱신해 7일 동안 로컬 캐시합니다. `BRK.B`, `BF.B` 같은 클래스 주식 티커는 Alpaca가 요구하는 점 표기를 유지합니다.

```powershell
python -m market_tracker refresh-universe
python -m market_tracker preflight
python -m market_tracker snapshot --market-date 2026-08-28 --output build/2026-08-28/market-snapshot.json
```

API 키 없이 전체 계약과 사이트를 확인하려면 고정 데모를 생성할 수 있습니다.

```powershell
python -m market_tracker demo --market-date 2026-08-28 --output-dir build/demo
```

최종 발행 전 검증은 세 파일을 함께 대조합니다.

```powershell
python -m market_tracker validate `
  --snapshot build/2026-08-28/market-snapshot.json `
  --ledger build/2026-08-28/evidence-ledger.json `
  --report build/2026-08-28/reports/2026-08-28.json
```

## 사이트 실행

```powershell
cd site
npm run dev
npm run build
```

사이트는 최신 리포트, `/reports/` 아카이브, `/reports/YYYY-MM-DD/` 상세 경로를 제공합니다. 데모 JSON은 실제 계약과 같은 20개 특징주, 6개 심층분석, 70거래일 차트, 출처와 세 검수 결과를 포함합니다.

## 발행

`qa.publishable=true`이고 비밀정보 패턴이 없는 보고서만 발행할 수 있습니다.

```powershell
pwsh -File scripts/publish-report.ps1 `
  -ReportPath build/2026-08-28/reports/2026-08-28.json
```

스크립트는 임시 clone에서 `reports/YYYY-MM-DD.json`과 `index.json`을 만들고, 같은 SHA-256 입력은 중복 커밋하지 않습니다. `-NoPush`로 원격 변경 없이 발행 절차를 시험할 수 있습니다. Pages 워크플로는 사이트 빌드가 성공한 경우에만 새 배포를 활성화하므로 실패 시 이전 정상 사이트가 유지됩니다.

GitHub 저장소 Settings → Pages → Source는 **GitHub Actions**로 설정해야 합니다.

## 테스트

```powershell
python -m pytest pipeline
cd site
npm run build
```

테스트는 순위와 동률, 거래량 배수, 이동평균선과 국면, 결측 데이터, 7일 증거 범위, 재전송 기사, 사건 이후 기사, 독립 출처, 잘못된 claimId, 원본 수치·심층 표시 변경, Loop 상한, JSON 계약과 CLI 발행 게이트를 다룹니다.

## 운영 원칙

- SEC·기업 IR 같은 1차 자료는 단독 근거가 될 수 있습니다.
- 일반 뉴스는 같은 원문 재전송이 아닌 독립 출처 2개가 필요합니다.
- 반응 이후 공개된 기사를 원인으로 연결하지 않습니다.
- 근거 부족 시 `확인된 단일 촉매 없음`을 유지합니다.
- 차트와 이동평균선은 관찰 방법으로만 설명하며 매수·매도 신호로 단정하지 않습니다.
- API 키와 원시 에이전트 로그는 리포트, 커밋, 웹 번들에 포함하지 않습니다.

이 프로젝트와 생성 리포트는 교육 목적이며 투자 조언이 아닙니다.
