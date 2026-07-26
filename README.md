# 역사 연속형 국가대표 축구 세계 — 핵심 엔진

이 저장소는 UI보다 먼저 **하나의 세계 상태, 시간 순서, 참가 근거와 감사 가능성**을 구현한 Python 3.11 시뮬레이션 코어다. 초기 저장소에는 이 README 외 코드가 없었으므로, 외부 의존성 없는 모듈형 패키지로 첫 수직 구간을 구성했다.

## 현재 구현 범위

- 단일 `WorldState`: 날짜, 국가, 협회, 대표팀, 대회 회차, 이벤트 큐, 경기와 감사 로그
- 정치 주체·협회·대표팀의 분리 및 존속 기간 검증
- 카운터 기반 중앙 결정론 난수와 저장 가능한 난수 상태
- 날짜/우선순위/삽입 순서가 안정적인 이벤트 처리
- 출처 상태를 포함한 회차별 규칙과 개막 전 규칙 동결 게이트
- 참가 근거, 예선/자동 진출 근거와 본선 슬롯 일치 검증
- Elo형 제로섬 레이팅 및 즉시 명성 효과와 지연된 문화/인프라 효과 분리
- 구조화되고 자동 복구되지 않는 `ConsistencyViolation`
- JSON 세이브/로드와 과거 기록을 검사하는 초기 `TimelineAuditor`
- 1934년 이집트 우승이 1938년 디펜딩 챔피언 자동 진출로 이어지는 회귀 시나리오

규칙 fixture의 `USER_DEFINED` 표시는 실제 역사 규칙을 검증했다고 과장하지 않기 위한 의도적인 제한이다. 현 단계는 2개 팀으로 인과 연결을 검증하는 수직 슬라이스이며, 실제 1908–1938 전체 참가국·일정·사료 데이터는 아직 포함하지 않는다.

## 실행 및 테스트

```bash
python -m pytest
```

패키지는 `src/football_world` 아래에서 UI와 독립적으로 동작한다. `build_early_world(seed)`로 고정 시드 세계를 만들고 `WorldEngine.advance_to(...)`로 사건을 시간순 처리한다.

Vercel 프로젝트의 **Root Directory는 비워 두거나 저장소 루트(`Footballl2`)로 설정해야 한다. `src` 또는 `tests`로 설정하면 안 된다.** `pyproject.toml`, `vercel.json`, `index.py`는 모두 저장소 루트를 기준으로 탐색되기 때문이다. `vercel.json`은 모든 URL을 루트 `index.py` Python Function으로 전달하고, `index.py`는 HTTP 구현이 있는 `api/index.py`의 WSGI 앱을 내보낸다. 루트 경로에는 한국어 상태 화면이, `/api/health`에는 초기 세계를 실제로 생성해 확인한 JSON 상태가 반환된다.

Vercel 설정:

- Framework Preset: `Other`
- Root Directory: 비움 (`.` / 저장소 루트)
- Build Command: 비움
- Output Directory: 비움

로컬에서는 다음과 같이 실행할 수 있다.

```bash
python api/index.py
```

## 다음 단계

가장 먼저 NOC·올림픽 엔트리·선수단·선수 등록 개체와 `EligibilityValidator`/시대별 이동 검증기를 추가한 뒤, 검증된 1908년 올림픽 규칙 데이터로 첫 실제 회차를 구성해야 한다. 이후에만 경기 생성 범위를 확대한다.
