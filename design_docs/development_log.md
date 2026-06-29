# 에이전트 누적 개발 일지 (Development Log)

본 문서는 프로젝트 진행에 참여하는 에이전트들이 작업 내역, 기술적 결정 사항, 이슈 및 인수인계 사항을 기록하는 누적 일지입니다.
새로운 작업을 시작하거나 마칠 때 반드시 이 문서에 로그를 남겨주세요.

---

## 📝 개발 일지 기록 작성 규칙
1. **헤더 양식**: `## [YYYY-MM-DD] 작업 내용 요약 - 작성 에이전트명`
2. **기록 항목**:
   - **수행 태스크**: `sprint_board.md` 기준 어떤 Task ID들을 완료했는지 기재
   - **주요 구현 내용**: 작성된 핵심 모듈, 함수, 테스트 코드 위치
   - **기술적 결정 및 특이사항**: 개발 과정에서 내린 설계 변경 사항이나 발생한 이슈 해결 과정
   - **다음 에이전트 인수인계 사항 (Handoff)**: 이어서 해야 할 작업, 유의할 점

---

## 📖 로그 히스토리

## [2026-06-29] 프로젝트 기획/설계 검토 및 마이크로 스프린트 보드 수립 - Antigravity

- **수행 태스크**: 
  - [x] 전체 기획서 분석 및 요구사항 완결성 검토
  - [x] 에이전트 및 DB 비동기/버전 관리 공백 메우기 위한 보완 설계 사양 구축
  - [x] 에이전트 간 인수인계가 원활하도록 마이크로 태스크 중심 스프린트 보드 및 인수인계 프로토콜(README.md) 구축
- **주요 구현 내용**:
  - `design_docs/supplementary_design_specs.md` 생성
  - `design_docs/sprint_board.md` 생성
  - `README.md` 가이드라인 보강 업데이트
- **기술적 결정 및 특이사항**:
  - 에이전트 교체 상황에 완벽히 대처할 수 있도록 스프린트 보드에 '구현/검증 수칙'을 못박았으며, 개발 일지(`development_log.md`)를 통해 컨텍스트 단절 없이 이어 나갈 수 있는 인프라를 조성함.
- **다음 에이전트 인수인계 사항 (Handoff)**:
  - 현재 모든 프로젝트 분석과 스프린트 보드 셋업이 완료되었으며, 실제 코드 작업은 아직 시작되지 않은 최초 단계입니다.
  - 다음 주자는 **`sprint_board.md` -> Sprint 1-A (데이터베이스 설계 및 비동기 연결 수립)**의 세부 태스크 `S1-A1`, `S1-A2`, `S1-A3`을 시작하면 됩니다.

## [2026-06-29] 데이터베이스 스택 전환 (SQLite ➔ PostgreSQL) - Antigravity

- **수행 태스크**:
  - [x] 데이터베이스 요구사항 전환에 따른 스택 재검토 및 문서 업데이트
- **주요 구현 내용**:
  - `requirements.txt`에 PostgreSQL 비동기 드라이버 `asyncpg` 및 `pgvector` 라이브러리 추가
  - `design_docs/tech_stack.md` 내 데이터베이스 및 최적화 사양을 SQLite WAL에서 PostgreSQL connection pooling + pgvector 검색으로 변경
  - `design_docs/supplementary_design_specs.md` 내의 2.1 DB 비동기 커넥션 스펙 및 3.1 RAG 검색 로직을 pgvector 확장(CREATE EXTENSION vector) 및 하이브리드 검색 코드로 전환 정의
  - `design_docs/sprint_board.md` 의 Sprint 1-A, 3-B, 5-B 태스크를 PostgreSQL 및 pgvector, PostgresSaver 기반으로 전면 재조정
  - `docker-compose.yml` 템플릿 파일 생성 (pgvector 탑재 PostgreSQL 도커 이미지 연동)
