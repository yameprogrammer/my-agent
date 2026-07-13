# 프론트엔드 재구현 검토 보고서 (Frontend Rebuild Review)

> **작성일**: 2026-07-13  
> **목적**: 현재 Streamlit 기반 프론트엔드의 한계를 진단하고, Vite + Vanilla JS SPA로의 재구현 타당성을 검토한다.

---

## 1. 현재 프론트엔드 진단

### 1.1 현재 기술 구성

| 항목 | 현재 상태 | 비고 |
| :--- | :--- | :--- |
| **프레임워크** | Streamlit (Python) | 데이터 분석/ML 프로토타이핑용 |
| **API 통신** | `requests` (동기 블로킹) | UI 스레드 차단 |
| **WebSocket** | `websocket-client` (동기 블로킹 recv 루프) | 메인 스레드 차단 |
| **상태 관리** | `st.session_state` (서버 사이드) | 클라이언트 사이드 상태 관리 불가 |
| **스타일링** | Streamlit 기본 테마 | 커스터마이징 극히 제한 |
| **파일 구성** | `ui/app.py`, `ui/api_client.py`, `ui/project_view.py`, `ui/monitor_view.py` | 총 4개 Python 파일 |

### 1.2 현재 UI 기능 목록

| 파일 | 기능 |
| :--- | :--- |
| `app.py` (132줄) | 로그인/회원가입, 프로젝트 목록/생성, 네비게이션 라우팅 |
| `api_client.py` (106줄) | `requests` 기반 REST API 클라이언트 (JWT 토큰 관리) |
| `project_view.py` (410줄) | 5개 탭: AI 기획 파트너, 세계관, 캐릭터 시트, 회차 관리, 프로젝트 설정(per-agent LLM) |
| `monitor_view.py` (238줄) | WebSocket 실시간 집필 모니터, HITL 피드백/승인, AI 평가 리포트 표시 |

### 1.3 핵심 병목 원인

Streamlit의 **전체 재실행(rerun) 모델**이 근본 원인이다:

1. **모든 인터랙션마다 전체 Python 스크립트가 재실행**됨 → 극심한 지연
2. **`requests` 동기 HTTP 호출**이 UI 스레드를 블로킹 → 반응성 저하
3. **`websocket-client` 동기 recv 루프**가 메인 스레드를 블로킹 → 집필 모니터 응답 지연
4. **서버 사이드 렌더링** → 모든 UI 변경이 서버 왕복(round-trip) 필요
5. **스타일 커스터마이징 한계** → 프로덕션 수준의 UI/UX 구현 불가

> ⚠️ **결론**: Streamlit의 근본적 아키텍처 한계로 인해 **패치나 최적화로는 해결 불가능**하며, 프론트엔드 전체 재구현만이 유일한 해결책이다.

---

## 2. 백엔드 API 현황 분석 (재사용 대상)

백엔드는 **FastAPI + PostgreSQL(pgvector) + LangGraph** 기반으로 완성도 높게 구현되어 있으며, 프론트엔드 교체 시 **변경 없이 그대로 재사용** 가능하다.

### 2.1 인증 체계

| 엔드포인트 | 메서드 | 기능 |
| :--- | :--- | :--- |
| `/auth/register` | POST | 회원가입 (관리자 Telegram 승인 필요) |
| `/auth/login` | POST | JWT 토큰 발급 (`OAuth2PasswordRequestForm`) |
| `/auth/me` | GET | 현재 사용자 정보 |
| `/auth/telegram/webhook` | POST | Telegram 봇 콜백 (승인/거부) |
| `/users/me` | GET | 인증된 사용자 정보 |

### 2.2 리소스 CRUD API

