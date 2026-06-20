# UI 사용성 개선 방안 (UI/UX Improvement Plan)

> **2026-06-20 수정**: 사용자의 피드백("집필 소설을 프로젝트 단위로 관리하고, 프로젝트 목록 → 선택 후 스토리 빌드/에피소드 빌드 구조")을 적극 반영하여 한 뎁스를 추가한 계층형 네비게이션 구조로 전면 수정됨. 기존 기본 내용(워크플로우, 에이전트, 결과 렌더링 등)은 유지.

## 1. 배경 및 문제 요약

이 프로젝트는 `novel_blueprint/`의 사양서(00_overview.md ~ 11_mvp_roadmap.md)에 따라 설계·구현된 **AI 장편 웹소설 제작 운영 시스템**이다.

- 사용자는 `.\scripts\run.ps1` (또는 `.bat`, `.sh`)로 간단히 실행 가능하며, Streamlit 기반 **Admin Console**(`apps/admin/main.py`)이 주 UI이다.
- docs/usage_guide.md, handover 문서, 코드 분석 결과, 실제 사용 경험에 따르면 **UI의 사용성이 매우 미흡**하다.

**주요 문제점 (사용자 관점)**

1. **어떻게 시작해야 하는지 모름 (Onboarding Failure)**
   - 작품(novel)을 UI에서 생성할 수 없음. `python` 코드 또는 `bootstrap`을 써야 함 (usage_guide.md 5.3, 10절 명시).
   - `run` 스크립트 실행 후 브라우저가 열리지만, "다음에 뭐 해야 하는지" 안내 없음.
   - **프로젝트 계층이 없음**: 여러 집필 프로젝트를 나열하고 관리하는 최상위 화면이 없어, "이게 하나의 소설 프로젝트인가, 전체 시스템인가?"가 모호함.

2. **작동 방식과 결과물 확인 경로 불명확 (Discoverability Failure)**
   - Workflow Execution에서 워크플로우를 실행해도 **결과가 `st.json(result)`로만 덤프**됨.
   - 생성된 소설 본문(EPISODE_DRAFT), 아크 계획, 마스터 플랜 등을 **읽기 좋게 볼 수 있는 화면이 전혀 없음**.
   - Project Overview: 에피소드 목록만 raw 출력. 실제 텍스트 확인 불가.
   - Validation Review / System Logs: raw JSON + expander, 맥락(해당 화의 초안 텍스트) 없이 표시.

3. **워크플로우가 파이프라인처럼 느껴지지 않음 + 계층 구조 부재**
   - 3개 워크플로우(`theme_to_arcs`, `episode_to_draft`, `draft_validation`)가 평면 선택지.
   - 선행 단계(아크 계획)가 있어야 후속(회차 집필)이 의미 있다는 의존성이 UI에 드러나지 않음.
   - 현재 단계, 진행률, "다음 추천 액션" 없음.
   - **한 뎁스가 부족**: "프로젝트 목록 → 특정 프로젝트 선택 → 그 안에서 스토리 빌드 / 에피소드 빌드 / 워크플로우 실행" 의 명확한 2단계 구조가 없음.

4. **승인/검토 UX가 개발자용**
   - Validation 승인 버튼이 raw `sqlite3` 직접 호출 + `st.rerun()` hack (apps/admin/main.py:161~183).
   - 초안 수정, 재생성, 부분 승인 기능 없음.
   - 검수 이슈와 실제 초안 텍스트를 함께 볼 수 없음.

5. **산출물(결과물)의 저장 위치와 형태가 사용자에게 숨겨져 있음**
   - 실제 소설 텍스트는 `drafts` 테이블의 `EPISODE_DRAFT` kind + `content` 컬럼에 저장 (src/my_agent/repository.py:273, database.py:112).
   - UI 어디에서도 이 컨텐츠를 "읽기" 위한 뷰가 없음.
   - usage_guide.md조차 "Validation Review / System Logs에서 결과 확인"이라고만 안내.

## 2. 검사 대상 문서 및 코드