- **기술적 결정 및 특이사항**:
  - 로컬/원격 PostgreSQL을 범용적으로 활용하되, 에이전트 RAG를 단일 DB에서 깔끔하게 통합 처리하기 위해 `pgvector` 기반 하이브리드 검색(1차 키워드 매칭 + 2차 코사인 유사도 검색)을 표준 구조로 채택함.
  - 로컬 개발 환경의 일관성과 pgvector 플러그인의 설치 번거로움을 해결하기 위해 `docker-compose`를 통한 로컬 인프라 자동화(ankane/pgvector 이미지 활용)를 기본 개발 표준으로 설정함.
- **다음 에이전트 인수인계 사항 (Handoff)**:
  - 데이터베이스 스택 교체 및 로컬 개발용 Docker Compose 구성이 완전히 끝났습니다.
  - 다음 주자는 **`sprint_board.md` -> Sprint 1-A (데이터베이스 설계 및 비동기 연결 수립)** 태스크를 수행하면 되며, 프로젝트 루트에서 `docker compose up -d` 명령어로 DB를 구동한 뒤 다음 태스크(S1-A2 SQLModel 스키마 정의)를 개시하면 됩니다.

## [2026-06-29] Sprint 1-A 완료 및 검증 성공 - Antigravity

- **수행 태스크**:
  - [x] **S1-A1**: Docker Compose 기반 pgvector 탑재 PostgreSQL 로컬 띄우기
  - [x] **S1-A2**: SQLModel 기반 데이터 스키마 정의 (`app/models.py`)
  - [x] **S1-A3**: asyncpg 비동기 엔진 구성 및 데이터베이스 연결 시 `vector` 확장 활성화 설정 구현 (`app/core/database.py`)
  - [x] **S1-A4**: PostgreSQL 테이블 마이그레이션/생성 및 임베딩 적재 테스트 (`tests/test_phase1.py`)
- **주요 구현 내용**:
  - `docker compose up -d` 구동 완료 (로컬 5432 포트에 PostgreSQL 띄움).
  - `app/models.py`에 User, Project, WorldSetting, Character, Episode, Content 엔티티 스키마 구현 완료 (Content parent_id 트리 구조 및 WorldSetting pgvector Column(Vector(1536)) 탑재).
  - `app/core/database.py`에 비동기 엔진, 세션 팩토리(`get_async_session`), DB 생성 헬퍼(`init_db()`) 구현 완료 (DB 접속 시 `vector` 확장 활성화 강제).
  - `tests/test_phase1.py` 비동기 테스트 실행 성공. E2E 데이터 삽입/삭제 및 pgvector 코사인 거리 유사도 쿼리 동작성 입증 완료.
- **기술적 결정 및 특이사항**:
  - 데이터 삭제 시 자식 Content가 부모 Content를 외래키로 참조하는 제약 조건 때문에 일시적으로 `ForeignKeyViolationError`가 있었으나, 테스트 코드 상에서 자식 인스턴스를 먼저 삭제하고 커밋한 뒤 부모 인스턴스를 지우는 순서로 변경하여 해결함.
  - 테스트 실패 잔류 데이터로 인한 `UniqueViolationError` 방지를 위해 임시 테스트 유저 생성 시 타임스탬프를 섞은 고유 사용자명을 사용하도록 로직을 강화함.
- **다음 에이전트 인수인계 사항 (Handoff)**:
  - **Sprint 1-A가 완벽히 검증 완료**되었습니다.
  - 다음은 **Sprint 1-B: FastAPI 기본 골격 구성** 단계입니다.
  - `app/core`, `app/models`, `app/routers`, `app/services` 패키지 디렉토리를 이니셜라이징하고, `.env` 로딩 및 헬스 체크 API를 구현하십시오.

## [2026-06-29] Sprint 1-B 완료 및 API 헬스체크 검증 성공 - Antigravity

- **수행 태스크**:
  - [x] **S1-B1**: FastAPI 디렉토리 패키지 구조 초기화
  - [x] **S1-B2**: Pydantic Settings 기반 환경 변수 (`config.py`) 로드 로직 구현
  - [x] **S1-B3**: 비동기 세션 의존성 주입 구성 및 DB 헬스체크 API (`/health`) 검증
