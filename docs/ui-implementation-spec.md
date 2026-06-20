# UI 개선 구현 작업 사양서 (UI Implementation Specification)

> **2026-06-20 수정**: 사용자가 제안한 "프로젝트 한 뎁스 더 추가" (프로젝트 목록 + CRUD + 선택 후 Workspace 내 스토리 빌드 / 에피소드 빌드 / 워크플로우)를 반영하여 전체 구조와 단계, 성공 기준, 수용 기준을 수정. 기본적인 에이전트·데이터 모델·워크플로우 내용은 그대로 유지하면서 UX 계층을 명확히 함.

## 1. 개요

**목표**: `docs/ui-improvement-plan.md`에서 정의한 개선 방안을 실제 코드 변경으로 실행에 옮긴다.

**배경**
- 현재 `apps/admin/main.py` + `workflow_helpers.py` 는 최소한의 Streamlit 프로토타입 수준.
- 사용자는 "결과물을 어디서 확인하나?" "어떻게 한 화를 완성하나?"를 알기 어려움.
- `novel_blueprint/02_architecture.md`의 "Author Console" 비전과 `04_workflow.md`의 단계별 흐름을 UI에 반영.

**성공 기준 (Definition of Done)**
- `.\scripts\run.ps1` (또는 동등) 실행 후, 브라우저에서 **프로젝트 목록 확인 → (새 프로젝트 생성 또는 데모 선택) → 프로젝트 진입 → 스토리 빌드 또는 에피소드 원고 읽기까지 4~5번 클릭 이내** 도달 가능.
- 생성된 draft_text, arc_plan, validation 이 **읽기 좋은 형태**로 표시됨 (항상 현재 선택된 프로젝트 스코프).
- 프로젝트 추가/선택/제거, 스토리 빌드, 에피소드 빌드, 워크플로우 실행, 승인 모두 **UI 내에서** 가능.
- 기존 테스트(`tests/test_admin_workflow.py` 등)와 기능 호환 (하위 호환 유지).

## 2. 범위

### 포함
- **프로젝트 계층 도입**: 최상위 Projects 목록 + CRUD + 프로젝트 선택 후 전용 Workspace.
- Streamlit Admin Console 대폭 개선 (기존 파일 리팩토링 + 새 로직, session_state 기반 프로젝트 컨텍스트).
- Repository / Schema 보강 (필요 시 update 메서드, episode별 조회 헬퍼, 프로젝트 요약 헬퍼).
- 사용자 가이드 업데이트 (usage_guide.md) — 프로젝트 중심 시나리오로 재작성.
- 간단한 시각적 진행 표시 및 원고 뷰어 (항상 선택된 프로젝트에 스코프).

### 제외 (이 단계)
- 새로운 백엔드 API 서버 (FastAPI).
- React 등 완전 재작성.
- 고급 시각화 (감정 곡선 차트 등).
- 실제 LLM 기반 재작성 루프 (StyleJudge, ReaderHook 연동은 별도).
- 프로젝트 삭제 시 cascade 삭제 (안전한 아카이브 또는 명시적 경고 수준으로 제한).

**기술 스택 유지**: Streamlit + 기존 `my_agent.*`, `packages.*`.

## 3. 현재 구조 요약 (참조)

| 위치 | 역할 | 문제 |
|------|------|------|
| `apps/admin/main.py` | 4개 메뉴 + 조잡한 렌더 | 결과 raw dump, novel 생성 없음, 검수 hack, **프로젝트 계층 부재** |
| `apps/admin/workflow_helpers.py` | 워크플로우 state 빌더 | UI와 결합, load_approved_arcs fallback 로직 |
| `src/my_agent/repository.py` | list_drafts, list_*, create_* | update_status 메서드 부족, 프로젝트 수준 요약 헬퍼 부족 |
| `packages/orchestrator/workflows.py` | 3개 빌더 워크플로우 | 결과 state가 UI 친화적이지 않음 |
| `docs/usage_guide.md` | 사용자 문서 | UI 중심 시나리오 부족 |

