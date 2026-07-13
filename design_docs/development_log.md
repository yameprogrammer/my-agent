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

## [2026-07-13] 모델 선택 드롭다운에 '직접 입력하기' 옵션 추가 - Gemini 3.5 Flash

- **수행 태스크**:
  - [x] **모든 프로바이더 드롭다운 확장**: `openai`, `google`, `anthropic`, `ollama` 및 `custom_openai`를 포함한 모든 제공자 모델 리스트의 마지막 항목에 `custom-model`("✏️ 직접 입력하기...") 옵션 추가 연동
  - [x] **동적 폼 토글 및 모델명 직접 입력 연동 (`dashboard.js`, `settings.js`)**:
    - 드롭다운에서 "✏️ 직접 입력하기..." 선택 시, 하단에 숨겨진 텍스트 인풋 필드(`#new-model-custom` 등)가 즉시 활성화(show)되도록 뷰 인터랙션 바인딩
    - 프로젝트 생성 및 설정 저장 시, 드롭다운이 `custom-model` 상태이면 사용자가 직접 입력한 텍스트를 모델명 파라미터(`llm_model`)로 취합하여 백엔드에 전송
  - [x] **커스텀 모델 설정 복원 로직 구현 (`settings.js`)**:
    - 프로젝트 설정 조회 시, DB에 저장된 모델명이 표준 드롭다운 목록에 없는 커스텀 명칭(예: `gpt-custom-v3`)일 경우, 드롭다운을 자동으로 "✏️ 직접 입력하기..." 상태로 선택하고 인풋 박스를 표시한 뒤 실제 저장된 커스텀 모델명을 복원해 채워주는 자동 복원(Restore) 감시 함수 구현 완료 (기본 모델 설정 및 5대 에이전트 설정 모두 동일 적용)
- **테스트 결과**:
  - `pytest` E2E 통합 테스트 35개 전체 검증 성공 (100% 통과)

## [2026-07-13] 최신 AI 모델 드롭다운 갱신 및 Custom OpenAI 호환 API 구현 - Gemini 3.5 Flash

- **수행 태스크**:
  - [x] **LLM 팩토리 보강 (`llm_factory.py`)**: `custom_openai` 프로바이더 분기를 추가하고, 암호화된 API 키 필드 내에 포함된 `::` 구분자를 파싱하여 `base_url` 인자를 `ChatOpenAI`에 동적으로 전달하도록 백엔드 처리 구현
  - [x] **신규 생성 폼 보강 (`dashboard.js`)**: LLM 프로바이더 목록에 "OpenAI 호환 API (Custom)"를 추가하고, 모델명 직접 입력 필드 및 API Base URL 입력 필드 추가. 생성 시 `API_KEY::BASE_URL` 포맷으로 취합 전송 연동 완료
  - [x] **프로젝트 설정 폼 보강 (`settings.js`)**: 기본 모델 및 5가지 개별 에이전트(Plotter/Writer/Judge/Editor/Reviewer) 설정에 "OpenAI 호환 API (Custom)" 지원 완비. DB 로딩 시 `api_key_override` 내 `::` 포맷을 분리 역해석하여 API Key 마스킹 텍스트와 Base URL 입력 필드에 각각 분리 복원하는 역파싱 로직 추가
  - [x] **드롭다운 모델 데이터 최신화**:
    - **OpenAI**: `gpt-4o-mini`, `gpt-4o`, `o3-mini`, `o1`, `o1-mini`
    - **Google**: `gemini-2.5-flash`, `gemini-2.5-pro`, `gemini-2.0-flash`, `gemini-2.0-pro-exp`
    - **Anthropic**: `claude-3-7-sonnet`, `claude-3-5-sonnet`, `claude-3-5-haiku`
    - **Ollama**: `deepseek-r1:8b`, `deepseek-r1:1.5b`, `llama3.3:70b`, `llama3.2:3b`, `qwen2.5:7b`
- **기술적 결정 및 특이사항**:
  - 데이터베이스 스키마 마이그레이션(Alembic alter table 등) 리스크를 완전히 차단하기 위해, 암호화되는 API Key 필드(`api_key_override`)를 오버로딩하여 `API_KEY::BASE_URL` 형태로 결합 저장하는 최적의 디자인 패턴을 적용했습니다.
  - 이로써 DeepSeek, Qwen 등 임의의 OpenAI 규격 호환 API를 별도 스키마 변경 없이 완벽하게 지원합니다.

## [2026-07-13] Sprint 6-G 프론트엔드 E2E 테스트 및 최적화 마무리 - Gemini 3.5 Flash

- **수행 태스크**:
  - [x] **S6-G1**: E2E 시나리오 통합 작동 검증. DB 볼륨 초기화 후 `pytest` 테스트 슈트 35개 성공 (100% 통과) 검증 완료
  - [x] **S6-G2**: 갤럭시 Z 폴드 4 커스텀 미디어 쿼리(`style.css`)에 따라 904px 이하의 접힌 화면에서의 1열 강제 및 햄버거 오버레이 사이드바 정상 동작 검사
  - [x] **S6-G3**: HSL 테마에 기반한 다크모드/라이트모드 글래스모피즘 오버레이 폰트 가독성 검사 완료
  - [x] **S6-G4**: 페이지 컴포넌트 전환 시 `destroyed` 커스텀 이벤트를 디스패치하여 활성 WebSocket 연결 누수를 방지하는 가드 프로파일링 검증 완료
  - [x] **S6-G5**: `README.md` 및 `tech_stack.md` 가이드에 Vite 프로덕션 빌드, FastAPI 서빙 명령어 및 단일 아키텍처 다이어그램 업데이트 완료
- **주요 구현 내용**:
  - **테스트 무결성**: 로컬 도커 DB 볼륨 리셋 후 DB 스키마 테이블 구조를 완벽 재생성하여, UndefinedColumnError 없이 모든 35개 테스트가 한 번에 통과하는 상태를 확인했습니다.
  - **문서화 마무리**: 빌드 가이드와 단일 서버 아키텍처 변경 내용을 문서화함으로써 차기 인수인계 및 배포 인프라 작업의 명확한 기초를 수립했습니다.
- **Sprint 6 요약**:
  - 이번 스프린트 6를 통해 속도가 매우 느리고 갤럭시 Z 폴드 4 환경에서 심각한 오버헤드를 일으키던 구 Streamlit UI가 **완벽히 가볍고 세련된 Vite + Vanilla JS SPA 웹 프론트엔드**로 교체 완료되었습니다!
  - 8080 단일 포트로 정적 자원 및 백엔드 API, 실시간 집필실 WebSocket이 모두 매끄럽게 호스팅됩니다.

## [2026-07-13] Sprint 6-F 프론트엔드 단일 서버 서빙 통합 구현 - Gemini 3.5 Flash

- **수행 태스크**:
  - [x] **S6-F1**: `npm run build` 결과로 생성되는 `frontend/dist/` 정적 구조 검증
  - [x] **S6-F2**: `app/main.py` 내 `StaticFiles` 미들웨어 마운트 추가 및 `favicon`/`icons` 루트 자원 개별 서빙 추가
  - [x] **S6-F2**: SPA 클라이언트 새로고침 시 경로 손실을 유실 방지하는 catch-all `spa_fallback` 라우터 구현 (API, health 및 WebSockets 통로 보호 정책 완비)
  - [x] **S6-F3**: 프론트엔드 빌드 최적화 분석 및 8080포트 단일 포트 서버 통합 완료
- **주요 구현 내용**:
  - **단일 포트 통합**: 기존에 Streamlit 포트(8501 등)와 FastAPI 포트(8080) 두 군데로 나뉘어 호스팅되던 것을, 프론트엔드 빌드 결과물을 백엔드 정적 디렉토리로 바인딩하여 8080 포트 하나로 모든 UI와 API, WebSockets를 제공하도록 서빙 통합을 완료했습니다.
  - **SPA fallback 라우팅**: FastAPI의 catch-all path parameter(`{fallback_path:path}`)를 사용하여, 사용자가 직접 도메인/경로(예: `/projects/1`)를 쳐서 들어와도 백엔드가 404가 아닌 SPA `index.html`을 반환하게 돕는 Fallback 경로를 마련하되, `auth/`, `projects/` 등 API 전용 prefix는 예외적으로 404를 반환하게 안전 설계했습니다.
- **기술적 결정 및 특이사항**:
  - 로컬 개발 모드에서는 여전히 Vite Dev Server(3000포트)를 기동하여 백엔드(8080)와 프록시 통신을 하고, 프로덕션 배포 시에는 빌드 후 FastAPI 단독 기동으로 운영하도록 설계되었습니다.
- **다음 에이전트 인수인계 사항 (Handoff)**:
  1. 다음 단계는 **Sprint 6-G (통합 테스트 및 배포 검증)**입니다.
  2. 프론트엔드가 실제 백엔드에 통합된 상태에서 E2E 작동 시나리오가 완벽히 동작하는지 확인하고, Galaxy Z Fold 4 기기 해상도에서의 반응형 레이아웃 정상 적용 여부, 그리고 다크모드 가독성을 통합 검사하면 마이그레이션 스프린트가 모두 종료됩니다.

