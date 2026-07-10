# 코드 리뷰 보고서 (2026-07-10)

> **범위**: 전체 코드베이스 (working tree clean, `main` @ 리뷰 시점)  
> **기준 문서**: `project_concept.md`, `product_spec.md`, `supplementary_design_specs.md`, `auth_telegram_design.md`, `sprint_board.md`  
> **스프린트 위치**: Sprint 4 말 (4-B/4-C 보드상 In Progress) / Sprint 5 배포 직전  
> **이슈 집계**: **8 bugs · 14 suggestions · 3 nits** (총 25건)  
> **구현 상태 (2026-07-10)**: P0 대부분 **resolved** — 잔여: Issue 9(암호화), 10(WS 쿼리 토큰), 14/17(UI·ConnectionManager), 24/25(백로그/Sprint5)

### 구현 완료 요약 (Sprint 4-D)

| Issue | 결과 |
| :---: | :--- |
| 1, 2, 4 | **resolved** — Editor→Judge(A1), HITL→user_review, loop merge |
| 3, 7 | **resolved** — WorldSetting 임베딩 + OpenAI 1536 고정 |
| 5, 6, 8 | **resolved** — activate_user, WS is_active, requirements |
| 11, 12, 16, 18 | **resolved** — webhook fail-closed, production JWT, health 503, bcrypt 72B |
| 13, 15, 19, 22 | **resolved** — outline 스키마, 텔레그램 카피, session factory, bare except |
| 9 | **open** — `API_KEY_ENCRYPTION_SECRET` 슬롯만 추가 |
| 10, 14, 17, 20–21, 23–25 | **open / backlog** |

---

## 1. 종합 평가 (Summary)

코드베이스는 design_docs와 정합하는 **로컬 MVP 스택**을 갖추고 있다.

- FastAPI + SQLModel/pgvector, JWT + 텔레그램 관리자 승인
- multi-LLM factory, LangGraph Plotter→RAG→Writer→Judge→Editor
- `interrupt_before` Human-in-the-loop, WebSocket 스트리밍, Streamlit 대시보드

소유권 가드와 API 키 응답 마스킹은 대체로 견고하고, 에이전트 그래프 **형태**는 `supplementary_design_specs.md`와 일치한다.

다만 Sprint 5 진입 전 지배적 리스크는 다음과 같다.

1. **에이전트 루프 정합성** — Editor 출력이 Writer에 의해 폐기되고, HITL 피드백 경로에서 draft가 오염될 수 있음
2. **RAG 임베딩 미적재** — 시맨틱 검색이 프로덕션에서 사실상 동작하지 않음
3. **인증/테스트 드리프트** — `is_active=False` 가입 정책과 테스트가 불일치
4. **배포 준비 미비** — 평문 API 키, WS 쿼리 토큰, `requirements.txt` 누락, 배포/백업 자동화 부재

**Verdict**: “시작 → 스트림 → 승인” 로컬 데모 수준은 가능하나, **자기 교정·HITL 재수정 경로를 올바르다고 간주하면 안 된다.** 임베딩 영속화 전까지 RAG Done 표기를 신뢰하지 말 것. Sprint 5 공개 배포 전 시크릿·WS 인증·의존성 핀을 강화할 것.

---

## 2. 이슈 목록

Severity: `bug` | `suggestion` | `nit`  
Status: 모두 `open` (리뷰 시점)

### 2.1 Bugs (P0 — 기능 정합성)

#### Issue 1 — Severity: bug
- **File**: `app/services/workflow.py:559-560`
- **Description**: 조건부 엣지가 항상 `editor → writer`. `WriterAgent.run`은 플롯/긴장/페이스만으로 씬을 재생성하고 Editor 수정문을 받지 않아 `current_scene_draft`가 덮어써진다. AI 자기 교정 루프가 LLM 호출만 소모하고 Judge 피드백을 반영하지 못한다.
- **Suggestion**: (a) `editor → judge`로 라우팅해 수정 후 Writer 스킵, 또는 (b) Writer가 `prior_draft`/`critique`를 받아 수정 모드로 동작. 선택 계약에 맞춰 테스트/목 갱신.
- **Status**: open
- **Work package**: WP-A