**핵심 데이터 모델 (이미 multi-novel 지원)**
- 프로젝트(집필 작품): `novels` + `NovelRead`
- 본문: `DraftRead` (kind=EPISODE_DRAFT, content=실제 텍스트)
- 구조: `list_arcs`, `list_episodes`, `list_episode_plans`, `list_scene_beats`
- 검수: `list_validations`

모든 작업은 `novel_id` 로 스코프되어야 하며, UI는 이를 "현재 선택 프로젝트"로 명시적으로 표현한다.

## 4. 단계별 세분화 실행 계획 (Granular Sequential Steps)

작업량이 상당하므로 **8개의 순차적 단계**로 세분화했다. 
각 단계는 **작은 범위 + 구체적 산출물 + 명확한 수용 기준**을 가지며, 이전 단계가 완료되어야 다음 단계로 진행할 수 있도록 설계했다.

**전략 원칙**
- 가능한 한 빨리 **사용자 가치**를 제공 (Step 2에서 이미 프로젝트 목록을 경험, Step 6에서 원고 확인 가능).
- 각 단계는 1~3일 정도의 집중 작업 단위로 나누기 좋음.
- 수직 슬라이스: 한 단계가 끝나면 해당 부분은 동작하고 테스트 가능.
- 프로젝트 스코프(`current_novel_id`)를 모든 단계에서 철저히 적용.

**단계 개요 표**

| Step | 제목                        | 주요 가치                     | 예상 기간 | 이전 단계 |
|------|-----------------------------|-------------------------------|-----------|-----------|
| 1    | 기반 인프라 준비            | Repository 헬퍼 + 컨텍스트   | 0.5~1일   | -         |
| 2    | Projects Dashboard          | 목록 + 새 프로젝트 생성       | 1~2일     | 1         |
| 3    | 프로젝트 컨텍스트 + 가드    | 선택된 프로젝트만 작업 가능   | 1일       | 2         |
| 4    | 프로젝트 홈                 | 상태 한눈에 파악              | 1일       | 3         |
| 5    | 스토리 빌드                 | 전체 구조 조회 + 실행         | 1.5~2일   | 3         |
| 6    | 에피소드 + 원고 뷰어        | **소설 본문 확인 (핵심)**     | 2~3일     | 3,5       |
| 7    | 집필 + 검수 + 승인          | 실행-검토 루프 완성           | 1.5~2일   | 6         |
| 8    | 마무리 + 문서화             | 사용성 + 가이드 + 검증        | 2~3일     | 7         |

### Step 1: 기반 인프라 준비 (Repository + 컨텍스트 유틸)
**목표**: 프로젝트 스코프 작업을 안전하고 쉽게 할 수 있는 기반을 마련한다.

**주요 작업**
- `src/my_agent/repository.py`에 추가:
  - `get_project_summary(novel_id: str) -> dict` (아크 수, 에피소드 수, 최근 draft 여부, pending validation 수 등)
  - `get_latest_draft(novel_id, kind)` 
  - `update_validation_status(validation_id, status)`
  - `update_draft_content(draft_id, new_content)` (선택)
  - (선택) `archive_novel` 또는 안전 삭제 헬퍼
- `apps/admin/` 안에 작은 `context.py` 또는 `project_context.py` 생성 (session_state 래퍼)
- `workflow_helpers.py`가 `novel_id`를 항상 명시적으로 받도록 정리

**산출물**
- Repository 헬퍼 메서드 + 간단 단위 테스트
- 프로젝트 컨텍스트 관리 유틸

**수용 기준**
- [ ] `repo.get_project_summary("demo-novel-001")` 이 의미 있는 정보를 반환
- [ ] 기존 테스트 전체 통과
- [ ] raw sqlite import가 아직 main.py에 남아 있어도 OK (다음 단계에서 제거)

**선행 단계**: 없음
**예상 노력**: 0.5 ~ 1일

### Step 2: Projects Dashboard — 프로젝트 목록 + 생성 (첫 사용자 가치)
**목표**: 앱을 켰을 때 "여러 집필 프로젝트를 관리한다"는 느낌을 즉시 준다.

