# 기술 스택 및 배포 아키텍처 (Tech Stack & Deployment)

## 1. 개요
본 문서는 AI 소설 집필 에이전틱 머신을 구현하기 위한 기술 스택을 정의하며, 특히 갤럭시 Z 폴드 4 (Termux) 환경의 리소스 제약과 서버 안정성을 최우선으로 고려하여 설계되었다.

## 2. 개발 단계 기술 스택 (Development Stack)
개발 단계에서는 빠른 반복(Iteration)과 기능 검증에 집중한다.

- **Language**: Python 3.11+
- **API Framework**: FastAPI (Async 기반)
- **Database**: PostgreSQL (with pgvector extension)
- **ORM**: SQLModel (Pydantic + SQLAlchemy 결합)
- **Database Driver**: asyncpg (Async PostgreSQL client)
- **Infrastructure (Local)**: Docker & Docker Compose (for DB running)
- **Authentication**: PyJWT + Passlib (Bcrypt)
- **UI**: Vite + Vanilla JS (SPA) (Streamlit 대체 완료)
- **Server**: Uvicorn (Single worker)

## 3. 최종 배포 아키텍처 (Production Architecture)
모바일 홈 서버에 올릴 때 적용될 최종 구성이며, 개발 시 이 구조를 염두에 두고 코딩한다.

### 3.1 네트워크 및 보안 계층 (Traffic Flow)
`User` $\rightarrow$ `Cloudflare Tunnel` $\rightarrow$ `Nginx (Reverse Proxy)` $\rightarrow$ `Uvicorn` $\rightarrow$ `FastAPI App (API + Static Serving)`

- **Cloudflare Tunnel**: 외부망에서 홈 서버로의 안전한 진입점 제공 및 HTTPS 자동 적용.
- **Nginx**: 
    - 포트 80/443 $\rightarrow$ 8000(FastAPI) 포워딩.
    - 비정상 요청 필터링 및 보안 헤더 적용.
- **FastAPI 정적 서빙**:
    - SPA 빌드 산출물(`frontend/dist/`)을 FastAPI가 직접 내부적으로 `/assets`에 마운트하여 서빙.
    - 별도 Node.js/Streamlit UI 서버 구동 부담이 완전히 해소되어 갤럭시 Z 폴드 4 메모리 오버헤드 극소화.

### 3.2 프로세스 및 리소스 관리
- **Process Manager**: PM2
    - 앱 크래시 시 자동 재시작.
    - `pm2 start`를 통한 백그라운드 상시 구동.
    - 로그 파일의 주기적 순환(Rotation)으로 저장 공간 낭비 방지.
- **DB Optimization**: 
    - Connection Pooling: asyncpg의 기본 비동기 커넥션 풀을 활용하여 데이터베이스 오버헤드 최소화.
    - pgvector 확장 기능 활용: 설정집 RAG 유사도 검색을 별도 데몬 추가 없이 DB 내부 연산으로 처리하여 Termux 리소스 최적화.
    - 정기적 `pg_dump` 백업 스크립트 운용.

## 4. 개발 가이드라인 (Dev-to-Prod Alignment)
최종 환경과의 괴리를 줄이기 위해 개발 단계부터 다음 원칙을 준수한다.

1. **Stateless Auth**: 세션을 서버 메모리에 저장하지 않고 JWT 토큰 기반으로 설계하여, 서버 재시작 시에도 인증이 유지되도록 함.
2. **Async Everything**: LLM API 호출 등 I/O 바운드 작업은 반드시 `async/await`를 사용하여 Termux의 제한된 CPU 리소스 내에서 처리량을 극대화함.
3. **File-based Config**: 환경 설정(API Key, DB 연결 URI 등)은 `.env` 파일을 통해 관리하여 배포 환경에 따라 유연하게 변경 가능하도록 함.
4. **Lightweight UI**: UI 프레임워크 선택 시 서버 사이드 렌더링 부하를 최소화하고, 가능한 클라이언트 사이드에서 처리하도록 설계.