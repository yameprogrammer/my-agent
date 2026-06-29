# 단계별 구현 로드맵 (Implementation Roadmap)

## 1. 로드맵 운영 원칙
- **Bottom-Up Approach**: 가장 기초가 되는 데이터 계층부터 구축하여 상위 계층(에이전트, UI)이 안정적인 기반 위에서 작동하도록 함.
- **Iterative Development**: 각 Phase 내에서도 [설계 $\rightarrow$ 구현 $\rightarrow$ 검증]의 짧은 주기를 반복하여 방향성을 상시 확인.
- **Termux First**: 모든 구현 단계에서 모바일 서버의 리소스 제약을 고려하여 최적화된 라이브러리와 비동기 패턴을 적용.

## 2. 상세 구현 단계 (Phases)

### Phase 1: Foundation & Data Layer (기반 및 데이터 계층)
**목표**: 사용자 인증과 프로젝트 데이터를 안전하게 저장하고 관리하는 기본 인프라 구축.

- **Task 1.1: DB 스키마 정밀 설계**
    - `User`, `Project`, `WorldSetting` (Lorebook), `Character`, `Episode`, `Content` 테이블 간의 관계 정의.
    - Git-like 버전 트리를 지원하도록 `Content` 테이블에 `parent_id` 설계 및 계층 관계 정의.
    - SQLModel + SQLAlchemy를 기반으로 `aiosqlite` 비동기 드라이버 및 SQLite WAL(Write-Ahead Logging) 모드 pragma 연동 설계.
    - LangGraph `SqliteSaver`가 사용하는 체크포인트 테이블 영역 구성 계획 반영.
- **Task 1.2: 프로젝트 기본 구조 설정**
    - FastAPI 앱 구조 설정 (Router, Service, Repository 패턴 적용).
    - 비동기 세션(`AsyncSession`) 의존성 주입 주입부 (`get_async_session`) 구성.
    - `.env` 기반 환경 변수 관리 체계 구축.
- **Task 1.3: 사용자 인증 시스템 구현**
    - Password hashing (Bcrypt) 및 JWT 발행/검증 로직 구현.
    - `/auth/login`, `/auth/register` API 엔드포인트 생성.
- **Task 1.4: 기초 DB 연동 및 검증**
    - SQLModel을 이용한 DB 연결 및 마이그레이션 테스트.
    - 유저 생성 및 로그인 흐름 End-to-End 테스트.

### Phase 2: Core Management Logic (핵심 관리 로직)
**목표**: 소설의 뼈대가 되는 프로젝트와 설정값들을 관리하는 CRUD 시스템 구축.

- **Task 2.1: 프로젝트 관리 API 구현**
    - 소설 프로젝트 생성/수정/삭제 및 목록 조회 기능.
- **Task 2.2: 세계관 및 설정 관리 시스템**
    - 세계관 설정(Lorebook) 및 캐릭터 시트 CRUD 구현.
    - 설정값의 버전 관리 또는 스냅샷 기능 검토.
- **Task 2.3: 회차 및 텍스트 관리 구조 구현**
    - 챕터/회차 생성 및 순서 관리 로직.
    - 집필된 텍스트의 저장 및 버전별 이력 관리.
- **Task 2.4: 관리 기능 통합 검증**
    - [프로젝트 생성 $\rightarrow$ 설정 입력 $\rightarrow$ 회차 생성 $\rightarrow$ 내용 저장] 흐름 검증.

### Phase 3: Agentic Writing Engine (에이전틱 집필 엔진)
**목표**: LLM API와 LangGraph를 결합하여 자율적으로 집필하는 에이전트 파이프라인 구축.

- **Task 3.1: 에이전트 페르소나 및 프롬프트 설계**
    - Plotter, Writer, Judge, Editor 각 역할별 시스템 프롬프트 정의.
- **Task 3.2: LangGraph 워크플로우 설계**
    - [플롯 생성 $\rightarrow$ 초안 집필 $\rightarrow$ 설정 검토 $\rightarrow$ 수정 $\rightarrow$ 최종 확정] 순환 그래프 설계.
    - 상태 관리(State) 정의: 현재 집필 단계, 누적된 컨텍스트 등.
- **Task 3.3: AI API 연동 및 최적화**
    - LLM 인터페이스 구현 및 비동기 호출 처리.
    - 토큰 소모 최적화를 위한 컨텍스트 윈도우 관리 전략 적용.
- **Task 3.4: 자율 집필 루프 검증**
    - 단일 챕터에 대한 완전 자동 집필 테스트 및 결과 품질 평가.

### Phase 4: Interface & User Experience (UI 및 경험)
**목표**: 사용자가 편리하게 제어하고 결과를 확인할 수 있는 웹 인터페이스 통합.

- **Task 4.1: Streamlit 기반 관리 패널 구현**
    - 로그인 화면 및 프로젝트 대시보드.
    - 세계관/캐릭터 설정 편집기.
- **Task 4.2: 집필 모니터링 인터페이스**
    - 에이전트의 현재 작업 상태(예: "플롯 설계 중...") 실시간 표시.
    - 생성된 텍스트의 실시간 스트리밍 표시.
- **Task 4.3: 사용자 피드백 루프 구현**
    - AI가 생성한 결과물에 대해 사용자가 수정을 요청하거나 승인하는 인터페이스.
- **Task 4.4: 통합 사용자 시나리오 테스트**
    - 전체 흐름(인증 $\rightarrow$ 설정 $\rightarrow$ 집필 $\rightarrow$ 저장)의 UX/UI 검증.

### Phase 5: Optimization & Deployment (최적화 및 배포)
**목표**: 갤럭시 Z 폴드 4 환경에서 상시 안정적으로 구동되는 프로덕션 상태 완성.

- **Task 5.1: Termux 서버 최적화**
    - PM2 프로세스 관리 설정 (자동 재시작, 로그 로테이션).
    - 메모리 및 CPU 사용량 모니터링 및 튜닝.
- **Task 5.2: 외부 접속 환경 구축**
    - Nginx 리버스 프록시 설정.
    - Cloudflare Tunnel 연동을 통한 HTTPS 보안 접속 적용.
- **Task 5.3: 데이터 백업 및 유지보수 체계**
    - SQLite DB 자동 백업 스크립트 구현.
    - 에러 로그 수집 및 알림 체계 구축.
- **Task 5.4: 최종 스트레스 테스트 및 릴리즈**
    - 장시간 구동 안정성 테스트 후 최종 배포.