**주요 작업**
- `apps/admin/main.py` 대대적 재구성 시작
- 사이드바 메뉴 대신 **Projects Dashboard**를 기본 화면으로
- 프로젝트 카드/테이블 구현 (title, genre, 상태, 에피소드 수, 최근 활동)
- "새 집필 프로젝트 만들기" 폼 (novel_id, title, genre, 설명)
- `repo.create_novel(...)` 호출 + 생성 후 자동 선택
- 프로젝트가 없을 때 안내 메시지

**산출물**
- 프로젝트 목록 화면 동작
- 새 프로젝트 생성 가능

**수용 기준**
- [ ] `.\scripts\run.ps1` 실행 → 프로젝트 목록이 첫 화면
- [ ] UI로 새 프로젝트 생성 → 목록에 즉시 나타남
- [ ] demo 프로젝트가 목록에 보임

**선행 단계**: Step 1
**예상 노력**: 1 ~ 2일

### Step 3: 프로젝트 컨텍스트 + 기본 레이아웃 가드
**목표**: "선택된 프로젝트 안에서만 작업한다"는 규칙을 강제하고 UI에 명확히 드러내기.

**주요 작업**
- 상단 또는 사이드바에 **"현재 프로젝트: XXX [변경]"** 표시기 구현
- `st.session_state["current_novel_id"]` 관리
- 프로젝트 미선택 상태에서 Story Build, Episode Build, 워크플로우 실행 시 "프로젝트를 먼저 선택하세요" 강제 안내
- 메뉴 구조 초기 정리 (프로젝트 선택 후에만 하위 섹션 노출)
- 프로젝트 선택 시 Workspace 영역으로 이동하는 로직

**산출물**
- 전역 프로젝트 컨텍스트
- 가드 로직

**수용 기준**
- [ ] 프로젝트를 선택하지 않으면 주요 빌드 버튼이 동작하지 않거나 명확한 안내
- [ ] 프로젝트 전환 후 이전 프로젝트 데이터가 섞이지 않음 (간단 확인)
- [ ] 현재 프로젝트 이름이 항상 화면에 표시

**선행 단계**: Step 2
**예상 노력**: 1일

### Step 4: 프로젝트 홈 (Project Dashboard)
**목표**: 프로젝트를 선택했을 때 "이 프로젝트의 현재 상태가 한눈에 보인다".

**주요 작업**
- 프로젝트 선택 후 기본 화면 = 프로젝트 홈
- 요약 카드: 총 아크 수, 작성된 에피소드 / 목표, 마지막 집필일, 승인 대기 건수
- `get_project_summary` 활용
- 빠른 액션 버튼 2~3개 (스토리 빌드 실행, 다음 에피소드 집필, 품질 게이트 보기)
- 최근 산출물 미리보기 (최근 아크 또는 최근 draft 제목)

**산출물**
- 프로젝트 홈 화면

**수용 기준**
- [ ] 프로젝트 선택 후 요약 정보가 정확히 표시
- [ ] 빠른 버튼 클릭 시 해당 영역으로 이동하거나 실행 유도

**선행 단계**: Step 3
**예상 노력**: 1일

### Step 5: 스토리 빌드 섹션 (전체 기획 조회 + 실행)
**목표**: 프로젝트의 큰 그림(스토리 구조)을 읽기 좋게 보고, 새로 빌드할 수 있다.

**주요 작업**
- "스토리 빌드" 탭/섹션 추가
- 기존 데이터 표시:
  - Logline, Premise, World Rules
  - Main Arcs / Sub Arcs 를 카드 또는 테이블 (arc_number, title, objective, episode_range)
- "스토리 빌드 실행" 버튼 → `theme_to_arcs` 호출 (현재 프로젝트 스코프)
- 실행 결과 즉시 예쁘게 렌더 (기존 `st.json` 대체)
- "에피소드 빌드로 이동" 유도 링크

**산출물**
- 스토리 빌드 화면 (조회 + 실행 + 결과 표시)