## [2026-07-13] Sprint 6-E 프론트엔드 실시간 집필 모니터 및 HITL 구현 - Gemini 3.5 Flash

- **수행 태스크**:
  - [x] **S6-E1**: 집필 모니터 페이지 레이아웃(`pages/writing-monitor.js`) 2컬럼 화면 구현
  - [x] **S6-E2**: WebSocket 연결 수립 시 로컬 스토리지 access_token을 읽어 자동 `auth` 이벤트 전송
  - [x] **S6-E3**: `text_stream` 청크 실시간 추가 및 타이핑 효과, 하단 자동 스크롤 고정 구현
  - [x] **S6-E4**: `status_changed` 전이에 맞춘 에이전트 순환 타임라인 인디케이터 활성화 구현
  - [x] **S6-E5**: `requires_user_review` 수신 시 AI 가독성/긴장감/종합 스코어카드 및 강약점 분석 카드 맵핑 구현
  - [x] **S6-E6**: 작가 피드백 반영 재작성(`submit_feedback`) 및 원고 최종 승인(`approve`) 요청 버튼 바인딩
  - [x] **S6-E7**: 대기 상태 시 "집필 프로세스 기동"(`start_writing`) 단독 버튼 노출 및 명령 전송 구현
  - [x] **S6-E8**: 뷰 파괴 시 `destroyed` 커스텀 이벤트를 감지하여 WebSocket 연결을 해제하고, 리커넥트 3회 제한 가드 적용
- **주요 구현 내용**:
  - **스트리밍 최적화**: 텍스트 청크 수신 시 즉시 DOM에 반영되도록 최적화했으며, 씬 전환 이벤트 수신 시 드래프트 영역을 리셋하는 마크업 가드를 추가했습니다.
  - **안전한 라이프사이클**: SPA 특성 상 페이지 전환 시 웹소켓 연결이 누수되는 것을 방지하기 위해 라우터(`router.js`)에서 이전 뷰 소멸 시 `destroyed` 이벤트를 알려 연결을 닫게 설계했습니다.
- **기술적 결정 및 특이사항**:
  - 소켓 재연결이 3회 초과 실패 시에는 토스트 메시지로 "서버 연결 실패"를 인지시키고 집필실 수동 재진입을 유도하도록 UX를 배려했습니다.
- **다음 에이전트 인수인계 사항 (Handoff)**:
  1. 다음 단계는 **Sprint 6-F (FastAPI 정적 서빙 통합)**입니다.
  2. `frontend` 디렉토리 빌드 결과물(`dist/`)을 FastAPI `app/main.py`에 `StaticFiles` 미들웨어로 서빙하도록 경로 마운트를 추가해 단일 서버 통합을 완료해야 합니다.

## [2026-07-13] Sprint 6-D 프론트엔드 프로젝트 상세 탭 및 CRUD 구현 - Gemini 3.5 Flash

- **수행 태스크**:
  - [x] **S6-D1**: 프로젝트 상세 컨테이너(`pages/project.js`) 및 5개 탭(기획/세계관/캐릭터/회차/설정) 전환 셸 구현
  - [x] **S6-D2**: AI 기획 파트너(`pages/brainstorm.js`) 브레인스토밍 suggestions 리스트 렌더링 및 일괄 DB Upsert API 연동
  - [x] **S6-D3**: 세계관 설정집(`pages/worldmap.js`) 카테고리 필터링 탭 및 설정 추가/수정/삭제 CRUD 모달 연동
  - [x] **S6-D4**: 캐릭터 시트(`pages/characters.js`) 중요도 그룹핑(주인공/조연/주요/기타) 리스트 및 CRUD 모달 연동
  - [x] **S6-C5**: 회차 관리(`pages/episodes.js`) 에피소드 CRUD 및 본문 버전 트리 조회, 최종 원고 승인 API 연동
  - [x] **S6-D6**: 프로젝트 설정(`pages/settings.js`) 메인 LLM 관리 및 5가지 에이전트별(Plotter/Writer/Judge/Editor/Reviewer) 독자적 AI 사양(Provider, Model, API Key) 개별 오버라이드 폼 구현
- **주요 구현 내용**:
  - **탭 샌드박스**: 각 탭 콘텐츠는 별도 모듈로 분할하여 전역 상태 오염을 방지하고, CSS Grid 및 HSL 뱃지를 사용해 모던하고 시각적으로 구조화된 데이터 구조를 실현했습니다.
  - **원고 버전 트리**: 에피소드마다 기작성된 버전 목록을 date desc 순서로 받아와, 승인 여부에 따라 특별한 테두리(`border-secondary`) 및 `최종 승인본` 표시를 다르게 주고, 원문 전체보기 모달과 최종 승인 API를 연동했습니다.
- **기술적 결정 및 특이사항**:
  - 에이전트별 LLM 오버라이드는 Pydantic 스키마의 중첩 구조(`{ plotter: { llm_provider, llm_model, api_key_override } }`)에 정확히 맞추어 payload를 빌드하고 전송하도록 설계했습니다.
- **다음 에이전트 인수인계 사항 (Handoff)**:
  1. 다음 단계는 **Sprint 6-E (실시간 집필 모니터 구현)**입니다.
  2. `frontend/src/pages/writing-monitor.js`에 WebSocket 연결 및 인증 메시지 전송, 에이전트 상태 변경 통지 바인딩, 스트리밍 텍스트 실시간 출력 및 자동 스크롤, AI 평가 리포트 시각화 및 Human-in-the-loop 피드백 루프를 구현해야 합니다.

## [2026-07-13] Sprint 6-C 프론트엔드 인증 및 프로젝트 대시보드 구현 - Gemini 3.5 Flash

- **수행 태스크**:
  - [x] **S6-C1**: 로그인 페이지(`pages/login.js`) 구현 - 사용자명/비밀번호 입력 및 API 클라이언트를 통한 인증 연동 완료
  - [x] **S6-C2**: 회원가입 폼 및 회원가입 시 텔레그램 관리자 승인 대기 안내 화면 구현
  - [x] **S6-C3**: 프로젝트 대시보드(`pages/dashboard.js`) 목록 카드 그리드, 메인 AI 모델 배지, 생성일 포맷팅 및 빈 상태(Empty State) UI 연동
  - [x] **S6-C4**: 신규 프로젝트 생성 모달 및 AI 프로바이더별 모델 동적 리스팅(OpenAI, Google, Anthropic, Ollama) 연동
  - [x] **S6-C5**: 프로젝트 삭제 모달 및 안전 삭제 확인, 삭제 성공 시 DOM 제거 페이드 아웃 애니메이션 처리
- **주요 구현 내용**:
  - **로그인 & 가입**: 계정 생성 성공 시 즉시 로그인되지 않고, 백엔드의 승인 시스템에 따라 "텔레그램 승인 대기" 화면을 노출하여 Human-in-the-loop 가입 흐름을 완벽히 조화시켰습니다.
  - **대시보드 관리**: 프로젝트마다 설정된 메인 AI 프로바이더 정보에 맞춰 배지 형태로 색상을 입혀 시각적 직관성을 향상시켰으며, 삭제 시 팝업을 통한 경고 및 카드가 부드럽게 오그라들며 사라지는 효과를 적용했습니다.
- **기술적 결정 및 특이사항**:
  - FastAPI의 `OAuth2PasswordRequestForm` 로그인 방식을 온전히 지원하기 위해 `utils/auth.js`에서 `URLSearchParams`를 통해 form-urlencoded 데이터로 인코딩하도록 처리하여 인증 문제를 해결했습니다.
- **다음 에이전트 인수인계 사항 (Handoff)**:
  1. 다음 단계는 **Sprint 6-D (프로젝트 상세 탭 CRUD 구현)**입니다.
  2. `frontend/src/pages/project.js`에 프로젝트 상세 정보 로딩, 탭 네비게이션 및 각 하위 탭들(기획, 세계관, 캐릭터, 회차, 설정)을 구현 및 바인딩하면 됩니다.

## [2026-07-13] Sprint 6-A, 6-B 프론트엔드 프로젝트 초기화 및 인프라 레이어 구축 - Gemini 3.5 Flash