### 사양서 (novel_blueprint/)
- `00_overview.md`: UI/Ops Layer = "진행 상태를 보고 수동 승인·수정·재실행"
- `02_architecture.md`: "Author Console" — 작품 상태 시각적 확인 + 승인/수정
- `04_workflow.md`: 단계별 흐름(테마→아크→사이클→상세→집필→검수)
- `06_data_schema.md`: novels, arcs, episodes, drafts, validations, episode_plans, scene_beats 등
- `11_mvp_roadmap.md`: "간단한 승인 UI"가 Step 6

### 진행/사용 문서
- `docs/usage_guide.md`: Admin Console 메뉴 설명 + "UI에 작품 생성 없음" 명시 + Python API 예제 위주
- `docs/handover/05_phase5_complete.md`: Phase 5.3에서 "Admin Console UI" 구현 완료로 기술 (기능 중심, UX 고려 미흡)

### 구현 코드
- `apps/admin/main.py`: 4개 라디오 메뉴 (Project Overview, Workflow Execution, Validation Review, System Logs). 대부분 `st.table`, `st.write`, `st.json`, raw expander.
- `apps/admin/workflow_helpers.py`: 상태 빌더 (load_approved_arcs 등). UI 레이어와 강결합.
- `src/my_agent/repository.py`, `domain.py`, `schemas.py`: DraftKind.EPISODE_DRAFT, list_drafts 등은 잘 갖춰져 있으나 UI 미활용.
- `packages/orchestrator/workflows.py`: `theme_to_arcs` → `episode_to_draft` → `draft_validation`. 결과에 `*_output`, `*_decision`, `draft_text` 포함.
- `scripts/run.ps1`, `bootstrap.py`: 데모 자동 생성되지만, 그 이후 흐름 안내 없음.

## 3. 근본 원인 분석

- **MVP 우선순위**: 에이전트·워크플로우·검증 로직 구현에 집중. UI는 "간단한" 수준으로 남음 (handover, roadmap).
- **"Admin Console" vs "Author Console"**: 이름부터 운영자/개발자용으로 인식되어, 실제 소설 작가/편집자 관점의 UI가 설계되지 않음.
- **결과물 중심이 아닌 실행 중심 설계**: 워크플로우 실행 버튼이 주체. 실행 후 산출물을 어디서/어떻게 소비하는지 설계되지 않음.
- **Streamlit 한계 + 시간 부족**: 탭/사이드바 수준의 프로토타입을 넘어선 구조화된 대시보드 개발 미진.

## 4. 개선 목표 (User-Centric)

1. **신규 사용자도 5분 안에 "프로젝트 목록 → 특정 집필 프로젝트 선택 → 소설 한 화 읽기"까지 도달**
2. **"어디서 결과를 확인하나?" 질문이 나오지 않게 함**
3. **여러 집필 프로젝트를 관리(추가/선택/제거)하고, 선택한 프로젝트 안에서만 작업이 진행되는 명확한 계층 구조 제공**
4. **파이프라인 느낌을 주는 단계적 가이드 + 시각적 진행 상태** (스토리 빌드 → 에피소드 빌드 → 검수/워크플로우)
5. **원고(소설 본문)를 읽고, 검토하고, 승인/재생성하는 흐름을 직관적으로**
6. **사양서의 "Author Console" 비전(시각적 상태 확인 + 승인·수정)에 근접** (여러 프로젝트를 다루는 제작 스튜디오 느낌)

## 5. 개선 방안 (우선순위별)

사용자가 제안한 **"한 뎁스 더 추가한 프로젝트 중심 계층 구조"** 를 적극 반영한다. 
기본 아이디어는 다음과 같다:

- **최상위**: Projects Dashboard (집필 프로젝트 목록 보기, 추가, 제거, 간단 상태)
- **선택 후**: 해당 프로젝트 전용 Workspace
  - 스토리 빌드 (전체 기획: 테마/마스터 플랜/아크 설계)
  - 에피소드 빌드 (회차 계획 → 상세 → 집필 → 원고 확인)
  - 워크플로우 / 품질 관리 (실행, 검수, 승인)

