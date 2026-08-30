# 프로젝트 서브에이전트

이 디렉터리의 TOML 파일은 저장소와 함께 배포되는 Codex 프로젝트 전용 서브에이전트 정의입니다. 저장소를 clone한 뒤 프로젝트 루트에서 Codex를 열면 별도 개인 설정 복사 없이 역할을 불러옵니다.

| 파일 | 역할 | 단계 |
|---|---|---|
| `gainer_researcher.toml` | 상승 심층 종목 3개 근거 조사 | Loop 2 |
| `loser_researcher.toml` | 하락 심층 종목 3개 근거 조사 | Loop 2 |
| `market_theme_researcher.toml` | 시장·Nasdaq·ETF·섹터 테마 조사 | Loop 2 |
| `fact_checker.toml` | 수치·claimId·출처·시간 순서 검수 | Loop 5/6 |
| `blog_quality_reviewer.toml` | 초보자 이해도·구조·차트 연결 검수 | Loop 5/6 |
| `humanify_reviewer.toml` | 사실을 잠근 자연스러운 한국어 문장 검수 | Loop 5/6 |

## 공유 및 재배포 규칙

- `.codex/config.toml`, `.codex/agents/`, `.codex/contracts/`, `.codex/ORCHESTRATION.md`, `.codex/prompts/`, `.agents/skills/market-report-composer/`를 함께 Git에 포함합니다.
- 각 에이전트는 `sandbox_mode = "read-only"`, `approval_policy = "never"`로 정의합니다. 파일 작성과 발행은 상위 오케스트레이터만 담당합니다.
- `model`과 `model_reasoning_effort`는 의도적으로 지정하지 않습니다. 예약 작업 또는 사용자가 선택한 상위 Codex 모델과 추론 수준을 상속하므로, 공유받은 환경에서 지원 모델이 달라도 정의 파일을 수정할 필요가 없습니다.
- 동시 서브에이전트 수는 `.codex/config.toml`의 `max_concurrent_threads_per_session = 3`으로 제한합니다.
- 조사 결과와 검수 결과는 각각 `.codex/contracts/evidence-batch.schema.json`, `.codex/contracts/review-result.schema.json`을 따라야 합니다.
- API 키나 로컬 절대 경로를 TOML에 넣지 않습니다. 자격 증명은 Git에서 제외된 저장소 루트 `.env`에서만 읽습니다.
- OKF 지식 페이지는 결정론적 변환기가 생성하므로 별도 쓰기 에이전트를 두지 않습니다. 기존 연구 에이전트는 위키를 탐색 힌트로만 읽고, 기존 검수 에이전트는 지식 델타가 있을 때 `reviewTarget: "knowledge"`로 원본 보고서 추적성과 읽기 품질을 검사합니다.
- 세 검수 에이전트는 작성 Skill의 `leadStory`, `nextWatch`, 편집 순서 불변 조건도 독립적으로 검사합니다. Skill은 작성 규칙을 공유하지만 파일을 수정하는 주체는 여전히 오케스트레이터 하나뿐입니다.

변경 후 아래 검사로 여섯 역할의 필수 필드, 읽기 전용 설정, 모델 상속, 동시성 제한을 확인합니다.

```powershell
python -m pytest pipeline/tests/test_codex_agent_configs.py
```