- **주요 구현 내용**:
  - `app/core/config.py` 작성 및 환경 변수 타입 안전 바인딩 완료.
  - `app/main.py` 작성 (FastAPI 인스턴스 생성, lifespan을 통한 DB 연결/정리 연동, `/health` 헬스체크 라우터 구현).
  - `tests/test_health.py` 작성 및 `pytest` 비동기 테스트 실행 성공 (`PASSED` 확인).
- **기술적 결정 및 특이사항**:
  - `.agents/AGENTS.md`에 정의한 하드코딩 금지 및 Pydantic Settings 연동 규칙을 철저히 따라, DB 설정 파일에서 `os.getenv` 대신 `settings.DATABASE_URL`을 주입받아 사용하도록 데이터베이스 연동 구조를 개선함.
- **다음 에이전트 인수인계 사항 (Handoff)**:
  - **Sprint 1-B가 성공적으로 완료**되었습니다.
  - 다음은 **Sprint 1-C: JWT 인증 시스템 & 보안 미들웨어** 단계입니다.
  - 비밀번호 해싱(`passlib`), JWT 토큰 생성/검증(`pyjwt`), 회원가입`/auth/register`, 로그인`/auth/login` 엔드포인트 및 API 접근 제어용 `get_current_user` 의존성을 구현하십시오.

## [2026-06-29] Sprint 1-C 완료 및 전체 사용자 인증 검증 성공 - Antigravity

- **수행 태스크**:
  - [x] **S1-C1**: Passlib(Bcrypt) 암호화 유틸리티 구현 (Bcrypt 직접 래핑으로 전환)
  - [x] **S1-C2**: PyJWT 기반 토큰 발급 및 검증 로직 구현
  - [x] **S1-C3**: `/auth/register`, `/auth/login` 엔드포인트 및 스키마 구현
  - [x] **S1-C4**: API 접근 권한 제어를 위한 `get_current_user` 의존성 주입 구현
  - [x] **S1-C5**: Sprint 1 통합 테스트 코드 작성 및 검증 (`tests/test_auth.py`)
- **주요 구현 내용**:
  - `app/core/security.py`에 bcrypt를 직접 사용한 해싱 및 JWT 생성/해독 함수 구축.
  - `app/core/dependencies.py`에 OAuth2PasswordBearer 규격을 탑재하여 사용자를 식별하는 `get_current_user` 완성.
  - `app/schemas/auth.py`에 회원가입 인풋(`UserRegister`) 및 아웃풋 스키마(`UserResponse`) 설계.
  - `app/routers/auth.py`에 중복 검사 로직이 포함된 가입/로그인 API 완성.
  - `tests/test_auth.py` E2E 테스트 성공 (가입 ➔ 로그인 ➔ 토큰 획득 ➔ 보안 API `/users/me` 성공 ➔ cleanup DB 완료).
- **기술적 결정 및 특이사항**:
  - **버그 해결**: `passlib`이 최신 `bcrypt` v4+ 과 충돌하여 72바이트 비밀번호 테스트 단계에서 `ValueError`를 터뜨리는 현상을 발견하고, 레거시 `passlib`을 전면 걷어낸 뒤 `bcrypt` 라이브러리를 직접 핸들링하는 네이티브 래퍼로 교체하여 문제를 원천 해결함.
- **다음 에이전트 인수인계 사항 (Handoff)**:
  - **Sprint 1의 모든 마이크로 태스크가 완료(🎉 Done)**되었습니다.
  - 다음 주자는 **Sprint 2: 프로젝트 & 설정 데이터 관리 (Sprint 2-A)** 단계입니다.
  - 소설 프로젝트 생성/조회/수정/삭제 CRUD API를 개발하고, `/projects` 엔드포인트 접근 시 해당 프로젝트가 현재 로그인한 사용자(`get_current_user`) 소유인지 교차 검증하는 인가 가드 로직을 작성하십시오.

## [2026-06-29] 다중 LLM 제공자(OpenAI/Gemini/Claude/Ollama) 연동 설계 및 DB 갱신 - Antigravity