#### Issue 2 — Severity: bug
- **File**: `app/services/workflow.py:375-390`, `:559-560`
- **Description**: 전체 회차 HITL 피드백 시 Editor가 `draft`를 갱신한 뒤 여전히 Writer로 간다. Writer가 마지막 씬을 `current_scene_draft`에 재생성하고, Judge 통과 시 `draft + separator + current_scene_draft`로 append되어 본문이 중복/오염된다.
- **Suggestion**: full-draft 피드백 후 `user_review` 또는 전용 re-review/save 경로로 라우팅. 전체 draft 재심사가 필요하면 마지막 씬 append 금지.
- **Status**: open
- **Work package**: WP-A

#### Issue 3 — Severity: bug
- **File**: `app/routers/world_setting.py:25-35` (create), update ~99-106
- **Description**: WorldSetting create/update 시 `embedding=None`만 저장. 주석은 “Sprint 3에서 비동기 적재”이나 Sprint 3은 Done. `retrieve_relevant_lores` 시맨틱 분기는 `embedding != None` 필터로 키워드 매칭만 남음. `app/` 어디에도 embedding 할당 없음.
- **Suggestion**: create/update 시 프로젝트 LLM/임베딩 설정으로 `generate_embedding` 호출 후 벡터 영속화. 기존 행 백필. API 실패 시 soft-fail + 로그(키워드 경로 유지).
- **Status**: open
- **Work package**: WP-B

#### Issue 4 — Severity: bug
- **File**: `app/services/workflow.py:291-304`, `route_after_judge` `:493-496`
- **Description**: Judge 실패 + `loop_count >= 3` 시 `user_review`로 가며 `current_scene_draft`를 `draft`에 병합하지 않음. 빈 피드백 승인 시 `save_node`가 불완전 `draft`만 저장할 수 있음.
- **Suggestion**: 루프 소진 시 best-effort merge + `status=failed`/partial 플래그, 또는 완료 전 저장 거부 + WS 경고.
- **Status**: open
- **Work package**: WP-A

#### Issue 5 — Severity: bug
- **File**: `tests/test_auth.py:53-64`, `tests/test_project.py:24-36` 등
- **Description**: 가입 시 `is_active=False`, 로그인 403. 통합 테스트는 가입 직후 로그인 200을 기대. 텔레그램 승인 설계와 모순. `tests/test_telegram.py` 승인/거절 케이스는 `pass` 스텁.
- **Suggestion**: 가입 → 로그인 403 검증 → DB/웹훅으로 활성화 → 로그인 200. 텔레그램 웹훅 테스트 구현. CRUD 테스트 동일 activation fixture.
- **Status**: open
- **Work package**: WP-C

#### Issue 6 — Severity: bug
- **File**: `app/routers/websocket.py:46-67`
- **Description**: 비-TESTING 경로에서 소유권은 검사하나 **`user.is_active` 미검사**. 거절/비활성 후에도 JWT 만료 전까지 WS 사용 가능. `TESTING=="True"`면 소유권/존재 검사 전체 스킵.
- **Suggestion**: `get_current_user`와 동일하게 비활성 거부. TESTING 스킵은 pytest fixture/오버라이드로만 허용.
- **Status**: open
- **Work package**: WP-C

#### Issue 7 — Severity: bug
- **File**: `app/services/rag.py:14-39`, `app/models.py:60-63`
- **Description**: 컬럼 고정 `Vector(1536)` (OpenAI). Google `text-embedding-004`는 보통 768-d, Anthropic 임베딩 경로 없음, Ollama는 chat 모델일 수 있음. 차원 불일치 시 insert/query 실패.
- **Suggestion**: 프로젝트당 임베딩 프로바이더/차원 표준화. 채팅 모델과 분리된 고정 임베딩 모델 사용 권장.
- **Status**: open
- **Work package**: WP-B