- **수행 태스크**:
  - [x] **S6-A1**: `frontend/` 디렉토리에 Vite 바닐라 JS 템플릿 설치 및 `package.json` 구성
  - [x] **S6-A2**: HSL 색상 토큰 기반 CSS 디자인 시스템 구축 (`frontend/src/style.css`)
  - [x] **S6-A3**: 바닐라 JS 기반 모달(`modal.js`), 토스트(`toast.js`), 로더 스피너/스켈레톤(`loading.js`) 공통 컴포넌트 구현
  - [x] **S6-A4**: 반응형 햄버거 메뉴를 지원하는 고정형 사이드바(`sidebar.js`) 구현
  - [x] **S6-B1**: `fetch` 기반 REST API 클라이언트(`api/client.js`) 구현 (JWT 자동 첨부, 401 Unauthorized 시 강제 로그아웃 가드 적용)
  - [x] **S6-B2**: JWT 토큰 만료 검증 및 URLSearchParams 기반 FastAPI 로그인 폼 대응 인증 모듈 (`utils/auth.js`) 구현
  - [x] **S6-B3**: 자동 재연결 및 JWT 인증을 지원하는 WebSocket 매니저 (`api/websocket.js`) 구현
  - [x] **S6-B4**: Regex 파라미터 매칭 및 인증 네비게이션 가드를 내장한 Hash SPA 라우터 (`utils/router.js`) 구현
  - [x] **S6-B5**: Vite 개발 프록시 설정 (`vite.config.js`) - `/api` -> `http://localhost:8080`, `/ws` -> WebSocket 포트 프록시
- **주요 구현 내용**:
  - **디자인 시스템**: 다크/라이트 테마를 CSS 변수 데이터 속성(`[data-theme]`)으로 동적 교체 가능하며, Galaxy Z Fold 4의 특수 비율(Folded: 1열 배치, Unfolded: 2/3열 배치)에 특화된 미디어 쿼리를 추가했습니다.
  - **인프라 레이어**: 바닐라 JS의 한계를 극복하기 위해 `CustomEvent`를 활용한 테마 변경/상태 갱신 이벤트를 전역 브로드캐스트하며, Hash change 이벤트를 가로채는 독립형 SPA 라우터를 구축했습니다.
- **기술적 결정 및 특이사항**:
  - Vite의 `/api` 경로 요청을 백엔드 REST 주소 `http://localhost:8080/`로 변환할 때, prefix인 `/api`를 rewrite를 통해 제거하도록 `vite.config.js`를 구성하여 백엔드 소스 수정 없이 즉시 작동되게 설계했습니다.
  - 빌드 검증 결과 `npm run build`가 146ms 만에 번들 파일(~13KB JS, ~5KB CSS)을 정상 산출함을 확인했습니다.
- **다음 에이전트 인수인계 사항 (Handoff)**:
  1. 다음 단계는 **Sprint 6-C (인증 & 대시보드 페이지 구현)**입니다.
  2. `frontend/src/pages/login.js`와 `frontend/src/pages/dashboard.js`에 실제 UI 폼 및 REST API 연동 로직을 바인딩하면 됩니다.

## [2026-07-10] AI 평가 에이전트(ReviewerAgent) 도입 및 에이전트별 LLM 분리 설정 구현 - Antigravity

- **수행 태스크**:
  - [x] AI 종합 평가 에이전트(`ReviewerAgent`) 및 Pydantic `ReviewReport` 스키마 구현 (`app/services/agents.py`)
  - [x] `Project` DB 모델 확장 및 에이전트별 LLM 설정 컬럼 추가 (`app/models.py`)
  - [x] `Project` 테이블 마이그레이션 적용 및 `scripts/migrate_agent_llm_fields.py` 기동
  - [x] `LLMFactory` 고도화 (`get_model_for_agent` 추가로 fallback 정책 구현, `app/services/llm_factory.py`)
  - [x] LangGraph 워크플로우에 `reviewer_node` 추가 및 엣지 라우팅 개선 (`app/services/workflow.py`)
  - [x] WebSocket 전송 데이터 및 상태 전이 연동 (`app/routers/websocket.py`)
  - [x] Streamlit 대시보드 프로젝트 설정 관리 및 AI 검수 결과 대시보드 시각화 연동 (`ui/project_view.py`, `ui/monitor_view.py`, `ui/api_client.py`)
  - [x] 신규 에이전트 및 워크플로우 단위 테스트 추가 및 검증 완료 (`tests/test_agents.py`, `tests/test_workflow.py`)
- **주요 구현 내용**:
  - **ReviewerAgent**: 에피소드 완료 시 1회차 전체 본문을 RAG 맥락과 함께 분석하여 종합 점수(Strengths, Weaknesses, Suggestions, Summary)를 생성하며, 본문 구체 문구 인용(Citation) 지침으로 환각(Hallucination) 방지.
  - **에이전트별 LLM 분리 설정(방안 A)**: 기획/집필/검수/윤문/평가 에이전트에 개별 프로바이더, 모델명, API Key를 지정할 수 있는 옵셔널 필드를 지원하고 미지정 시 프로젝트 기본 설정으로 폴백.
  - **락 대기 지연 해결**: 종합 평가 연산 시 지연 시간에 대비해 실시간 웹소켓 이벤트 `"reviewing"` 상태 메시지를 브로드캐스트하여 로딩 중임을 통지.
- **기술적 결정 및 특이사항**:
  - 기존 E2E 테스트(`test_route_after_editor_scene_vs_episode`)에서 `user_review` 직행을 가정하던 부분을 `reviewer` 노드 경유로 변경됨에 따라 검증 대상 라우팅도 `"reviewer"`로 업데이트했습니다.
  - 추천 프리셋 셀렉트박스를 통해 OpenAI 및 Anthropic 최신 사양을 손쉽게 바인딩하도록 설계했습니다.

## [2026-07-10] 잔여 작업 문서화 및 당일 작업 마무리 - Grok

- **수행 태스크**:
  - [x] 잔여 작업 백로그 문서 작성: `design_docs/remaining_work_2026-07-10.md`
  - [x] README / sprint_board 링크·참고 반영
  - [x] Sprint 4-D 커밋 푸시 이후 후속 항목 정리 (커밋 별도)
- **주요 구현 내용**:
  - P0: API 키 암호화, WS 토큰, 임베딩 백필
  - P1: ConnectionManager, 모니터 UX, 텔레그램 E2E, outline UI
  - P2: product_spec 고급 UX
  - P3: Sprint 5 배포·백업
  - 운영 체크리스트 및 권장 착수 순서 고정
- **기술적 결정 및 특이사항**:
  - 당일 구현 범위는 4-D 로 마무리. 추가 코딩 없이 문서 인수인계로 세션 종료.
- **다음 에이전트 인수인계 사항 (Handoff)**:
  1. [`remaining_work_2026-07-10.md`](./remaining_work_2026-07-10.md) 의 **RW-01** 부터 착수 권장
  2. 리뷰 정본: [`code_review_2026-07-10.md`](./code_review_2026-07-10.md)
  3. 보드: `sprint_board.md` Sprint 4-D 완료 후 Sprint 5 또는 RW-01 마이크로 태스크 추가

---

## [2026-07-10] Sprint 4-D 리뷰 이슈 수정 구현 (WP-A~E) - Grok

- **수행 태스크**:
  - [x] **S4-D1 WP-A**: Editor→Judge (A1), HITL full-draft→user_review, loop≥3 draft merge
  - [x] **S4-D2 WP-B**: WorldSetting 임베딩 적재 + OpenAI 1536 고정
  - [x] **S4-D3 WP-C**: activate_user 테스트, WS is_active, requirements 보강
  - [x] **S4-D4 WP-D**: health 503, production JWT 거부, webhook secret fail-closed, bcrypt 72B
  - [x] **S4-D5 WP-E**: episode outline 스키마, UI 텔레그램 카피, session factory, bare except
  - [ ] Issue 9 API 키 at-rest 암호화 (후속)
  - [ ] Issue 17 ConnectionManager (후속)
- **주요 구현 내용**:
  - `app/services/workflow.py`: `route_after_editor`, `_finalize_judge_result`
  - `app/routers/world_setting.py` + `app/services/rag.py`: 임베딩 영속화
  - `app/routers/websocket.py`, `tests/conftest.py` (`activate_user`), `requirements.txt`
  - `app/main.py` health 503, telegram webhook fail-closed; `app/core/config.py` ENVIRONMENT
  - 테스트: workflow HITL 피드백 경로, telegram pending login, ui api_client synopsis 수정
- **기술적 결정 및 특이사항**:
  - Editor 수정문은 Writer를 거치지 않음 (옵션 A1).
  - 임베딩은 채팅 프로바이더와 무관하게 OpenAI `text-embedding-3-small` (키 없으면 키워드 RAG만).
  - API 키 평문 저장(Issue 9)은 `API_KEY_ENCRYPTION_SECRET` 슬롯만 두고 Sprint 5 전 암호화 작업으로 남김.
- **다음 에이전트 인수인계 사항 (Handoff)**:
  1. pytest 전체 green 확인 후 커밋 권장
  2. 잔여: Issue 9 Fernet 암호화, ConnectionManager, product_spec 고급 UX, Sprint 5 배포
  3. 프로덕션 기동 시 `ENVIRONMENT=production` + 비기본 `JWT_SECRET` 필수

## [2026-07-10] 전체 코드베이스 리뷰 문서화 및 수정 작업 패키지 준비 - Grok

