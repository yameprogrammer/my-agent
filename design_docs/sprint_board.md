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
| | **1-C** | JWT 인증 시스템 및 보안 미들웨어 구현 | 🟢 To Do |
| **Sprint 2** | **2-A** | 프로젝트 CRUD 및 사용자 소유권 검증 API | ⚪ To Do |
| | **2-B** | 설정집(WorldSetting/Lorebook) 및 캐릭터 CRUD | ⚪ To Do |
| | **2-C** | 회차(Episode) 및 버전 트리형 본문(Content) API | ⚪ To Do |
| **Sprint 3** | **3-A** | 각 역할군 에이전트 프롬프트 설계 & LLM 연동 | ⚪ To Do |
| | **3-B** | LangGraph 워크플로우 구현 및 State/Checkpoint DB 연동 | ⚪ To Do |
| | **3-C** | 키워드 RAG 파이프라인 및 무한 루프 제한 가드레일 | ⚪ To Do |
| **Sprint 4** | **4-A** | FastAPI WebSocket/SSE 라우터 및 데이터 브로드캐스트 | ⚪ To Do |
| | **4-B** | Streamlit 대시보드, 에디터 및 실시간 진행 상태 UI | ⚪ To Do |
| | **4-C** | Human-in-the-loop 피드백 루프 연동 (승인/반려) | ⚪ To Do |
| **Sprint 5** | **5-A** | Termux 환경 PM2 프로세스 관리 및 Nginx 프록시 구성 | ⚪ To Do |
| | **5-B** | Cloudflare Tunnel 외부 접속 연동 및 DB 백업 체계 | ⚪ To Do |

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
- **상태**: 🟢 To Do

| Task ID | 작업 내용 | 우선순위 | 상태 | 구현/검증 수칙 |
| :--- | :--- | :---: | :---: | :--- |
| **S1-C1** | Passlib(Bcrypt) 암호화 유틸리티 구현 | High | ⚪ To Do | 패스워드 검증 단위 테스트 |
| **S1-C2** | PyJWT 기반 토큰 발급 및 검증 로직 구현 | High | ⚪ To Do | 만료 기간 처리 확인 |
| **S1-C3** | `/auth/register`, `/auth/login` 엔드포인트 구현 | High | ⚪ To Do | 중복 가입 예외 처리 |
| **S1-C4** | API 접근 권한 제어를 위한 `get_current_user` 의존성 주입(Dependency) 구현 | High | ⚪ To Do | 유효하지 않은 토큰 차단 테스트 |
| **S1-C5** | Sprint 1 통합 테스트 코드 작성 및 검증 | Medium | ⚪ To Do | Pytest 기반 E2E 인증 흐름 검증 |

---

## 🏃‍♂️ Sprint 2: 프로젝트 & 설정 데이터 관리 (Phase 2)
*(상세 마이크로 태스크는 Sprint 1 완료 후 필요시 재조정)*
- **Sprint 2-A**: 소설 프로젝트 CRUD API 개발 (소유권 검증 포함)
- **Sprint 2-B**: 설정집(Lorebook) 및 캐릭터 CRUD API 개발
- **Sprint 2-C**: 회차(Episode) 및 parent_id 기반 버전 트리 조회 API 개발

---

## 🏃‍♂️ Sprint 3: 에이전틱 집필 엔진 & RAG (Phase 3)
- **Sprint 3-A**: Plotter, Writer, Judge, Editor 프롬프트 작성 및 API 테스트
- **Sprint 3-B**: LangGraph 워크플로우 정의 및 PostgresSaver 세션 체크포인트 저장 설정
- **Sprint 3-C**: 키워드 기반 RAG 파이프라인 구현 및 무한 루프 제한 가드레일 작동 검증

---

## 🏃‍♂️ Sprint 4: 실시간 웹 인터페이스 MVP (Phase 4)
- **Sprint 4-A**: FastAPI WebSocket 라우터 구축 (상태/스트리밍 브로드캐스트)
- **Sprint 4-B**: Streamlit 대시보드 화면 및 실시간 진행 상태 UI 구현
- **Sprint 4-C**: Human-in-the-loop 피드백/승인 루프 연동

---

## 🏃‍♂️ Sprint 5: 최적화 & Termux 배포 (Phase 5)
- **Sprint 5-A**: PM2 프로세스 관리 및 Nginx 프록시 연동 (로그 로테이션 포함)
- **Sprint 5-B**: Cloudflare Tunnel 외부 접속 연동 및 PostgreSQL pg_dump 자동 백업 스크립트 작성