**수용 기준**
- [ ] theme_to_arcs 실행 후 logline/premise/arcs 목록이 Markdown/카드로 잘 보임
- [ ] 실행 결과가 해당 프로젝트에만 저장됨
- [ ] 기존 데이터가 있는 경우에도 바로 표시

**선행 단계**: Step 3 (Step 4와 병행 가능)
**예상 노력**: 1.5 ~ 2일

### Step 6: 에피소드 빌드 & 원고 뷰어 (가장 중요한 가치 제공 단계)
**목표**: 사용자가 "내가 쓴 소설 본문을 어디서 보는가?" 문제를 해결한다.

**주요 작업**
- "에피소드 빌드 & 원고" 섹션
- 에피소드 목록 (프로젝트 스코프): 번호, 제목, 상태, draft 존재 여부, validation 점수
- 에피소드 선택 → 상세 패널
  - Episode 계획 정보
  - Scene Beats
  - **원고**: `st.markdown(draft_text)` 로 소설처럼 표시 (가장 중요)
- (보너스) 간단 텍스트 편집 + 저장 (update_draft)

**산출물**
- 프로젝트 내 에피소드 목록 + 실제 본문 읽기 기능

**수용 기준**
- [ ] episode_to_draft 실행 후 생성된 draft_text가 목록에 나타나고, 선택 시 Markdown으로 읽기 가능
- [ ] 다른 프로젝트의 에피소드가 섞이지 않음
- [ ] draft가 없는 에피소드도 목록에 표시됨

**선행 단계**: Step 3, Step 5 (부분적으로)
**예상 노력**: 2 ~ 3일 (가장 큰 덩어리)

### Step 7: 집필 실행 + 검수/승인 통합
**목표**: 프로젝트 안에서 "집필 → 검수 → 승인"의 루프를 UI에서 완성한다.

**주요 작업**
- 에피소드 상세 패널에 "이 에피소드 집필 실행" 버튼 (`episode_to_draft`)
- "검수 실행" 버튼 (`draft_validation`)
- Validation 결과 + Approve / Reject (repository 메서드 사용, raw SQL 완전 제거)
- "다음 에피소드 추천" 로직 간단 추가
- Workflows 메뉴는 고급용으로 남겨두거나 프로젝트 스코프로 이동

**산출물**
- 에피소드 단위 집필 + 검수 + 승인 흐름

**수용 기준**
- [ ] 에피소드 상세에서 집필 버튼으로 draft 생성 가능
- [ ] 검수 후 Approve/Reject 가 정상 동작하고 DB에 반영
- [ ] raw sqlite3 코드가 admin/main.py에서 완전히 사라짐
- [ ] 승인/반려 후 목록의 상태가 업데이트됨

**선행 단계**: Step 6
**예상 노력**: 1.5 ~ 2일

### Step 8: 마무리, UX 세부, 문서화 및 검증
**목표**: 사용자가 실제로 쓸 수 있는 수준으로 완성하고 문서를 정리.

**주요 작업**
- 프로젝트 전환 시 하위 상태 초기화 안정화
- 각 섹션에 도움말/가이드 expander 대폭 추가
- "추천 다음 액션" 로직 (간단 if)
- `docs/usage_guide.md` 대폭 개정 (프로젝트 중심 빠른 시작 시나리오 작성)
- `README.md` 업데이트
- 수동 검증 체크리스트 작성 (docs에 추가)
- 불필요한 기존 메뉴 정리 (Validation Review, System Logs 등 통합 또는 격하)
- `tests/test_admin_workflow.py`에 프로젝트 스코프 관련 간단 테스트 추가
- (선택) 프로젝트 삭제 안전 처리

**산출물**
- 완성된 프로젝트 중심 UI
- 업데이트된 사용자 문서
- 검증 가능한 상태

**수용 기준**
- [ ] 전체 흐름 테스트: 새 프로젝트 생성 → 스토리 빌드 → 1~2화 집필 → 원고 확인 → 검수 → 승인
- [ ] usage_guide.md 가 프로젝트 계층을 중심으로 설명
- [ ] 기존 pytest 전체 통과
- [ ] raw SQL, `st.json` 덤프가 주요 화면에서 사라짐