| 리소스 | 경로 패턴 | 지원 메서드 |
| :--- | :--- | :--- |
| **Projects** | `/projects`, `/projects/{id}` | POST, GET, PUT, DELETE |
| **World Settings** | `/projects/{id}/world-settings` | POST, GET(list), GET(single), PUT, DELETE |
| **Characters** | `/projects/{id}/characters` | POST, GET(list), GET(single), PUT, DELETE |
| **Episodes** | `/projects/{id}/episodes` | POST, GET(list), GET(single), PUT, DELETE |
| **Contents** | `/projects/{id}/episodes/{id}/contents` | POST, GET(list), GET(single) |
| **Contents 승인** | `.../contents/{id}/approve` | PUT |

### 2.3 AI 기능 API

| 엔드포인트 | 메서드 | 기능 |
| :--- | :--- | :--- |
| `/projects/{id}/brainstorm` | POST | AI 브레인스토밍 (세계관+캐릭터 제안 생성) |
| `/projects/{id}/brainstorm/apply` | POST | 브레인스토밍 결과 일괄 저장 (upsert) |
| `/health` | GET | DB 연결 포함 헬스체크 |

### 2.4 WebSocket 실시간 집필

- **경로**: `ws://{host}/ws/projects/{project_id}/episodes/{episode_id}/write`
- **인증**: 첫 메시지로 `{action: "auth", token: "JWT"}` 전송
- **클라이언트 → 서버 액션**: `start_writing`, `submit_feedback`, `approve`
- **서버 → 클라이언트 이벤트**: `current_state`, `status_changed`, `text_stream`, `requires_user_review`, `error`

### 2.5 AI 에이전트 워크플로우 (LangGraph)

5개 에이전트가 LangGraph 상태 머신으로 순환 동작:

| 에이전트 | 역할 |
| :--- | :--- |
| **Plotter** | 에피소드를 3~5개 씬으로 기획 (tension/pace 점수 포함) |
| **Writer** | 개별 씬 산문 집필 (스트리밍 지원) |
| **Judge** | 세계관 일관성 검증 (통과/실패 + 비평) |
| **Editor** | 피드백 기반 교정 (스트리밍 지원) |
| **Reviewer** | 종합 평가 (100점 만점 + 가독성/긴장감/강점/약점/제안) |

워크플로우 흐름: `Plotter → RAG → Writer → Judge → (통과: 다음 씬 또는 Reviewer) / (실패: Editor 재시도) → User Review (HITL) → Save`

### 2.6 재사용 판정

| 항목 | 상태 |
| :--- | :--- |
| CORS 설정 | ✅ `["*"]` — 별도 프론트엔드 서버에서 접근 가능 |
| JWT 인증 | ✅ Bearer 토큰 기반 — 클라이언트 독립 |
| WebSocket | ✅ 프로토콜 정의 완비 — 네이티브 WebSocket 연결 가능 |
| 응답 스키마 | ✅ Pydantic v2 기반 JSON — 어떤 프론트엔드에서든 소비 가능 |

---

## 3. 기술 스택 비교 및 선정

### 3.1 후보 기술 비교

| 고려사항 | Vite + Vanilla JS | React SPA | Vue SPA | Next.js |
| :--- | :--- | :--- | :--- | :--- |
| **프로덕션 번들 크기** | ~50KB (최소) | ~150KB+ | ~120KB+ | ~200KB+ |
| **Termux 빌드 호환성** | ✅ 정적 파일 산출 | ⚠️ Node.js 런타임 필요 | ⚠️ Node.js 런타임 필요 | ❌ SSR 서버 필요 |
| **반응 속도** | ✅ 네이티브 DOM | ✅ Virtual DOM | ✅ Virtual DOM | ✅ 빠름 |
| **메모리 사용** | ✅ 최소 | ⚠️ 런타임 오버헤드 | ⚠️ 런타임 오버헤드 | ❌ 과다 |
| **빌드 후 서빙** | ✅ FastAPI static 통합 | ✅ 동일 | ✅ 동일 | ❌ 별도 Node 서버 |
| **외부 의존성** | ✅ 없음 (순수 JS) | ⚠️ react, react-dom | ⚠️ vue | ❌ next, react |
| **학습 곡선** | ✅ 낮음 | ⚠️ 중간 | ⚠️ 중간 | ⚠️ 높음 |
| **Galaxy Z Fold 4 적합성** | ✅ 최적 | ⚠️ 보통 | ⚠️ 보통 | ❌ 부적합 |