#### Issue 8 — Severity: bug
- **File**: `requirements.txt`
- **Description**: 런타임이 `bcrypt`, `psycopg_pool`, `langchain_ollama`, `email-validator` 등을 import하나 requirements에 없음. 신규 설치/Termux 배포 시 import 또는 checkpointer 실패 가능. langgraph/langchain 핀 부재.
- **Suggestion**: `bcrypt`, `psycopg[binary]`, `psycopg-pool`, `langchain-ollama`, `email-validator` 명시 및 검증된 버전 핀.
- **Status**: open
- **Work package**: WP-C

### 2.2 Suggestions (P1–P2)

| ID | Severity | File | 요약 | WP |
| :--- | :--- | :--- | :--- | :--- |
| 9 | suggestion | `app/models.py:35`, `project.py` | 프로젝트 API 키 DB 평문 저장 | WP-D |
| 10 | suggestion | `websocket.py:29-32`, `monitor_view.py:70` | JWT를 WS 쿼리스트링으로 전달 (로그 유출) | WP-D |
| 11 | suggestion | `telegram.py:26-32`, `main.py:54` | 빈 webhook secret으로 set_webhook 가능 | WP-D |
| 12 | suggestion | `config.py:10` | 기본 JWT_SECRET으로 기동 가능 | WP-D |
| 13 | suggestion | `schemas/episode.py` | `Episode.outline` API/UI 미노출 | WP-E |
| 14 | suggestion | `ui/monitor_view.py` | 블로킹 WS 수신, 재연결 부재, draft 클리어 UX | WP-E |
| 15 | suggestion | `ui/app.py:39` | 가입 성공 문구가 여전히 “이메일 승인” | WP-E |
| 16 | suggestion | `main.py:87-105` | `/health` DB 장애 시에도 HTTP 200 | WP-D |
| 17 | suggestion | WS/workflow | ConnectionManager 부재, thread 동시 쓰기 race | WP-E |
| 18 | suggestion | `security.py:11-15` | 72바이트 초과 비밀번호 미검증 | WP-D |
| 19 | suggestion | `database.py:38-43` | 요청마다 sessionmaker 재생성 | WP-E |
| 20 | suggestion | `tests/test_websocket.py` | feedback/loop/inactive 경로 미커버 | WP-A/C |
| 24 | suggestion | `product_spec.md` vs `ui/*` | 고급 UX(플롯맵, 대조편집 등) 미구현 | backlog |
| 25 | suggestion | `docker-compose.yml` | Sprint 5 배포/백업 구성 부족 | Sprint 5 |

### 2.3 Nits (P3)

| ID | File | 요약 | WP |
| :--- | :--- | :--- | :--- |
| 21 | `main.py` / `auth.py` | `/users/me`와 `/auth/me` 중복 | WP-E |
| 22 | `ui/project_view.py:61-62` | bare `except:` | WP-E |
| 23 | `security.py` 등 | naive `datetime.utcnow` | WP-E |

---

## 3. Design alignment

### 잘 맞는 부분
- 텔레그램 승인 인증 (`is_active` / `rejected_at` / webhook secret + admin chat_id)
- 에이전트 그래프 토폴로지 및 `loop_count` 가드레일 **구조**
- Content `parent_id` 버전 트리, 소유권 가드, API 키 응답 마스킹
- multi-LLM, WebSocket 이벤트 형태, Streamlit MVP 화면

### 의도적 갭 / 다음 단계
- Sprint 5: Termux PM2, Nginx, Cloudflare Tunnel, `pg_dump` 백업 — 미착수
- product_spec 고급 UX — post-MVP 백로그
- 임베딩 ingestion — 설계 대비 미구현 (Issue 3)
- Connection Manager — 보드 Done이나 추상화 부재 (Issue 17)
- 텔레그램/승인 E2E 테스트 — 미비 (Issue 5)

---

## 4. 작업 패키지 (Remediation Plan)

Sprint 5 진입 **전** 아래 순서로 처리한다. 상세 태스크는 `sprint_board.md` → **Sprint 4-D** 참고.