**선행 단계**: Step 7
**예상 노력**: 2 ~ 3일

---

### 단계별 매핑 (참고)
- M1 (Quick Value): Step 1 ~ Step 3
- M2 (Core Value): Step 4 ~ Step 6
- M3 (Complete): Step 7 ~ Step 8

이 8단계를 순서대로 진행하면 점진적으로 가치가 쌓이고, 중간에라도 "지금까지 만든 것"을 실행해 볼 수 있다.

## 5. 구체적 변경 파일 목록 (예상)

### 생성/수정 파일 (단계별로 점진 적용)
- `docs/ui-implementation-spec.md`, `docs/ui-improvement-plan.md` (문서)
- `src/my_agent/repository.py` (Step 1)
- `apps/admin/main.py` (거의 모든 단계에서 수정 — 가장 큰 파일)
- 추천: Step 3 이후부터 `apps/admin/` 아래 컴포넌트 분리 시작
  - `project_context.py` 또는 `context.py`
  - `project_dashboard.py`
  - `story_build.py`
  - `episode_workspace.py`
  - `ui_components.py` (공통)
- `apps/admin/workflow_helpers.py` (Step 1, 5, 7)
- `docs/usage_guide.md` (주로 Step 8)
- `README.md` (Step 8)

**팁**: 한 번에 전체를 고치지 말고, Step 2에서 목록만 먼저 만들고, 이후 단계에서 점진적으로 main.py를 확장하는 방식으로 진행.

### DB / 마이그레이션
- SQLite + SQLAlchemy. 새 컬럼 불필요.
- 순수 메서드 추가 + UI 변경 중심.

## 6. 구현 우선순위 및 마일스톤 (8단계 기준)

- **M1: 프로젝트 계층 기반 (Step 1~3)**  
  프로젝트 목록, 생성, 선택 컨텍스트, 가드까지.  
  이 단계가 끝나면 사용자가 "여러 프로젝트를 관리한다"는 경험을 처음으로 함. (예상 3~5일)

- **M2: 핵심 빌드 경험 (Step 4~6)**  
  프로젝트 홈 + 스토리 빌드 + 에피소드 + 원고 읽기.  
  여기까지 오면 사용자가 실제로 소설 구조를 보고 본문을 확인할 수 있음. (예상 4~7일)

- **M3: 실행 + 검수 루프 완성 + 마무리 (Step 7~8)**  
  집필 트리거, 검수/승인 통합, raw SQL 제거, 가이드, 문서화.  
  전체 흐름이 닫히는 단계. (예상 4~6일)

**전체 예상 기간**: 11~18일 (1인 기준, 집중 작업 시).  
Streamlit UI 특성상 Step 2, Step 6, Step 8을 **주요 릴리스 포인트**로 삼아 점진적으로 검증하는 것을 추천. 

각 Step이 끝날 때마다 `streamlit run apps/admin/main.py`로 실제 동작 확인 후 다음 단계로 넘어가는 것을 강력 권장.

## 7. 수용 기준 (Acceptance Criteria) — 단계별 체크리스트

### M1 완료 기준 (Step 1~3)
- [ ] 프로젝트 목록이 첫 화면으로 열림
- [ ] UI에서 새 프로젝트 생성 가능
- [ ] 현재 프로젝트 선택기가 화면에 항상 표시
- [ ] 프로젝트 미선택 시 주요 작업 가드 동작

### M2 완료 기준 (Step 4~6)
- [ ] 프로젝트 홈에서 요약 정보 확인 가능
- [ ] 스토리 빌드에서 arcs가 읽기 좋게 표시 + 실행 결과 렌더링
- [ ] 에피소드 목록에서 draft가 있는 화 선택 시 `st.markdown`으로 본문 확인 가능
- [ ] 다른 프로젝트의 데이터가 섞이지 않음