### 3.2 선정: **Vite + Vanilla JS (SPA)**

**선정 사유**:
1. **Termux 환경 최적화**: 빌드 산출물이 순수 정적 파일(HTML/CSS/JS)이므로 FastAPI의 `StaticFiles` 미들웨어로 서빙 가능. 별도 Node.js 런타임이나 프론트엔드 서버 불필요.
2. **번들 크기 최소화**: 프레임워크 런타임 오버헤드 없이 ~50KB 수준의 경량 번들 생성.
3. **메모리 효율**: Galaxy Z Fold 4의 제한된 RAM(6~8GB)에서 백엔드(FastAPI + PostgreSQL + LangGraph)와 공존 가능.
4. **기존 tech_stack.md의 가이드라인 준수**: "Lightweight UI" 및 "클라이언트 사이드 처리" 원칙에 부합.

---

## 4. 기능 매핑 (현재 Streamlit → 신규 SPA)

### 4.1 페이지 구조

| 페이지 | 경로 (Hash) | 대응 API |
| :--- | :--- | :--- |
| 로그인/회원가입 | `#/login` | `/auth/login`, `/auth/register` |
| 대시보드 (프로젝트 목록) | `#/` | `GET /projects`, `POST /projects` |
| 프로젝트 상세 | `#/projects/:id` | `GET /projects/:id` |
| ├ AI 기획 파트너 | `#/projects/:id/brainstorm` | `POST /brainstorm`, `POST /brainstorm/apply` |
| ├ 세계관 (Lorebook) | `#/projects/:id/world` | CRUD `/world-settings` |
| ├ 캐릭터 시트 | `#/projects/:id/characters` | CRUD `/characters` |
| ├ 회차 관리 | `#/projects/:id/episodes` | CRUD `/episodes`, `/contents` |
| ├ 프로젝트 설정 | `#/projects/:id/settings` | `PUT /projects/:id` |
| └ 집필 모니터 | `#/projects/:id/episodes/:eid/write` | `WS /ws/.../write` |

### 4.2 기능별 개선 사항

| 현재 (Streamlit) | 신규 (SPA) | 개선 효과 |
| :--- | :--- | :--- |
| `st.text_input` 로그인 | 모던 폼 + JWT localStorage 관리 | 자동 로그인, 새로고침 시 세션 유지 |
| `st.columns` 프로젝트 목록 | 카드 그리드 + 모달 생성 | 시각적 대시보드, 빠른 전환 |
| `st.selectbox` LLM 프로바이더 | 커스텀 드롭다운 + 프리셋 버튼 | 직관적 구성 |
| `st.form` AI 브레인스토밍 | 인터랙티브 제안 패널 + 체크박스 | 즉각적 피드백, 일괄 저장 |
| `st.expander` 세계관 | 카테고리 탭 + 인라인 편집 | 빠른 탐색, 컨텍스트 유지 |
| `st.columns` 캐릭터 | 캐릭터 카드 + 중요도 뱃지 | 시각적 계층 표현 |
| 동기 WebSocket recv 루프 | **네이티브 WebSocket** 이벤트 기반 | 논블로킹, 즉시 반영 |
| `st.tabs` 평가 리포트 | 스코어카드 + 게이지 차트 | 시각적 평가 표현 |
| `st.text_area` HITL 피드백 | 드래프트 나란히 비교 + 리치 피드백 | 원문 참조하며 피드백 작성 |
| `st.selectbox` per-agent LLM | 에이전트별 설정 카드 | 한눈에 전체 구성 파악 |

---

## 5. 신규 프론트엔드 프로젝트 구조