이 구조는 기존 데이터 모델(`novel_id` 기반 multi-project 지원)이 이미 준비되어 있어 자연스럽다.

### A. 즉시 적용 (Quick Wins, 1~2일) — 프로젝트 계층 도입 최소 버전
- **Projects Dashboard 최상위 화면**:
  - 프로젝트 카드/테이블 목록 (제목, 장르, 상태, 최근 활동, 에피소드 수, 진행률 요약).
  - "새 집필 프로젝트 만들기" 폼 (novel_id/slug, title, genre, 간단 설명). UI에서 바로 생성 가능.
  - 프로젝트 선택 시 해당 프로젝트로 "진입" (session_state에 current_novel_id 저장).
  - 프로젝트 제거(삭제 또는 아카이브) 버튼 (확인 모달 필수, 데이터 파괴적임을 경고).
- **프로젝트 미선택 시**: 전체 시스템 개요 + 프로젝트 목록 + 생성 유도.
- **프로젝트 선택 후 헤더/사이드**: "현재 프로젝트: [제목] [전환 버튼]" 표시. 모든 하위 작업이 이 프로젝트에 스코프됨.
- **기본 결과 렌더링 즉시 적용**:
  - theme_to_arcs 실행 결과 → logline/premise/arcs 를 Markdown + 카드로 표시 (프로젝트 내부).
  - episode_to_draft → draft_text 를 `st.markdown` 으로 읽기 모드 제공.

### B. 핵심 UX 재설계 (1~2주) — 프로젝트 내부 워크스페이스
프로젝트를 선택하면 이제 **프로젝트 전용 대시보드 + 하위 섹션**으로 이동:

- **프로젝트 홈 (Project Dashboard)**:
  - 전체 진행 상황 요약 (메인 아크 수, 작성 완료 화 수 / 목표, 마지막 검수 상태, 현재 추천 단계).
  - 빠른 액션: "스토리 빌드 시작", "다음 에피소드 집필", "전체 품질 게이트 확인".
  - 최근 산출물 미리보기 (최근 생성된 아크 또는 드래프트 카드).

- **1. 스토리 빌드 (Story Build)** 섹션:
  - Theme Scout + Master Planner + Arc Planner 결과를 통합 뷰.
  - Logline, Premise, World Rules, Main/Sub Arcs 를 구조화된 카드/테이블 + Markdown으로 표시.
  - "스토리 빌드 실행 / 재실행" 버튼 (theme_to_arcs 워크플로우).
  - 승인 상태 및 다음 단계 안내.

- **2. 에피소드 빌드 (Episode Build & Manuscripts)** 섹션 (핵심):
  - 에피소드 목록 (번호, 제목, 상태, draft 유무, validation 점수).
  - 에피소드 선택 시 상세 패널:
    - Episode Cycle / Plan 요약
    - Scene Beats
    - **원고 (Draft)**: `st.markdown(draft_text)` 읽기 + 간단 편집/저장
    - Validation 결과 + Approve / Reject / "이 화만 재집필"
  - "새 에피소드 집필" 버튼 (선택한 화 또는 다음 화에 대해 episode_to_draft 실행).

- **3. 워크플로우 & 품질 관리 (Workflows & Quality)**:
  - 고급 실행(기존 Workflow Execution을 이 안에 통합, 항상 현재 프로젝트에 스코프).
  - Validation Review를 프로젝트/에피소드 필터로 고도화.
  - 전체 로그, 승인 대기 항목.

- **공통 지원**:
  - **Story Bible** 탭 (프로젝트 내부): characters, world_rules, threads, memory documents 등을 읽기 전용으로 제공.
  - 모든 화면에서 "현재 프로젝트" 컨텍스트가 유지되도록 `st.session_state` 적극 활용.
  - repo 기반 승인/상태 변경 (raw sqlite 완전 제거).