- **수행 태스크**:
  - [x] design_docs 기준 프로젝트 목표 파악 및 전체 코드베이스 코드 리뷰 수행
  - [x] 리뷰 정본 문서 작성: `design_docs/code_review_2026-07-10.md`
  - [x] Sprint 4-D (Remediation) 마이크로 태스크 보드 반영: `sprint_board.md`
  - [x] 코드 수정 착수 → 상단 로그(WP-A~E 구현) 참고
- **주요 구현 내용**:
  - 이슈 25건 정리 (8 bugs / 14 suggestions / 3 nits)
  - 작업 패키지 WP-A~E 및 권장 순서·설계 옵션(A1/B1) 확정안 문서화
  - 파일 영향 맵 및 검증 수칙 정의
- **기술적 결정 및 특이사항**:
  - 로컬 diff가 없어 **전체 코드베이스 + design_docs 정합** 기준으로 리뷰함.
  - 기본 구현 옵션: Editor→Judge 직행(A1), 고정 1536-d 임베딩(B1).
- **다음 에이전트 인수인계 사항 (Handoff)**: (구현 완료 — 상단 2026-07-10 구현 로그 참고)

---

## [2026-07-07] 회원가입 관리자 승인(이메일 연동) 흐름 구현 - Antigravity
- **수행 태스크**: 사용자 인증 강화 및 쿼터 남용 방지
- **주요 구현 내용**:
  - `User` 모델에 `is_active`, `is_admin` 필드 추가 및 DB 마이그레이션 스크립트 실행
  - `app/services/email_service.py` 생성: `smtplib`를 활용한 비동기 이메일 발송 로직 구현 (외부 패키지 미사용)
  - `app/routers/auth.py` 개편: 회원가입 시 승인 대기 상태 저장, 관리자 승인(`GET /auth/approve/{user_id}`) 및 알림 이메일 발송 처리
  - `dependencies.py` 내 `get_current_user`에서 미승인 계정 접근 차단 로직 추가
  - `ui/app.py` Streamlit 로그인/회원가입 메시지 렌더링 업데이트
- **기술적 결정 및 특이사항**:
  - 보안을 위해 `ui/app.py`에서 무분별한 회원 등록 시 로그인을 차단하고 관리자의 명시적 승인이 있어야만 활성화되도록 변경. Gmail SMTP 연동을 위해 `.env`에 설정 양식 추가.
- **다음 에이전트 인수인계 사항 (Handoff)**:
  - 실제 이메일 발송을 테스트하려면 `.env`에 유효한 SMTP 인증 정보(Gmail 앱 비밀번호 등)를 채워 넣은 후 실행하세요.

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

## [2026-06-29] Sprint 2-B 완료 및 설정/캐릭터 CRUD 검증 성공 - Antigravity

- **수행 태스크**:
  - [x] **Sprint 2-B**: 설정집(Lorebook) 및 캐릭터 CRUD API 개발 및 E2E 테스트 검증 (`tests/test_lore_char.py`)
- **주요 구현 내용**:
  - `app/schemas/world_setting.py` 및 `app/schemas/character.py`에 입력/출력 DTO 구현 완료.
  - `app/core/dependencies.py`에 `check_project_owner` 인가 헬퍼 추가 (project_id를 파라미터로 받아 로그인 유저 소유가 맞는지 확인하고, 아닐 시 403 Forbidden 차단).
  - `app/routers/world_setting.py` (세계관 설정 CRUD) 및 `app/routers/character.py` (캐릭터 시트 CRUD) 구현 및 `app/main.py`에 인클루드 완료.
  - `tests/test_lore_char.py` E2E 테스트 성공 (가입 ➔ 로그인 ➔ 프로젝트 생성 ➔ 설정/캐릭터 생성 ➔ 타인 토큰으로 해당 설정/캐릭터 접근 또는 생성 시도 시 403 Forbidden으로 원천 차단 검증 ➔ 수정 ➔ 삭제 ➔ 404 확인 ➔ cleanup 완료).
- **기술적 결정 및 특이사항**:
  - 설정집(`WorldSetting`)의 RAG용 벡터 데이터(`embedding`)는 수천 차원의 고용량 float 배열이므로, API 쿼리 및 통신 오버헤드를 획기적으로 줄이기 위해 **`WorldSettingResponse` 응답 스키마에서 embedding을 완벽히 마스킹(배제)**하도록 필드를 구성함.
- **다음 에이전트 인수인계 사항 (Handoff)**:
  - **Sprint 2-B가 성공적으로 완료(🎉 Done)**되었습니다.
  - 다음은 **Sprint 2-C: 회차(Episode) 및 parent_id 기반 버전 트리 조회 API 개발** 단계입니다.
  - 소설의 회차(Episode) 생성/조회/수정/삭제 라우터를 만들고, 본문(`Content`) 저장 시 특정 이전 버전(`parent_id`)을 부모로 상속받아 새로운 가지(Branch)를 칠 수 있는 트리형 Content 저장/조회 API를 완성하십시오.

## [2026-06-29] Sprint 2-C 완료 및 프로젝트/설정/회차/본문 버전관리 완료 (Phase 2 전체 완료) - Antigravity

- **수행 태스크**:
  - [x] **Sprint 2-C**: 회차(Episode) 및 parent_id 기반 버전 트리 조회 API 개발 및 E2E 테스트 검증 (`tests/test_episode_content.py`)
- **주요 구현 내용**:
  - `app/schemas/episode.py` 및 `app/schemas/content.py`에 Pydantic 입출력 DTO 구현 완료.
  - `app/routers/episode.py` (회차 CRUD) 및 `app/routers/content.py` (본문 버전 트리 CRUD 및 최종본 승인 API) 작성 완료.
  - **중복 승인 차단**: 한 회차 내 특정 버전을 승인(Approve) 처리할 때, 기존 승인된 본문들의 승인 여부(`is_approved`)를 자동으로 일괄 해제(False) 처리하는 비즈니스 가드 구축.
  - `tests/test_episode_content.py` E2E 테스트 성공 (가입 ➔ 프로젝트 생성 ➔ 회차 생성 ➔ v1.0 본문 추가 ➔ v1.0 상속 v1.1 추가 ➔ 타인 접근 시 403 차단 검증 ➔ v1.1 승인 및 v1.0 승인 자동 해제 확인 ➔ cleanup 완료).
- **기술적 결정 및 특이사항 (DB 무결성 고도화)**:
  - **Cascade Delete 연동**: 부모 프로젝트 삭제 시 연관 에피소드, 세계관, 캐릭터가 Null 처리되는 대신 자동으로 동시 전멸되도록 `app/models.py` 관계 설정에 `sa_relationship_kwargs={"cascade": "all, delete-orphan"}`을 보강함.
  - **자기참조 외래키 충돌 해결**: 본문 버전들 간에 `parent_id` 외래키 참조 관계가 걸려 있어 일괄 삭제 시 `ForeignKeyViolationError`가 발생하는 문제를 예방하기 위해, `parent_id` 컬럼 정의 시 `ondelete="SET NULL"` 제약조건을 강제하여 참조 교착 상태를 완벽히 해결함.
- **다음 에이전트 인수인계 사항 (Handoff)**:
  - **Sprint 2의 모든 마이크로 태스크가 완료(🎉 Done)**되었습니다.
  - 다음 주자는 **Sprint 3: AI 에이전트 & LangGraph 워크플로우** 단계입니다.

## [2026-06-30] Sprint 3-A, 3-B, 3-C 전체 완료 및 에이전트/LangGraph/pgvector RAG 통합 성공 - Antigravity

- **수행 태스크**:
  - [x] **Sprint 3-A**: AI 에이전트 프롬프트 설계 및 LLM Factory 동적 바인딩 (`app/services/agents.py`, `tests/test_agents.py`)
  - [x] **Sprint 3-B**: LangGraph Cyclic Graph 순환 워크플로우 정의 및 DB 체크포인터 연동 (`app/services/workflow.py`, `tests/test_workflow.py`)
  - [x] **Sprint 3-C**: pgvector/키워드 하이브리드 RAG 파이프라인 엔진 구현 및 연동 (`app/services/rag.py`, `tests/test_rag.py`)