- **수행 태스크**:
  - [x] 사용자의 요구사항에 맞춘 유연한 AI 공급자 연동 인터페이스 설계
  - [x] DB 스키마 갱신 및 데이터 무결성 검증 E2E 테스트 재수행 (`tests/test_phase1.py`, `tests/test_auth.py`)
- **주요 구현 내용**:
  - `app/models.py` 내 `Project` 테이블에 `llm_provider`, `llm_model`, `api_key_override` 3가지 설정을 가질 수 있는 필드를 추가함.
  - `design_docs/supplementary_design_specs.md` 하단에 **"5. 다중 LLM 제공자 연동 설계"**를 구성하고, LangChain 기반 챗 모델을 주입해 주는 `LLMFactory` 구조 및 API 키 오버라이드 룰을 정의함.
  - `requirements.txt`에 `langchain-google-genai` 및 `langchain-anthropic` 추가 및 가상환경 설치 완료.
  - `tests/test_phase1.py`에 테이블 재생성 강제화(`drop_all` ➔ `create_all`) 로직을 추가하여 마이그레이션이 온전히 수행되도록 개선하고 신규 필드 CRUD 검증 성공.
- **기술적 결정 및 특이사항**:
  - SQLModel의 `create_all()`이 기존 테이블이 있으면 컬럼 확장을 생략하므로, DB 테이블을 완전 드롭 후 재생성하는 코드를 테스트 시작점에 반영하여 마이그레이션을 강제하였고, 이 과정에서 모든 검증(임베딩 유사도 검색 포함)과 JWT 가입/로그인 테스트가 모두 100% 정상 작동(`PASSED`)함을 교차 증명함.
- **다음 에이전트 인수인계 사항 (Handoff)**:
  - 다중 LLM 유연화 설계 및 스키마 반영, 검증까지 모두 끝난 완결 상태입니다.
  - 다음 주자는 **Sprint 2-A: 프로젝트 CRUD API 및 유저 권한 제어 가드**를 이어서 작성하십시오.

## [2026-06-29] Sprint 2-A 완료 및 소유권 인가 가드 검증 성공 - Antigravity

- **수행 태스크**:
  - [x] **Sprint 2-A**: 소설 프로젝트 CRUD API 개발 (소유권 검증 포함) 및 단위 테스트 (`tests/test_project.py`)
- **주요 구현 내용**:
  - `app/schemas/project.py`에 소설 프로젝트 정보 수신(`ProjectCreate`, `ProjectUpdate`) 및 리스폰스(`ProjectResponse`) 스키마 완성.
  - `app/routers/project.py`에 프로젝트 CRUD 엔드포인트 구현 완료.
  - 로그인한 사용자(`get_current_user`) 본인 소유의 프로젝트인지 교차 검증하는 인가(Authorization) 가드 적용.
  - `tests/test_project.py` E2E 테스트 성공 (가입 ➔ 로그인 ➔ 프로젝트 생성 ➔ 조회 ➔ 수정 ➔ 타인의 토큰으로 다른 사람의 프로젝트 ID 조회 시 403 Forbidden 차단 검증 ➔ 삭제 ➔ 404 Not Found ➔ cleanup 완료).
- **기술적 결정 및 특이사항**:
  - **보안 강화**: 사용자가 지정한 프로젝트별 개인 API 키(`api_key_override`) 정보가 외부 API 응답을 통해 노출되는 보안 취약점을 예방하기 위해, `ProjectResponse` 반환 시 원본 텍스트를 제거하고 단순 등록 여부(`has_api_key: bool`)만 전달되도록 응답 형식을 철저히 제한함.
- **다음 에이전트 인수인계 사항 (Handoff)**:
  - **Sprint 2-A가 성공적으로 완료(🎉 Done)**되었습니다.
  - 다음은 **Sprint 2-B: 설정집(Lorebook) 및 캐릭터 CRUD API 개발** 단계입니다.
  - 설정집(`WorldSetting`) 및 캐릭터(`Character`) CRUD API를 개발하고, 설정집 및 캐릭터가 속한 `Project`가 현재 로그인한 사용자 소유가 맞는지 검증하는 교차 프로젝트 소유권 가드를 구현하십시오.

