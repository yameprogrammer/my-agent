# 프로젝트 스프린트 보드 (Sprint Board)

소설 집필 에이전틱 머신 개발을 체계적으로 진행하기 위해 구성된 스프린트 보드입니다. 
에이전트가 컨텍스트 한계를 초과하지 않고, 각 단계별로 완벽한 테스트와 검증을 거쳐 오류 없이 빌드할 수 있도록 **마이크로 태스크(Micro-tasks)** 단위로 세분화하였습니다.

> [!NOTE]
> 세부적인 작업 히스토리 및 에이전트 간의 인수인계 사항은 **[development_log.md](file:///C:/Users/parkp/Workspace/personal/my-agent/design_docs/development_log.md)**에서 실시간으로 기록하고 추적합니다.


---

## 📅 스프린트 개요 및 상태 요약

| 스프린트 | 세부 단계 | 목표 | 진행 상태 |
| :--- | :--- | :--- | :--- |
| **Sprint 1** | **1-A** | 데이터베이스 설계 및 비동기 연결 수립 | 🎉 Done |
| | **1-B** | FastAPI 프로젝트 기본 골격 및 환경 설정 구성 | 🎉 Done |
| | **1-C** | JWT 인증 시스템 및 보안 미들웨어 구현 | 🎉 Done |
| **Sprint 2** | **2-A** | 프로젝트 CRUD 및 사용자 소유권 검증 API | 🎉 Done |
| | **2-B** | 설정집(WorldSetting/Lorebook) 및 캐릭터 CRUD | 🎉 Done |
| | **2-C** | 회차(Episode) 및 버전 트리형 본문(Content) API | 🎉 Done |
| **Sprint 3** | **3-A** | 각 역할군 에이전트 프롬프트 설계 & LLM 연동 | 🎉 Done |
| | **3-B** | LangGraph 워크플로우 구현 및 State/Checkpoint DB 연동 | 🎉 Done |
| | **3-C** | 키워드 RAG 파이프라인 및 무한 루프 제한 가드레일 | 🎉 Done |
| **Sprint 4** | **4-A** | FastAPI WebSocket/SSE 라우터 및 데이터 브로드캐스트 | 🎉 Done |
| | **4-B** | Streamlit 대시보드, 에디터 및 실시간 진행 상태 UI | 🟢 In Progress |
| | **4-C** | Human-in-the-loop 피드백 루프 연동 (승인/반려) | 🟢 In Progress |
| | **4-D** | 코드 리뷰 이슈 수정 (에이전트 루프·RAG·인증·보안) | 🟢 In Progress / 대부분 Done |
| **Sprint 5** | **5-A** | Termux 환경 PM2 프로세스 관리 및 Nginx 프록시 구성 | ⚪ To Do |
| | **5-B** | Cloudflare Tunnel 외부 접속 연동 및 DB 백업 체계 | ⚪ To Do |

> **리뷰 정본**: [code_review_2026-07-10.md](./code_review_2026-07-10.md)  
> **잔여 작업**: [remaining_work_2026-07-10.md](./remaining_work_2026-07-10.md) — 4-D 이후 P0~Sprint5 백로그 (다음 착수: **RW-01** API 키 암호화)

---

## 🏃‍♂️ Sprint 1: 기반 인프라 & 인증 (Phase 1)
- **에이전트 수행 가이드라인**: 각 하위 단계(1-A, 1-B, 1-C)가 끝날 때마다 실제 코드가 정상 작동하는지 테스트 스크립트 또는 Pytest를 통해 검증을 완료한 후 다음 단계로 넘어간다.

### 📍 Sprint 1-A: 데이터베이스 설계 및 비동기 연결 수립
- **목표**: 데이터 모델을 확정하고 비동기 PostgreSQL DB 엔진 세팅 완료
- **상태**: 🎉 Done

| Task ID | 작업 내용 | 우선순위 | 상태 | 구현/검증 수칙 |
| :--- | :--- | :---: | :---: | :--- |
| **S1-A1** | Docker Compose 기반 pgvector 탑재 PostgreSQL 로컬 띄우기 | High | ✅ Done | `docker compose up -d` 명령어 및 컨테이너 정상 구동 여부 확인 |
| **S1-A2** | SQLModel 기반 데이터 스키마 정의 (`User`, `Project`, `WorldSetting`, `Character`, `Episode`, `Content`) | High | ✅ Done | `Content` 테이블의 parent_id 관계 및 `WorldSetting` pgvector 임베딩 컬럼 선언 확인 |
| **S1-A3** | asyncpg 비동기 엔진 구성 및 데이터베이스 연결 시 `vector` 확장 활성화 설정 구현 | High | ✅ Done | DB 세션 연결 테스트 스크립트로 동작 확인 |
| **S1-A4** | PostgreSQL 테이블 마이그레이션/생성 및 임베딩 적재 테스트 | Medium | ✅ Done | 테이블 생성 및 목데이터(Mock Data) 적재/조회 E2E 테스트 |

### 📍 Sprint 1-B: FastAPI 기본 골격 구성
- **목표**: Clean Architecture 형태의 디렉토리 구조 및 환경 변수 연동 완료
- **상태**: 🎉 Done

| Task ID | 작업 내용 | 우선순위 | 상태 | 구현/검증 수칙 |
| :--- | :--- | :---: | :---: | :--- |
| **S1-B1** | FastAPI 디렉토리 패키지 구조 초기화 (`app/core`, `app/models`, `app/routers`, `app/services`) | Medium | ✅ Done | 구조 무결성 검증 |
| **S1-B2** | python-dotenv 기반 환경 변수(`.env`, `config.py`) 로드 로직 구현 | High | ✅ Done | 필수 변수 누락 시 에러 발생 가드 추가 |
| **S1-B3** | 비동기 세션 의존성 주입(`get_async_session`) 구성 및 간단한 DB 헬스체크 API 검증 | High | ✅ Done | API 응답 속도 및 세션 닫힘 보장 여부 확인 |

### 📍 Sprint 1-C: JWT 인증 시스템 & 보안 미들웨어
- **목표**: 사용자 인증 및 권한 가드 완비
- **상태**: 🎉 Done

| Task ID | 작업 내용 | 우선순위 | 상태 | 구현/검증 수칙 |
| :--- | :--- | :---: | :---: | :--- |
| **S1-C1** | Passlib(Bcrypt) 암호화 유틸리티 구현 | High | ✅ Done | 패스워드 검증 단위 테스트 (Bcrypt 최신 래퍼 적용) |
| **S1-C2** | PyJWT 기반 토큰 발급 및 검증 로직 구현 | High | ✅ Done | 만료 기간 처리 확인 |
| **S1-C3** | `/auth/register`, `/auth/login` 엔드포인트 구현 | High | ✅ Done | 중복 가입 예외 처리 |
| **S1-C4** | API 접근 권한 제어를 위한 `get_current_user` 의존성 주입(Dependency) 구현 | High | ✅ Done | 유효하지 않은 토큰 차단 테스트 |
| **S1-C5** | Sprint 1 통합 테스트 코드 작성 및 검증 | Medium | ✅ Done | Pytest 기반 E2E 인증 흐름 검증 |

---

## 🏃‍♂️ Sprint 2: 프로젝트 & 설정 데이터 관리 (Phase 2)
*(상세 마이크로 태스크는 Sprint 1 완료 후 필요시 재조정)*
- **Sprint 2-A**: 소설 프로젝트 CRUD API 개발 (소유권 검증 포함) [상태: 🎉 Done]
- **Sprint 2-B**: 설정집(Lorebook) 및 캐릭터 CRUD API 개발 [상태: 🎉 Done]
- **Sprint 2-C**: 회차(Episode) 및 parent_id 기반 버전 트리 조회 API 개발 [상태: 🎉 Done]

---

## 🏃‍♂️ Sprint 3: AI 에이전트 & LangGraph 워크플로우 (Phase 3)
- **Sprint 3-A**: 각 역할군 에이전트 프롬프트 설계 & LLM 연동 [상태: 🎉 Done]
- **Sprint 3-B**: LangGraph 워크플로우 정의 및 PostgresSaver 세션 체크포인트 저장 설정 [상태: 🎉 Done]
- **Sprint 3-C**: 키워드 기반 RAG 파이프라인 구현 및 무한 루프 제한 가드레일 작동 검증 [상태: 🎉 Done]

---

## 🏃‍♂️ Sprint 4: 실시간 웹 인터페이스 MVP (Phase 4)
- **에이전트 수행 가이드라인**: WebSocket 기반 스트리밍 전송과 Streamlit UI 화면 구성 및 Human-in-the-loop 승인/반려 피드백 흐름이 단절 없이 동작하는지 연동 테스트를 통하여 검증한다.

### 📍 Sprint 4-A: FastAPI WebSocket 라우터 구축
- **목표**: 실시간 에이전트 작업 상태 및 소설 본문 스트리밍용 WebSocket 엔드포인트 구축
- **상태**: 🎉 Done

| Task ID | 작업 내용 | 우선순위 | 상태 | 구현/검증 수칙 |
| :--- | :--- | :---: | :---: | :--- |
| **S4-A1** | WebSocket 연결 관리자(Connection Manager) 구현 | High | ✅ Done | 여러 클라이언트 연결/해제 및 개별/전체 브로드캐스트 기능 테스트 |
| **S4-A2** | FastAPI WebSocket 라우터 엔드포인트(`/ws/projects/{project_id}/episodes/{episode_id}/write`) 추가 | High | ✅ Done | LangGraph 상태 노드의 스트리밍 출력을 WebSocket 메시지로 전송하도록 연동 |
| **S4-A3** | WebSocket 통신 및 메시지 포맷 정의 | Medium | ✅ Done | 에이전트 상태(Plotter, Writer 등) 변경 이벤트 및 씬 본문 청크 JSON 포맷 검증 |

### 📍 Sprint 4-B: Streamlit 대시보드 및 실시간 UI 구현
- **목표**: Streamlit을 이용해 작가용 대시보드 UI 및 에이전트 현황 뷰어 제작 (안정성을 위해 3단계로 세분화하여 진행)
- **상태**: 🟢 In Progress

| Task ID | 작업 내용 | 우선순위 | 상태 | 구현/검증 수칙 |
| :--- | :--- | :---: | :---: | :--- |
| **S4-B1** | (UI 1단계) Streamlit 기본 대시보드 뼈대 구성 및 로그인/프로젝트 관리 화면 | Medium | ✅ Done | 기존 FastAPI JWT 인증 정보 저장 및 API 인증 헤더 연동 |
| **S4-B2** | (UI 2단계) 설정집(Lorebook) 및 캐릭터 관리, 회차 생성 인터페이스 구현 | Medium | ✅ Done | 세계관 설정 및 캐릭터 추가/수정/조회 UI 화면 구성 |
| **S4-B3** | (UI 3단계) 실시간 집필 모니터 화면 구현 (WebSocket 연동) | High | ✅ Done | WebSocket을 구독하여 에이전트 활동 상태 및 글쓰기 텍스트 실시간 렌더링 |

### 📍 Sprint 4-C: Human-in-the-loop 피드백 루프 연동
- **목표**: 승인/반려 및 사용자 윤문 가이드를 전달할 수 있는 피드백 루프 완성
- **상태**: 🟢 In Progress

| Task ID | 작업 내용 | 우선순위 | 상태 | 구현/검증 수칙 |
| :--- | :--- | :---: | :---: | :--- |
| **S4-C1** | LangGraph interrupt 대기 시 피드백/승인 수신 엔드포인트 구현 | High | ✅ Done | 사용자의 피드백 입력을 LangGraph thread config에 주입하고 resume 처리하는 API 구현 |
| **S4-C2** | Streamlit UI 내 피드백 및 승인/반려 상호작용 컴포넌트 탑재 | High | ✅ Done | 대기 상태(`waiting_user`) 감지 시 입력창과 버튼(승인/반려) 활성화 및 API 통신 |
| **S4-C3** | E2E 피드백 루프 통합 시나리오 테스트 | High | ✅ Done | 에이전트 생성 ➔ Human-in-the-loop 대기 ➔ 피드백 제공 후 재수정 혹은 승인 후 저장되는 전체 시나리오 검증 |

### 📍 Sprint 4-D: 코드 리뷰 이슈 수정 (Remediation)
- **목표**: 2026-07-10 전체 코드베이스 리뷰에서 발견된 P0/P1 이슈를 수정하고 Sprint 5 배포 전 정합성을 확보
- **상태**: 🟢 구현 완료 (잔여: Issue 9 평문 API 키 암호화, ConnectionManager, product_spec 고급 UX)
- **정본**: [code_review_2026-07-10.md](./code_review_2026-07-10.md)
- **권장 순서**: WP-A → WP-B → WP-C → WP-D → WP-E → Sprint 5

| Task ID | 작업 내용 | 우선순위 | 상태 | 구현/검증 수칙 |
| :--- | :--- | :---: | :---: | :--- |
| **S4-D1** | **WP-A** 에이전트 루프·HITL draft 정합성 (Issue 1, 2, 4) — Editor 라우팅, full-draft 피드백 경로, loop 소진 시 merge | High | ✅ Done | `tests/test_workflow.py` E2E + `route_after_editor` + loop merge 단위 테스트 통과 |
| **S4-D2** | **WP-B** RAG 임베딩 적재·차원 정책 (Issue 3, 7) — WorldSetting create/update 시 벡터 저장, 임베딩 모델 표준화 | High | ✅ Done | OpenAI 1536 고정; create/update 시 `generate_embedding` 호출 (키 없으면 soft-fail) |
| **S4-D3** | **WP-C** 인증·WS 가드·테스트·deps (Issue 5, 6, 8) — is_active 테스트/WS, requirements 보완 | High | ✅ Done | `activate_user` fixture; 미승인 403; WS `is_active` 검사; requirements 보강 |
| **S4-D4** | **WP-D** 배포 전 보안/헬스 하드닝 (Issue 9–12, 16, 18) | Medium | ✅ Done (9 부분) | production JWT 거부; health 503; webhook secret fail-closed; bcrypt 72B; Issue 9는 문서화+훅만 |
| **S4-D5** | **WP-E** UX/API 폴리시·nit (Issue 13–15, 17, 19, 21–23) | Low | ✅ Done (17 제외) | outline 스키마, 텔레그램 카피, session factory, bare except; ConnectionManager 는 후속 |

**설계 결정 (적용됨)**:
- WP-A: **옵션 A1** — Editor 후 `judge` 직행; HITL full-draft 피드백 후 Writer 스킵
- WP-B: **옵션 B1** — 채팅 LLM과 분리된 고정 1536-d OpenAI 임베딩
- WP-D Issue 9: **후속** — `API_KEY_ENCRYPTION_SECRET` 설정 슬롯만 추가, Fernet 암호화는 Sprint 5 전 별도 작업

---

## 🏃‍♂️ Sprint 5: 최적화 & Termux 배포 (Phase 5)
- **Sprint 5-A**: PM2 프로세스 관리 및 Nginx 프록시 연동 (로그 로테이션 포함)
- **Sprint 5-B**: Cloudflare Tunnel 외부 접속 연동 및 PostgreSQL pg_dump 자동 백업 스크립트 작성