- **주요 구현 내용**:
  - **4대 AI 에이전트 모듈화**: `PlotterAgent`, `WriterAgent`, `JudgeAgent`, `EditorAgent`를 설계하고, 생성자 레벨에서 LangChain prompt | model 체인을 완성하도록 최적화하여 런타임 성능 및 단위 테스트 모킹 편의성을 개선했습니다.
  - **LangGraph 순환 워크플로우 구축**: 기획(Plotter) ➔ RAG ➔ 씬 집필(Writer) ➔ 검수(Judge) ➔ 피드백 윤문(Editor) ➔ 사용자 검토(Human-in-the-loop) ➔ DB 저장(Save)으로 흐르는 상태 관리 제어 흐름을 구현했습니다.
  - **하이브리드 RAG 엔진 (pgvector + 키워드)**: 관련 캐릭터의 가중치 기반 중요도 키워드 매칭과, 세계관 설정(Lorebook)에 대한 pgvector 코사인 유사도 벡터 거리(cosine_distance) 검색을 유기적으로 엮어 맞춤형 맥락(lore_context)을 동적 제공하도록 연동했습니다.
  - **세션 체크포인트 영구 저장**: `langgraph-checkpoint-postgres` 및 `psycopg[binary]` 패키지를 설치하여 PostgreSQL을 활용한 체크포인트 영구 적재(`AsyncPostgresSaver`)를 구현하였고, 검증 단계에서는 `MemorySaver`를 유연하게 스위칭하도록 추상화했습니다.
  - **모든 테스트 패스 (13 Passed)**: 에이전트 Mock 테스트, LangGraph cyclic 루프 중단/재개 E2E 테스트, pgvector 하이브리드 검색 테스트 등을 포함한 전체 테스트 스위트가 에러 없이 성공적으로 검증되었습니다.
- **기술적 결정 및 특이사항 (이벤트 루프 & 트랜잭션 최적화)**:
  - **NullPool 전환**: pytest 환경에서 비동기 DB 엔진이 풀링된 커넥션을 다른 테스트의 소멸된 이벤트 루프로 재사용하려다가 발생하는 `InterfaceError` / `MissingGreenlet` 오류를 차단하기 위해, `TESTING=True` 환경에서는 `NullPool`을 적용하여 격리성을 확보했습니다.
  - **즉시 ID 캡처(Flush 활용)**: 비동기 SQLAlchemy의 `commit()`이 모델 속성들을 일제히 만료시키는 특성 때문에 생기는 `MissingGreenlet` 에러를 회피하고자, `db_session.flush()` 호출 직후 기본 키 ID 값들을 일반 정수 변수에 즉시 캡처하여 안전하게 바인딩했습니다.
  - **씬 단위 드래프트 조기 병합**: 사용자 최종 검토 대기 시점(`interrupt_before`)에 전체 드래프트가 비어 있거나 상태 변수가 불일치하는 현상을 방지하기 위해, AI Judge 통과 즉시 해당 씬의 텍스트를 `draft`로 병합하고 상태값을 `waiting_user`로 선제 업데이트하도록 흐름을 견고히 보완했습니다.
- **다음 에이전트 인수인계 사항 (Handoff)**:
  - **Sprint 3의 모든 단계가 성공적으로 완결(🎉 Done)**되었습니다.
  - 다음 주자는 **Sprint 4: 실시간 웹 인터페이스 MVP (Phase 4)** 단계입니다.

## [2026-06-30] Sprint 4-A 완료 & 4-C 백엔드 연동 및 LangGraph E2E 테스트 버그 픽스 - Antigravity

- **수행 태스크**:
  - [x] **Sprint 4-A**: FastAPI WebSocket 라우터 구축 (`app/routers/websocket.py`) 및 `/ws/projects/.../write` 엔드포인트 연동
  - [x] **Sprint 4-C**: Human-in-the-loop 피드백 루프 백엔드 연동 및 LangGraph state resume 검증
  - [x] **테스트 및 버그 픽스**: `test_workflow.py` 및 `test_websocket.py` E2E 격리 테스트 통과 검증 완료 (14 passed)
- **주요 구현 내용**:
  - `app/routers/websocket.py`에 실시간 모니터링 및 스트리밍을 위한 WebSocket 라우터(`/ws/projects/{project_id}/episodes/{episode_id}/write`) 구현 완료.
  - JWT 토큰 인가 처리 및 프로젝트/에피소드 소유권 교차 검증을 포함한 보안 가드 완비.
  - LangGraph 워크플로우 실행 흐름을 WebSocket 메시지로 실시간 스트리밍(`on_status`, `on_chunk` 콜백 주입)하도록 연동.
  - 사용자 피드백 반영 및 재개(`submit_feedback`, `approve`) 액션을 통한 Human-in-the-loop 제어 기능 구현.
  - `tests/test_websocket.py` 추가를 통해 스트리밍 데이터 청크 및 승인 저장 E2E 실시간 통신 흐름 격리 검증 완료.
- **기술적 결정 및 특이사항**:
  - **버그 해결 1**: `TESTING=True` 환경에서 `plotter_node`가 패칭된 `PlotterAgent.run` 대신 하드코딩된 단일 씬 리스트를 즉시 반환하도록 구현되어 있어, 2개 이상의 씬을 검증하려는 `test_workflow.py`에서 `AssertionError`가 발생하는 현상을 발견했습니다. 이를 `TESTING` 환경에서도 `MagicMock`을 주입받은 `PlotterAgent`를 호출하여 패치가 정상 동작하도록 구조를 개선함으로써 해결했습니다.
  - **버그 해결 2**: `TESTING=True` 환경에서 `save_node`가 아예 데이터베이스에 적재하지 않고 Mock으로 스킵하도록 설정되어 있는 반면, `test_workflow.py` 테스트는 실제 데이터베이스에 정상적으로 세션 및 객체가 저장되었는지를 검증하려다 보니 `AssertionError`가 발생했던 문제를 해결했습니다. `save_node` 내 `TESTING` 예외 스킵 블록을 제거하여 테스트 모드에서도 SQLite 데이터베이스에 정상 적재되고 통합 단계를 검증할 수 있도록 바로잡았습니다.
- **다음 에이전트 인수인계 사항 (Handoff)**:
  - **Sprint 4의 백엔드 실시간 통신 & 피드백 핵심 엔진이 모두 정상 구현 및 검증 완료(🎉 Done)**되었습니다.
  - 다음은 **Sprint 4-B: Streamlit 대시보드 및 실시간 UI 구현** 단계입니다.
  - Streamlit 대시보드 화면을 통해 에이전트 진행 상태 실시간 뷰어, 설정집 관리 인터페이스 및 승인/반려 피드백 UI 구성 요소를 구현하고, 이번에 완성한 WebSocket 엔드포인트와 연동하십시오.

## [2026-07-04] Sprint 4-B UI 세분화 및 1단계 구현 (로그인 및 대시보드) - Antigravity

- **수행 태스크**:
  - [x] Streamlit 종속성(`streamlit`, `websocket-client`) 설치 및 `requirements.txt` 갱신
  - [x] UI 작업의 안정성을 위해 Sprint 4-B 및 4-C UI 작업을 3개의 단계로 세분화 (1단계: 로그인/프로젝트 대시보드, 2단계: 프로젝트 내부 설정집/회차 관리, 3단계: 실시간 모니터링 및 피드백 인터페이스)
  - [x] **1단계 구현**: `ui/api_client.py` 및 `ui/app.py` 뼈대 생성. JWT 토큰 기반 인증 상태 관리 및 로그인/회원가입, 프로젝트 생성/목록 조회/삭제 기능 구현.
- **주요 구현 내용**:
  - `requirements.txt`에 UI 개발을 위한 필수 라이브러리 추가 및 설치 완료.
  - `ui/api_client.py`를 통해 FastAPI 통신 로직 모듈화 (요청 헤더에 JWT 자동 삽입).
  - `ui/app.py`에 `st.session_state`를 활용하여 토큰 관리, 로그인/대시보드 화면 전환 구현.
- **기술적 결정 및 특이사항**:
  - UI 렌더링 로직의 복잡성과 Streamlit 상태 관리(session_state) 충돌을 방지하기 위해 4-B 및 4-C UI 작업을 3단계로 나누어 점진적으로 컴포넌트를 확장하기로 결정했습니다.
- **다음 에이전트 인수인계 사항 (Handoff)**:
  - 1단계(S4-B1) 작업이 마무리되었습니다.
  - 다음 단계로 **2단계(S4-B2): 프로젝트 세부 화면(세계관, 캐릭터, 회차 관리 CRUD UI)** 구현을 진행하면 됩니다.

## [2026-07-04] Sprint 4-B UI 세분화 및 2단계 구현 (프로젝트 설정/회차 관리) - Antigravity

- **수행 태스크**:
  - [x] **2단계 구현**: `ui/project_view.py` 파일 분리 및 구현. 세계관(Lorebook) 추가/삭제, 캐릭터 추가/삭제, 회차 추가/삭제 및 에피소드 집필 뷰어 이동 버튼 UI 구성.
  - [x] `ui/api_client.py`에 Lorebook, Character, Episode에 대응되는 API 요청 래퍼 함수 추가.
  - [x] `ui/app.py` 라우팅 로직을 수정하여 대시보드에서 프로젝트 클릭 시 `project_view.render`를 호출하도록 연동.
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

## [2026-06-29] Sprint 2-B 완료 및 설정/캐릭터 CRUD 검증 성공 - Antigravity