### C. 고도화 (후속)
- 프로젝트 목록에 **상태 배지 + 진행률 바** (스토리 완성도, 에피소드 작성 비율).
- 프로젝트별 **설정** (목표 화 수, 장르 타겟, 승인 정책 오버라이드 등).
- 프로젝트 제거 시 안전 장치 (아카이브 우선, 또는 연관 데이터 요약 후 삭제).
- 히스토리 비교, 원고 전체 export, "프로젝트 복제" 기능.
- 가이드 모드: "새 프로젝트로 첫 소설 만들기" wizard (프로젝트 생성 → 스토리 빌드 → 첫 화 집필).
- Workflow Execution은 "고급 수동 실행"으로 프로젝트 내부에 두고, 일상 흐름은 Story Build / Episode Build에서 유도.

이 구조를 적용하면 사용자는 **"여러 소설 프로젝트를 관리하다가, 하나의 프로젝트를 깊게 파고드는"** 자연스러운 멘탈 모델을 갖게 된다. 기존의 평면 4개 메뉴 문제를 근본적으로 해결한다.

상세한 실행 단계는 `ui-implementation-spec.md`의 **"4. 단계별 세분화 실행 계획 (8단계)"** 에 정리되어 있다. 
각 단계는 1~3일 단위로 나눠서 순차적으로 진행할 수 있도록 설계했다.

## 6. 데이터 흐름 관점에서 본 개선 포인트

- **프로젝트(작품) = 최상위 컨테이너**: 모든 데이터가 `novel_id` 로 스코프됨. UI에서 이 사실을 명확히 드러내야 함.
- **저장 위치 명확화**:
  - 프로젝트 자체: `novels` 테이블
  - 전체 구조(Arc Plan) → `drafts.kind=ARC_PLAN`
  - 회차 상세 → `episode_plans`, `scene_beats`
  - 본문 → `drafts.kind=EPISODE_DRAFT`
  - 검수 → `validations`
- UI 시각 계층: **Projects (목록/관리) → 선택된 Project Workspace → (Story Build / Episode Build / Quality) → 개별 Draft**
- 모든 조회/실행 시 `current_novel_id` 를 명시적으로 전달. `list_* (novel_id)` API를 철저히 활용.

## 7. 측정 기준 (Success Metrics)

- 신규 사용자가 스크립트 실행 → **프로젝트 목록 확인 → 새 프로젝트 생성 또는 선택 → 스토리 빌드 결과 확인 → 첫 에피소드 원고 읽기**까지 5분 이내 도달.
- "어디서 결과를 확인하나?" "이게 어떤 프로젝트의 결과인가?" 질문 0회.
- 프로젝트 목록에서 여러 프로젝트를 보고 전환하는 동작이 자연스럽게 느껴짐.
- Validation approve/reject가 draft와 함께 보이고, 1클릭으로 가능.
- 사용자가 "이 UI로 여러 소설 프로젝트를 관리하면서 실제 소설을 만들어 볼 수 있겠다"고 느끼는 수준.

## 8. 관련 문서 업데이트 필요

- `docs/usage_guide.md` 대폭 개정 (UI 중심 시나리오로).
- README.md의 Admin Console 설명 보강.
- `novel_blueprint/02_architecture.md`의 Author Console 설명을 최신 UI 비전으로 반영 (또는 별도 UI spec 링크).

---

**결론**: 현재 UI는 "워크플로우를 실행하는 개발자 도구"에 가깝다. 사용자가 제안한 **프로젝트 계층(Projects → Project Workspace)** 을 추가하면 "여러 집필 프로젝트를 관리하고, 선택한 프로젝트 안에서 스토리 빌드 → 에피소드 빌드 → 원고 확인"이라는 명확한 흐름이 생긴다.

이 구조는 기존 `novel_id` 기반 설계를 잘 활용하면서, 사양서의 Author Console 비전에 훨씬 가까워진다.

이 문서는 `ui-implementation-spec.md`의 기반이 된다. (사용자 제안이 반영되어 대폭 수정됨)