### M3 완료 기준 (Step 7~8)
- [ ] 에피소드 상세에서 집필 실행 → 검수 → Approve/Reject 전체 루프 동작
- [ ] admin/main.py에 raw sqlite3 코드 완전 제거
- [ ] 프로젝트 중심 흐름이 `usage_guide.md`에 잘 문서화됨
- [ ] "새 프로젝트 → 스토리 빌드 → 1화 집필 → 원고 확인" 전체 시나리오가 5분 이내에 UI만으로 가능
- [ ] 기존 `pytest` 전체 통과 + 수동 검증 체크리스트 통과

### 전체 공통
- [ ] 기존 pytest 전부 통과
- [ ] `python main.py --init-db` + bootstrap 후 UI 정상 동작

## 8. 리스크 및 완화

- **Streamlit 복잡도 증가**: 프로젝트 계층 + 여러 섹션 때문에 복잡해짐. `ui_components.py` 등으로 적극 분리. M1에서는 Projects + 최소 Workspace로 시작.
- **Agent가 stub (template draft)**: 실제 텍스트 품질은 별개 이슈. UI는 "생성된 내용이 어디에 보이는가"와 "프로젝트별로 잘 격리되는가"에 집중.
- **상태 불일치**: `current_novel_id` 관리가 핵심. session_state + 명시적 `novel_id` 전달로 관리. 프로젝트 전환 시 하위 상태 초기화 필수.
- **기존 사용자 영향**: bootstrap demo는 "demo-novel-001" 프로젝트로 유지. 메뉴 구조 변화는 가이드와 함께 제공.
- **프로젝트 삭제 안전성**: 삭제 기능은 Phase 2 후반 또는 M3로 미루고, 우선 "아카이브" 또는 목록에서 숨기기만 제공하는 것도 고려.

## 9. 추가 고려사항

- **UI 용어 일관성**: 내부는 `novel` / `novel_id` 유지. 사용자에게는 **"프로젝트"**, **"집필 프로젝트"**, **"스토리 빌드"**, **"에피소드 빌드"** 등 한국어 라벨 사용. "Novel"이라는 단어는 기술 문서에만.
- **프로젝트 전환 UX**: 프로젝트 목록에서 클릭 한 번으로 Workspace 진입. 상단에 빠른 전환 드롭다운 제공.
- **성능**: 에피소드가 많아질 때 목록 가상화 또는 페이지네이션 고려 (현재는 소규모 MVP).
- **미래 확장**: 이 구조는 나중에 여러 프로젝트를 동시에 보는 대시보드나, 프로젝트 템플릿 기능으로 확장하기 좋음. 08_api_and_jobs.md 참고.
- **시각 자료**: 구현 후 `docs/` 에 실제 스크린샷(프로젝트 목록, 스토리 빌드 화면, 에피소드 원고 화면) 추가 강력 권장.

## 10. 참고

- [ui-improvement-plan.md](./ui-improvement-plan.md) (사용자 제안 반영본)
- [novel_blueprint/02_architecture.md](../novel_blueprint/02_architecture.md) — Author Console 비전
- [novel_blueprint/00_overview.md](../novel_blueprint/00_overview.md) — multi-project 지원 명시
- [docs/usage_guide.md](./usage_guide.md)
- [apps/admin/main.py](../apps/admin/main.py)
- [src/my_agent/repository.py](../src/my_agent/repository.py) (novel_id 스코프)
- Agents.md — "multi-project 지원"

---

**이 사양서에 따라 구현 시**, 사용자는 다음과 같은 흐름을 자연스럽게 경험할 수 있다:

1. 앱 실행 → **프로젝트 목록** 확인 (여러 집필 프로젝트 관리)
2. 새 프로젝트 추가 또는 기존 선택
3. **스토리 빌드**로 전체 구조 설계
4. **에피소드 빌드**로 회차 집필 + 원고 확인
5. 품질 게이트에서 검토 및 승인

사용자가 제안한 "한 뎁스 더" 구조가 기본 내용(기존 에이전트·워크플로우·데이터 모델)을 유지하면서 UX를 크게 개선한다.

구현 전 이 문서와 improvement-plan.md 를 리뷰하고, 점진적 PR(예: M1 먼저)로 진행하는 것을 권장한다.