- **수행 태스크**:
  - [x] **Sprint 2-B**: 설정집(Lorebook) 및 캐릭터 CRUD API 개발 및 E2E 테스트 검증 (`tests/test_lore_char.py`)
- **주요 구현 내용**:
  - `app/schemas/world_setting.py` 및 `app/schemas/character.py`에 입력/출력 DTO 구현 완료.
  - `app/core/dependencies.py`에 `check_project_owner` 인가 헬퍼 추가 (project_id를 파라미터로 받아 로그인 유저 소유가 맞는지 확인하고, 아닐 시 403 Forbidden 차단).
  - `app/routers/world_setting.py` (세계관 설정 CRUD) 및 `app/routers/character.py` (캐릭터 시트 CRUD) 구현 및 `app/main.py`에 인클루드 완료.
  - `tests/test_lore_char.py` E2E 테스트 성공 (가입 ➔ 로그인 ➔ 프로젝트 생성 ➔ 설정/캐릭터 생성 ➔ 타인 토큰으로 해당 설정/캐릭터 접근 또는 생성 시도 시 403 Forbidden으로 원천 차단 검증 ➔ 수정 ➔ 삭제 ➔ 404 확인 ➔ cleanup 완료).
- **기술적 결정 및 특이사항**:
  - 설정집(`WorldSetting`)의 RAG용 벡터 데이터(`embedding`)는 수천 차원의 고용량 float 배열이므로, API 쿼리 및 통신 오버헤드를 획기적으로 줄이기 위해 **`WorldSettingResponse` 응답 스키마에서 embedding을 완벽히 마스킹(배제)**하도록 필드를 구성함.
- **다음 에이전트 인수인계 사항 (Handoff)**:
  - **Sprint 2-B가 성공적으로 완료(🎉 Done)**되었습니다.
  - 다음은 **Sprint 2-C: 회차(Episode) 및 parent_id 기반 버전 트리 조회 API 개발** 단계입니다.
  - 소설의 회차(Episode) 생성/조회/수정/삭제 라우터를 만들고, 본문(`Content`) 저장 시 특정 이전 버전(`parent_id`)을 부모로 상속받아 새로운 가지(Branch)를 칠 수 있는 트리형 Content 저장/조회 API를 완성하십시오.

## [2026-06-29] Sprint 2-C 완료 및 프로젝트/설정/회차/본문 버전관리 완료 (Phase 2 전체 완료) - Antigravity

- **수행 태스크**:
  - [x] **Sprint 2-C**: 회차(Episode) 및 parent_id 기반 버전 트리 조회 API 개발 및 E2E 테스트 검증 (`tests/test_episode_content.py`)
- **주요 구현 내용**:
  - `app/schemas/episode.py` 및 `app/schemas/content.py`에 Pydantic 입출력 DTO 구현 완료.
  - `app/routers/episode.py` (회차 CRUD) 및 `app/routers/content.py` (본문 버전 트리 CRUD 및 최종본 승인 API) 작성 완료.
  - **중복 승인 차단**: 한 회차 내 특정 버전을 승인(Approve) 처리할 때, 기존 승인된 본문들의 승인 여부(`is_approved`)를 자동으로 일괄 해제(False) 처리하는 비즈니스 가드 구축.
  - `tests/test_episode_content.py` E2E 테스트 성공 (가입 ➔ 프로젝트 생성 ➔ 회차 생성 ➔ v1.0 본문 추가 ➔ v1.0 상속 v1.1 추가 ➔ 타인 접근 시 403 차단 검증 ➔ v1.1 승인 및 v1.0 승인 자동 해제 확인 ➔ cleanup 완료).
- **기술적 결정 및 특이사항 (DB 무결성 고도화)**:
  - **Cascade Delete 연동**: 부모 프로젝트 삭제 시 연관 에피소드, 세계관, 캐릭터가 Null 처리되는 대신 자동으로 동시 전멸되도록 `app/models.py` 관계 설정에 `sa_relationship_kwargs={"cascade": "all, delete-orphan"}`을 보강함.
  - **자기참조 외래키 충돌 해결**: 본문 버전들 간에 `parent_id` 외래키 참조 관계가 걸려 있어 일괄 삭제 시 `ForeignKeyViolationError`가 발생하는 문제를 예방하기 위해, `parent_id` 컬럼 정의 시 `ondelete="SET NULL"` 제약조건을 강제하여 참조 교착 상태를 완벽히 해결함.
- **다음 에이전트 인수인계 사항 (Handoff)**:
  - **Sprint 2의 모든 마이크로 태스크가 완료(🎉 Done)**되었습니다.
  - 다음 주자는 **Sprint 3: AI 에이전트 & LangGraph 워크플로우** 단계입니다.

## [2026-06-30] Sprint 3-A, 3-B, 3-C 전체 완료 및 에이전트/LangGraph/pgvector RAG 통합 성공 - Antigravity

- **수행 태스크**:
  - [x] **Sprint 3-A**: AI 에이전트 프롬프트 설계 및 LLM Factory 동적 바인딩 (`app/services/agents.py`, `tests/test_agents.py`)
  - [x] **Sprint 3-B**: LangGraph Cyclic Graph 순환 워크플로우 정의 및 DB 체크포인터 연동 (`app/services/workflow.py`, `tests/test_workflow.py`)
  - [x] **Sprint 3-C**: pgvector/키워드 하이브리드 RAG 파이프라인 엔진 구현 및 연동 (`app/services/rag.py`, `tests/test_rag.py`)
- **주요 구현 내용**:
  - **4대 AI 에이전트 모듈화**: `PlotterAgent`, `WriterAgent`, `JudgeAgent`, `EditorAgent`를 설계하고, 생성자 레벨에서 LangChain prompt | model 체인을 완성하도록 최적화하여 런타임 성능 및 단위 테스트 모킹 편의성을 개선했습니다.
  - **LangGraph 순환 워크플로우 구축**: 기획(Plotter) ➔ RAG ➔ 씬 집필(Writer) ➔ 검수(Judge) ➔ 피드백 윤문(Editor) ➔ 사용자 검토(Human-in-the-loop) ➔ DB 저장(Save)으로 흐르는 상태 관리 제어 흐름을 구현했습니다.
  - **하이브리드 RAG 엔진 (pgvector + 키워드)**: 관련 캐릭터의 가중치 기반 중요도 키워드 매칭과, 세계관 설정(Lorebook)에 대한 pgvector 코사인 유사도 벡터 거리(cosine_distance) 검색을 유기적으로 엮어 맞춤형 맥락(lore_context)을 동적 제공하도록 연동했습니다.
  - **세션 체크포인트 영구 저장**: `langgraph-checkpoint-postgres` 및 `psycopg[binary]` 패키지를 설치하여 PostgreSQL을 활용한 체크포인트 영구 적재(`AsyncPostgresSaver`)를 구현하였고, 검증 단계에서는 `MemorySaver`를 유연하게 스위칭하도록 추상화했습니다.
  - **모든 테스트 패스 (13 Passed)**: 에이전트 Mock 테스트, LangGraph cyclic 루프 중단/재개 E2E 테스트, pgvector 하이브리드 검색 테스트 등을 포함한 전체 테스트 스위트가 에러 없이 성공적으로 검증되었습니다.
- **기술적 결정 및 특이사항 (이벤트 루프 & 트랜잭션 최적화)**:
  - **NullPool 전환**: pytest 환경에서 비동기 DB 엔진이 풀링된 커넥션을 다른 테스트의 소멸된 이벤트 루프로 재사용하려다가 발생하는 `InterfaceError` / `MissingGreenlet` 오류를 차단하기 위해, `TESTING=True` 환경에서는 `NullPool`을 적용하여 격리성을 확보했습니다.
  - **즉시 ID 캡처(Flush 활용)**: 비동기 SQLAlchemy의 `commit()`이 모델 속성들을 일제히 만료시키는 특성 때문에 생기는 `MissingGreenlet` 에러를 회피하고자, `db_session.flush()` 호출 직후 기본 키 ID 값들을 일반 정수 변수에 즉시 캡처하여 안전하게 바인딩했습니다.
  - **씬 단위 드래프트 조기 병합**: 사용자 최종 검토 대기 시점(`interrupt_before`)에 전체 드래프트가 비어 있거나 상태 변수가 불일치하는 현상을 방지하기 위해, AI Judge 통과 즉시 해당 씬의 텍스트를 `draft`로 병합하고 상태값을 `waiting_user`로 선제 업데이트하도록 흐름을 견고히 보완했습니다.
- **다음 에이전트 인수인계 사항 (Handoff)**:
  - **Sprint 3의 모든 단계가 성공적으로 완결(🎉 Done)**되었습니다.
  - 다음 주자는 **Sprint 4: 실시간 웹 인터페이스 MVP (Phase 4)** 단계입니다.

## [2026-06-30] Sprint 4-A 완료 & 4-C 백엔드 연동 및 LangGraph E2E 테스트 버그 픽스 - Antigravity