```
frontend/                       # 새 프론트엔드 디렉토리 (기존 ui/ 보존)
├── index.html                 # SPA 진입점
├── package.json               # Vite 의존성
├── vite.config.js             # Vite 설정 (개발 시 API 프록시 포함)
├── public/
│   └── favicon.svg
└── src/
    ├── main.js                # 앱 초기화 + SPA 라우터
    ├── style.css              # 디자인 시스템 (CSS 변수, 다크모드, 반응형)
    │
    ├── api/
    │   ├── client.js          # fetch 기반 REST API 클라이언트 (JWT 자동 첨부)
    │   └── websocket.js       # WebSocket 매니저 (자동 재연결, 이벤트 핸들링)
    │
    ├── components/
    │   ├── sidebar.js         # 사이드바 네비게이션
    │   ├── modal.js           # 범용 모달 다이얼로그
    │   ├── toast.js           # 알림 토스트
    │   ├── loading.js         # 스켈레톤 로더
    │   ├── scorecard.js       # 평가 스코어 표시
    │   └── streaming-text.js  # 스트리밍 텍스트 렌더러
    │
    ├── pages/
    │   ├── login.js           # 로그인 / 회원가입
    │   ├── dashboard.js       # 프로젝트 대시보드
    │   ├── project.js         # 프로젝트 상세 (탭 컨테이너)
    │   ├── brainstorm.js      # AI 기획 파트너
    │   ├── worldmap.js        # 세계관 설정
    │   ├── characters.js      # 캐릭터 시트
    │   ├── episodes.js        # 에피소드 / 회차 관리
    │   ├── settings.js        # 프로젝트 설정 (per-agent LLM)
    │   └── writing-monitor.js # 실시간 집필 모니터 (WebSocket + HITL)
    │
    └── utils/
        ├── router.js          # Hash-based SPA 라우터
        ├── state.js           # 클라이언트 상태 관리
        └── auth.js            # JWT 토큰 관리 (저장, 만료 체크, 자동 첨부)
```

---

## 6. 기술 개선 비교 요약

| 영역 | Streamlit (현재) | Vite SPA (신규) |
| :--- | :--- | :--- |
| **렌더링** | 전체 Python 스크립트 재실행 | DOM 부분 업데이트 (변경 부분만) |
| **API 호출** | `requests` 동기 블로킹 | `fetch()` 비동기 (`async/await`) |
| **WebSocket** | `websocket-client` 동기 블로킹 | 네이티브 `WebSocket` API (이벤트 기반) |
| **상태 관리** | `st.session_state` (서버 사이드) | 클라이언트 사이드 (`localStorage` + 메모리) |
| **인증** | 세션 기반 토큰 저장 | JWT `localStorage` + 자동 첨부 (Authorization 헤더) |
| **스트리밍** | 블로킹 recv 루프 | `onmessage` 이벤트 핸들러 |
| **스타일링** | Streamlit 기본 테마 (변경 불가) | CSS 변수 + 다크모드 + 마이크로 애니메이션 |
| **반응형 디자인** | 없음 | 모바일/태블릿/데스크톱 미디어 쿼리 |
| **배포** | 별도 Streamlit 서버 필요 (`streamlit run`) | `npm run build` → FastAPI `StaticFiles` 서빙 |

---

## 7. 최종 판정

| 판단 기준 | 결과 |
| :--- | :--- |
| 백엔드 API 완성도 | ✅ 인증, CRUD(20+), 브레인스토밍, WebSocket 모두 완비 |
| API 분리도 | ✅ RESTful + CORS + JWT — 프론트엔드 독립 교체 가능 |
| 현재 UI 개선 가능성 | ❌ Streamlit 전체 재실행 모델의 근본 한계 |
| 백엔드 변경 필요성 | ✅ **없음** — 프론트엔드만 교체 |
| 디바이스 적합성 | ✅ Vite 빌드 산출물은 정적 파일로 Termux 경량 서빙 가능 |

> **결론**: 프론트엔드 재구현은 **가능하며 강력히 권장**한다. 백엔드 코드 변경 없이 `frontend/` 디렉토리에 Vite + Vanilla JS SPA를 새로 구축하고, 안정화 후 기존 `ui/` 디렉토리를 제거하는 방식으로 진행한다.