| WP | 이름 | 포함 Issue | 우선순위 | 상태 | 예상 검증 |
| :--- | :--- | :--- | :---: | :---: | :--- |
| **WP-A** | 에이전트 루프·HITL draft 정합성 | 1, 2, 4, (20 일부) | P0 | ⚪ Ready | `tests/test_workflow.py`, feedback-resume 시나리오 |
| **WP-B** | RAG 임베딩 적재·차원 정책 | 3, 7 | P0 | ⚪ Ready | WorldSetting create 후 embedding NOT NULL, hybrid retrieve |
| **WP-C** | 인증·WS 가드·테스트·deps | 5, 6, 8, (20 일부) | P0 | ⚪ Ready | pytest 전체, 비활성 WS 거부 |
| **WP-D** | 배포 전 보안/헬스 하드닝 | 9–12, 16, 18 | P1 | ⚪ Ready | 설정 가드, health 503, 키 암호화 또는 문서화 결정 |
| **WP-E** | UX/API 폴리시·성능 nit | 13–15, 17, 19, 21–23 | P2 | ⚪ Ready | 스모크 UI, 단위 테스트 |
| **Backlog** | product_spec 고급 UX | 24 | P3 | ⚪ Later | — |
| **Sprint 5** | 배포·백업 | 25 + 5-A/5-B | — | ⚪ After 4-D | PM2/tunnel 체크리스트 |

### 권장 구현 순서
```
WP-A (루프) → WP-B (임베딩) → WP-C (인증/테스트/deps) → WP-D (보안) → WP-E (폴리시) → Sprint 5
```

### WP-A 설계 결정 (구현 전 확정 필요)
리뷰 제안 중 하나를 선택한다 (권장안 표시).

| 옵션 | 내용 | 권장 |
| :--- | :--- | :---: |
| **A1** | Editor 후 `judge`로 직행 (Writer 스킵). HITL full-draft 피드백 후 re-review/save | ✅ Recommended |
| **A2** | Writer에 revise 모드 추가 (`prior_draft` + `critique`) | 대안 |

HITL full-draft 경로: Editor 이후 **Writer로 가지 않음** (Issue 2 필수).

### WP-B 설계 결정
| 옵션 | 내용 | 권장 |
| :--- | :--- | :---: |
| **B1** | 채팅 LLM과 무관하게 OpenAI `text-embedding-3-small`(1536) 고정 (또는 env 지정) | ✅ Recommended |
| **B2** | 프로젝트별 임베딩 모델/차원 컬럼 도입 | 중기 |

### WP-D Issue 9 결정
| 옵션 | 내용 |
| :--- | :--- |
| **D1** | Fernet 등 env 키로 at-rest 암호화 |
| **D2** | DB 미저장, 세션/env 키만 사용 |

구현 시 옵션을 로그/문서에 명시한다.

---

## 5. 파일 영향 맵 (작업 착수 가이드)

| 영역 | 주요 파일 |
| :--- | :--- |
| 워크플로 | `app/services/workflow.py`, `app/services/agents.py` |
| RAG | `app/services/rag.py`, `app/routers/world_setting.py`, `app/models.py` |
| 인증/WS | `app/routers/auth.py`, `app/routers/websocket.py`, `app/core/dependencies.py` |
| 설정/보안 | `app/core/config.py`, `app/core/security.py`, `app/core/database.py` |
| 의존성 | `requirements.txt`, `uv.lock` |
| UI | `ui/app.py`, `ui/monitor_view.py`, `ui/project_view.py` |
| 테스트 | `tests/test_workflow.py`, `test_auth.py`, `test_project.py`, `test_telegram.py`, `test_websocket.py`, `conftest.py` |

---

## 6. 인수인계 (Handoff)

- 본 문서는 2026-07-10 전체 코드베이스 리뷰의 **정본(source of truth)** 이다.
- 구현 시작 시 `sprint_board.md` Sprint 4-D 태스크를 In Progress로 갱신하고, 완료 시 본 문서 Issue Status를 `resolved`로 바꾸거나 체크한다.
- 작업 로그는 `development_log.md`에 남긴다.
- **코드 수정은 아직 착수하지 않음** — 문서화 및 작업 패키지 Ready 상태까지 완료.

---

## 7. 원본 리뷰 아티팩트

로컬 임시 경로 (세션용, 저장소 외):

- Review: `%TEMP%\grok-review\grok-review-4a10b2b2.md`
- Summary: `%TEMP%\grok-review\grok-review-summary-4a10b2b2.md`