- **수행 태스크**:
  - [x] **Sprint 4-A**: FastAPI WebSocket 라우터 구축 (`app/routers/websocket.py`) 및 `/ws/projects/.../write` 엔드포인트 연동
  - [x] **Sprint 4-C**: Human-in-the-loop 피드백 루프 백엔드 연동 및 LangGraph state resume 검증
  - [x] **테스트 및 버그 픽스**: `test_workflow.py` 및 `test_websocket.py` E2E 격리 테스트 통과 검증 완료 (14 passed)
- **주요 구현 내용**:
  - `app/routers/websocket.py`에 실시간 모니터링 및 스트리밍을 위한 WebSocket 라우터(`/ws/projects/{project_id}/episodes/{episode_id}/write`) 구현 완료.
  - JWT 토큰 인가 처리 및 프로젝트/에피소드 소유권 교차 검증을 포함한 보안 가드 완비.
  - LangGraph 워크플로우 실행 흐름을 WebSocket 메시지로 실시간 스트리밍(`on_status`, `on_chunk` 콜백 주입)하도록 연동.
  - 사용자 피드백 반영 및 재개(`submit_feedback`, `approve`) 액션을 통한 Human-in-the-loop 제어 기능 구현.
  - `tests/test_websocket.py` 추가를 통해 스트리밍 데이터 청크 및 승인 저장 E2E 실시간 통신 흐름 격리 검증 완료.
- **기술적 결정 및 특이사항**:
  - **버그 해결 1**: `TESTING=True` 환경에서 `plotter_node`가 패칭된 `PlotterAgent.run` 대신 하드코딩된 단일 씬 리스트를 즉시 반환하도록 구현되어 있어, 2개 이상의 씬을 검증하려는 `test_workflow.py`에서 `AssertionError`가 발생하는 현상을 발견했습니다. 이를 `TESTING` 환경에서도 `MagicMock`을 주입받은 `PlotterAgent`를 호출하여 패치가 정상 동작하도록 구조를 개선함으로써 해결했습니다.
  - **버그 해결 2**: `TESTING=True` 환경에서 `save_node`가 아예 데이터베이스에 적재하지 않고 Mock으로 스킵하도록 설정되어 있는 반면, `test_workflow.py` 테스트는 실제 데이터베이스에 정상적으로 세션 및 객체가 저장되었는지를 검증하려다 보니 `AssertionError`가 발생했던 문제를 해결했습니다. `save_node` 내 `TESTING` 예외 스킵 블록을 제거하여 테스트 모드에서도 SQLite 데이터베이스에 정상 적재되고 통합 단계를 검증할 수 있도록 바로잡았습니다.
- **다음 에이전트 인수인계 사항 (Handoff)**:
  - **Sprint 4의 백엔드 실시간 통신 & 피드백 핵심 엔진이 모두 정상 구현 및 검증 완료(🎉 Done)**되었습니다.
  - 다음은 **Sprint 4-B: Streamlit 대시보드 및 실시간 UI 구현** 단계입니다.
  - Streamlit 대시보드 화면을 통해 에이전트 진행 상태 실시간 뷰어, 설정집 관리 인터페이스 및 승인/반려 피드백 UI 구성 요소를 구현하고, 이번에 완성한 WebSocket 엔드포인트와 연동하십시오.

## [2026-07-04] Sprint 4-B UI 세분화 및 1단계 구현 (로그인 및 대시보드) - Antigravity

- **수행 태스크**:
  - [x] Streamlit 종속성(`streamlit`, `websocket-client`) 설치 및 `requirements.txt` 갱신
  - [x] UI 작업의 안정성을 위해 Sprint 4-B 및 4-C UI 작업을 3개의 단계로 세분화 (1단계: 로그인/프로젝트 대시보드, 2단계: 프로젝트 내부 설정집/회차 관리, 3단계: 실시간 모니터링 및 피드백 인터페이스)
  - [x] **1단계 구현**: `ui/api_client.py` 및 `ui/app.py` 뼈대 생성. JWT 토큰 기반 인증 상태 관리 및 로그인/회원가입, 프로젝트 생성/목록 조회/삭제 기능 구현.
- **주요 구현 내용**:
  - `requirements.txt`에 UI 개발을 위한 필수 라이브러리 추가 및 설치 완료.
  - `ui/api_client.py`를 통해 FastAPI 통신 로직 모듈화 (요청 헤더에 JWT 자동 삽입).
  - `ui/app.py`에 `st.session_state`를 활용하여 토큰 관리, 로그인/대시보드 화면 전환 구현.
- **기술적 결정 및 특이사항**:
  - UI 렌더링 로직의 복잡성과 Streamlit 상태 관리(session_state) 충돌을 방지하기 위해 4-B 및 4-C UI 작업을 3단계로 나누어 점진적으로 컴포넌트를 확장하기로 결정했습니다.
- **다음 에이전트 인수인계 사항 (Handoff)**:
  - 1단계(S4-B1) 작업이 마무리되었습니다.
  - 다음 단계로 **2단계(S4-B2): 프로젝트 세부 화면(세계관, 캐릭터, 회차 관리 CRUD UI)** 구현을 진행하면 됩니다.

## [2026-07-04] Sprint 4-B UI 세분화 및 2단계 구현 (프로젝트 설정/회차 관리) - Antigravity

- **수행 태스크**:
  - [x] **2단계 구현**: `ui/project_view.py` 파일 분리 및 구현. 세계관(Lorebook) 추가/삭제, 캐릭터 추가/삭제, 회차 추가/삭제 및 에피소드 집필 뷰어 이동 버튼 UI 구성.
  - [x] `ui/api_client.py`에 Lorebook, Character, Episode에 대응되는 API 요청 래퍼 함수 추가.
  - [x] `ui/app.py` 라우팅 로직을 수정하여 대시보드에서 프로젝트 클릭 시 `project_view.render`를 호출하도록 연동.
- **주요 구현 내용**:
  - `st.tabs`를 사용하여 "세계관", "캐릭터 시트", "회차 관리" 3개의 탭으로 공간을 분리하여 UX 개선.
  - FastAPI의 프로젝트 종속 하위 리소스들에 접근하는 REST API 통신 구현 완료.
- **기술적 결정 및 특이사항**:
  - 단일 `app.py`가 너무 길어지는 것을 방지하기 위해 개별 컴포넌트(`project_view.py`)로 파일을 나누어 모듈화 하였음.
- **다음 에이전트 인수인계 사항 (Handoff)**:
  - 2단계 작업이 마무리되었습니다.
  - 다음은 **3단계(S4-B3 및 S4-C2): 실시간 WebSocket 집필 모니터 화면 및 승인/반려 피드백 UI** 컴포넌트를 구현할 차례입니다.

## [2026-07-04] Sprint 4-B/C UI 세분화 및 3단계 구현 완료 (실시간 모니터 및 피드백) - Antigravity

- **수행 태스크**:
  - [x] **3단계 구현**: `ui/monitor_view.py` 파일 생성 및 WebSocket 통신 엔진 구축.
  - [x] 에이전트 상태 변경, 텍스트 스트리밍 렌더링, 사용자 검토 대기 모드(`waiting_user`) 컴포넌트 연동.
  - [x] Human-in-the-loop 피드백 제출 및 승인 처리 액션을 백엔드 WebSocket으로 라우팅.
- **주요 구현 내용**:
  - `websocket-client` 라이브러리를 활용하여, Streamlit의 선언적 UI 구조 내에서 `while` 루프를 돌며 `ws.recv()`로 수신한 JSON 청크를 `st.session_state`에 동기화하고 화면에 실시간 업데이트(`st.empty().markdown()`)하는 렌더링 함수(`handle_ws_loop`) 구현 완료.
  - 에피소드 선택 시 `app.py`에서 `monitor_view.py`로 라우팅되도록 통합 연동 완료.
- **기술적 결정 및 특이사항**:
  - Streamlit의 동기적 특성과 WebSocket의 비동기 스트림을 매끄럽게 연결하기 위해, 상태 변경 이벤트를 수신하면 `st.session_state.ws_status`를 전이시키고 `st.rerun()`을 호출하여 UI 컴포넌트가 올바른 뷰(작성 중/대기 중/승인 완료)를 표시하도록 제어의 역전을 구현함.
- **다음 에이전트 인수인계 사항 (Handoff)**:
  - **Sprint 4(UI/UX 및 WebSocket 실시간 통신 전체)**가 성공적으로 완결(🎉 Done)되었습니다.
  - 다음 주자는 **Sprint 5: 최적화 및 Termux 배포 (Phase 5)** 단계입니다. PM2, Nginx, Cloudflare Tunnel 세팅 및 PostgreSQL 백업 스크립트를 구현하십시오.

## [2026-07-04] Sprint 4 버그 픽스 및 UI 보완 - Antigravity

