# AI 소설 집필 에이전틱 머신: 프로젝트 구상 및 제안

## 1. 프로젝트 개요
- **목표**: AI API를 활용하여 완전 자동화된 에이전틱 소설 집필 머신 구축
- **핵심 가치**: 사용자의 최소 입력으로 고품질의 소설을 생성하는 자동화 워크플로우 구현
- **최종 형태**: 웹 인터페이스를 통해 접근 가능한 서비스

## 2. 기술 스택 제안
### 2.1 언어 및 환경
- **Language**: Python 3.10+
- **Runtime Environment**: Termux (Galaxy Z Fold 4)
- **Rationale**: AI 생태계의 표준 언어이며, Termux 리눅스 환경에서 안정적인 구동 가능

### 2.2 백엔드 및 프레임워크
- **API Framework**: FastAPI
    - 비동기 처리(`asyncio`)를 통해 LLM의 긴 생성 시간을 효율적으로 관리
- **Agent Framework**: LangGraph (추천)
    - 소설 집필의 특성상 [계획 $\rightarrow$ 집필 $\rightarrow$ 피드백 $\rightarrow$ 수정]의 순환 구조(Cyclic Graph)가 필요하므로, 상태 관리가 정밀한 LangGraph가 최적임
- **Memory/State**: SQLite 또는 Vector DB (ChromaDB/FAISS)
    - 소설의 설정, 캐릭터 시트, 이전 챕터 내용을 기억하기 위한 컨텍스트 관리

### 2.3 유저 인터페이스 (UI)
- **Frontend**: Streamlit (초기 검증용) $\rightarrow$ React/Next.js (최종 확장용)
- **Communication**: REST API / WebSocket (실시간 집필 진행 상황 중계)

## 3. 핵심 요구사항 및 기능 설계

### 3.1 사용자 인증 및 권한 관리
- **목적**: 개인화된 프로젝트 관리 및 무분별한 토큰 사용 방지
- **기능**:
    - JWT(JSON Web Token) 기반의 인증 시스템
    - **관리자 승인 기반 회원가입**: 악의적인 봇 가입이나 무분별한 리소스 사용을 막기 위해, 회원가입 시 관리자에게 이메일로 승인 요청이 발송되며, 관리자가 승인(활성화)해야만 서비스 로그인이 가능하도록 설계.
    - 사용자별 작업 공간 격리 (본인이 생성한 프로젝트만 접근 가능)
    - 심플한 계정 생성 및 로그인 기능

### 3.2 프로젝트 중심의 체계적 데이터 관리 (DB)
- **목적**: 소설의 설정, 회차, 텍스트 등 모든 데이터를 구조적으로 보관하고 추적
- **저장소**: SQLite (Termux 환경 최적화 및 이식성 확보)
- **데이터 모델링 구조**:
    - `User` $\rightarrow$ `Project` (1:N)
    - `Project` $\rightarrow$ `WorldSettings`, `Characters` (1:N)
    - `Project` $\rightarrow$ `Episodes/Chapters` (1:N)
    - `Episode` $\rightarrow$ `Contents/Versions` (1:N)
- **관리 범위**: 단순 텍스트 저장을 넘어 설정집(Lorebook)과 집필 이력을 체계적으로 관리

## 4. 배포 및 운영 전략 (Termux 기반)
- **서버**: 갤럭시 Z 폴드 4 (Termux)
- **프로세스 관리**: PM2 등을 활용하여 백그라운드 상시 운용
- **외부 접속**: 필요 시 Cloudflare Tunnel 또는 Tailscale을 통해 외부 웹 접근 허용

## 5. 향후 마일스톤
- [ ] Phase 1: MVP 범위 정의 및 기본 아키텍처 설계
- [ ] Phase 2: 핵심 에이전트(Plotter, Writer) 기초 구현 및 API 연동
- [ ] Phase 3: 에이전트 간 피드백 루프(Self-Correction) 구현
- [ ] Phase 4: 웹 UI 통합 및 Termux 최적화 배포