- **수행 태스크**:
  - [x] LangGraph f-string 파싱 에러 및 JsonPlusSerializer dumps 에러 픽스
  - [x] 캐릭터 시트 관리(수정 기능 추가) 및 UI enum 값 불일치 버그 픽스
  - [x] 에피소드 관리 탭 내에 '본문 확인하기' 인라인 뷰어 기능 탑재
  - [x] 배포 환경을 위한 JWT_SECRET 기본값 경고 처리 (보안 규칙 준수)
- **주요 구현 내용**:
  - `langgraph-checkpoint-postgres` 패키지를 최신(v3.1.0)으로 업데이트하여 JsonPlusSerializer 에러 원천 해결.
  - `ui/project_view.py` 및 `ui/api_client.py`에 캐릭터 수정 폼 및 API 연결 구현. 숫자 슬라이더를 문자열 드롭다운으로 교체하여 HTTP 422 에러 방지.
  - 에피소드 목록에서 작성 완료된 승인본(is_approved=True) 또는 최신 초안을 읽어오는 아코디언 컴포넌트 추가.
  - Streamlit 캐싱 충돌(AttributeError) 방지를 위한 `importlib.reload(api_client)` 명시.
- **기술적 결정 및 특이사항**:
  - JWT_SECRET과 같은 민감한 환경 변수가 상용 배포 환경에서 노출되는 것을 막기 위해 `app/core/config.py` 구동 시 경고 로그를 남기도록 보안을 강화함.
- **다음 에이전트 인수인계 사항 (Handoff)**:
  - MVP 개발 및 주요 버그 픽스가 안정화되었습니다. 이후 UI 렌더링 최적화 혹은 사용자 매뉴얼 작성을 진행하면 좋습니다.

Resume: agy --conversation=715aa061-8375-4247-9175-856ebceea967 (or -c)
### [2026-07-10] RW-01 프로젝트 API 키 암호화 구현 완료
- **수행자**: AI Agent
- **내용**: 
  - pp/core/crypto.py 에 Fernet 대칭키 암호화 모듈 추가
  - Project API 키 생성 및 수정 시 ncrypt_api_key 적용 (pp/routers/project.py)
  - LLMFactory 및 RAG 로직 호출 시 decrypt_api_key 적용하여 실행 시점에만 원문 로딩 (pp/services/llm_factory.py, pp/services/rag.py)
  - 평문 API 키 마이그레이션을 위한 scripts/migrate_api_keys.py 스크립트 작성
- **검증**: pytest 테스트 통과 및 문서 업데이트 완료


### [2026-07-10] RW-02 WebSocket JWT 전달 방식 개선 (보안 강화)
- **수행자**: AI Agent
- **내용**: 
  - `app/routers/websocket.py`에서 기존 URL Query Parameter(`?token=...`)를 이용한 인증 방식을 제거하고, 연결 직후 클라이언트가 보내는 첫 메시지 `{"action": "auth", "token": "..."}` 기반 인증으로 변경함.
  - `ui/monitor_view.py` (Streamlit UI)에서 WebSocket URL의 쿼리 파라미터를 제거하고 연결 시점에 `action: auth` JSON 페이로드를 전송하도록 클라이언트 수정함.
  - 관련 `pytest` (`test_websocket.py` 등) 수정 후 통과 확인함.
- **결과**: 브라우저 히스토리, 프록시, ngrok, Cloudflare 등의 액세스 로그에 사용자 JWT 토큰이 평문으로 기록되는 보안 취약점을 원천 차단함.


### [2026-07-10] RW-03 기존 WorldSetting 임베딩 백필 스크립트 작성 완료
- **수행자**: AI Agent
- **내용**: 
  - `scripts/backfill_embeddings.py` 관리 스크립트 신규 작성.
  - 해당 스크립트는 `WorldSetting` 테이블에서 임베딩이 비어있는 레거시 행을 조회하고, 각 프로젝트의 API 키 또는 전역 API 키를 활용하여 OpenAI 임베딩 API를 호출, `embedding` 컬럼을 백필함.
  - 대량의 API 호출을 고려하여 10개씩 배치(Batch) 형태로 DB 트랜잭션을 나누어 Commit 하도록 안정성 확보.
- **결과**: `pytest` 테스트 수행 후 정상 패스 확인 및 잔여 작업(remaining_work) 상태 갱신 완료.


### [2026-07-10] RW-04 WebSocket ConnectionManager 및 동시 쓰기 직렬화 구현 완료
- **수행자**: AI Agent
- **내용**: 
  - `app/routers/websocket.py` 내에 `ConnectionManager` 클래스를 구현하여 thread_id별 연결 객체(`active_connections`)와 락(`locks`)을 관리하도록 구조화함.
  - 동일한 에피소드(thread_id)에 여러 클라이언트가 동시 연결할 시, 실시간 스트리밍 메시지(`on_status`, `on_chunk`)가 `manager.broadcast`를 통해 모든 연결된 클라이언트에게 전송(multi-client 브로드캐스트)되도록 개선함.
  - `start_writing`, `submit_feedback`, `approve` 등의 그래프 실행 액션이 수행되는 동안 해당 `thread_id`에 대한 `asyncio.Lock`을 획득하도록 직렬화(Serialization)를 강제함. 만약 이미 락이 활성화되어 다른 작업이 진행 중이면, 중복 요청은 에러 메시지 반환 후 거부함.
- **결과**: `pytest` 테스트(`tests/test_websocket.py` 내의 `test_connection_manager_logic` 및 기존 E2E 테스트)가 정상 통과함을 확인함.


### [2026-07-10] RW-05 Streamlit 모니터 UX 보강 및 상태 연동 기능 개선 완료
- **수행자**: AI Agent
- **내용**: 
  - **상태 기반 화면 연동**: `app/routers/websocket.py`에서 웹소켓 연결 수립 즉시 기존에 실행되었던 진행 상황(`current_state` 이벤트)을 클라이언트에 전송하도록 구현함. `ui/monitor_view.py`에서는 최초 접속 시 `checking_state`를 통해 백엔드 상태를 조회하여 현재 집필 상황(writing/waiting_user/done/idle)에 따라 알맞은 화면을 자동으로 복구하도록 연동함.
  - **부드러운 화면 전환**: 피드백 반영 후 재작성(`submitting_feedback`) 시, 즉시 기존 화면을 다 지우지 않고 `clear_on_next_chunk` 플래그를 두어 새로운 AI 생성 텍스트의 첫 청크가 도착하는 시점에 클리어함으로써 화면 깜빡임 및 빈 공간 노출 UX를 개선함.
  - **네트워크 재연결 대응**: 웹소켓 통신 연결이 중단되거나 실패하는 경우를 대비해 3~5회 연결 재시도 로직을 설계하고, 재연결 실패 시 화면에 "다시 연결 시도" 버튼을 노출하는 `disconnected` 대체 상태를 추가함.
- **결과**: `pytest`를 통한 WebSocket 및 전반적인 E2E 테스트가 정상 수행됨을 확인함.


### [2026-07-10] RW-06 텔레그램 웹훅 승인/거절 E2E 테스트 구현 완료
- **수행자**: AI Agent
- **내용**: 
  - `tests/test_telegram.py` 파일의 승인, 거절, 재가입 관련 테스트 스텁들을 실제 E2E 시나리오로 전면 교체함.
  - **가입 승인 E2E 테스트 (`test_telegram_webhook_approve_success`)**: 신규 유저 등록 -> 비승인 상태 로그인 시도 (403 확인) -> webhook secret 및 callback_data 페이로드를 모킹하여 `/auth/telegram/webhook` 호출 -> 승인 처리 후 정상 로그인 (200 확인) E2E 검증.
  - **가입 거절 E2E 테스트 (`test_telegram_webhook_reject_success`)**: 유저 등록 -> 웹훅을 통해 거절 처리 -> 거절 완료된 사용자의 로그인 시도 시 거절 관련 메세지 반환 (403 확인) 검증.
  - **거절 유저 재가입 E2E 테스트 (`test_rejected_user_reregister`)**: 가입 -> 거절 -> 동일한 사용자명으로 재가입 시도 -> 정상 가입 처리 및 승인 대기 상태로 초기화되는 기능 검증.
- **결과**: `pytest tests/test_telegram.py` (5 passed) 및 전체 테스트 패키지 정상 통과 확인함.


### [2026-07-10] RW-07 Episode outline UI 연동 완료
- **수행자**: AI Agent
- **내용**: 
  - `ui/api_client.py`의 `create_episode` 함수 수정: 회차 생성 API 요청 시 `outline` 파라미터가 JSON 페이로드에 포함되도록 개선함.
  - `ui/project_view.py`의 회차 관리(tab3) 탭 수정: "새 회차 생성" 폼에 `e_outline` (Text area) 입력 필드를 탑재하고, 에피소드 리스트에서 개요가 존재할 시 `st.caption`을 통해 하단에 회차 개요가 노출되도록 뷰를 개선함.
- **결과**: `pytest` 테스트 정상 동작 및 UI 스키마 상의 정합성 확보 완료.
