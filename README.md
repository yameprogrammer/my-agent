# AI 소설 집필 에이전틱 머신 (Novel Writing Agent Project)

본 프로젝트는 AI API와 LangGraph 워크플로우를 활용하여 갤럭시 Z 폴드 4 (Termux) 환경에서 동작하는 완전 자동화 에이전틱 소설 집필 머신을 구축합니다.

---

## 👥 에이전트 협업 및 인수인계 가이드
본 프로젝트는 **에이전틱 개발 방식(Agentic Development)**으로 진행되며, 작업 도중 에이전트가 교체되거나 다른 세션에서 개발을 이어받을 수 있습니다. 
다음 에이전트는 아래 지침에 따라 작업을 인수인계 받으십시오.

0. **보안·작업 규칙 (필수, 최우선)**:
   - **[`.agents/AGENTS.md`](.agents/AGENTS.md)** 를 읽고 준수하십시오. (공개 GitHub 저장소 — 시크릿·export·production 가드)
   - 커밋/푸시 전: `python scripts/check_no_secrets.py` 및 staged 목록에 `.env` 없는지 확인.
1. **현재 상태 확인**: 
   - [sprint_board.md](design_docs/sprint_board.md)를 열어 현재 어떤 스프린트와 태스크가 진행 중(`In Progress`)인지 확인하십시오.
2. **구현 히스토리 확인**:
   - [development_log.md](design_docs/development_log.md)에서 이전 에이전트가 작성한 개발 기록, 이슈 사항, 해결 방법을 확인하십시오.
3. **태스크 수행 수칙**:
   - 코드를 작성할 때는 `sprint_board.md`에 명시된 **"구현/검증 수칙"**을 철저히 준수해야 합니다.
   - 각 마이크로 태스크 완료 시 반드시 테스트(단위 테스트 스크립트 작성 및 실행)를 거친 후 완료 처리하십시오.
   - 보안 관련 변경 시 `tests/test_security_hardening.py` 및 AGENTS.md 체크리스트를 함께 갱신하십시오.
4. **진행 상황 업데이트**:
   - 태스크 완료 시 `sprint_board.md`와 `development_log.md`를 업데이트하여 다음 에이전트를 위한 상태를 동기화하십시오.

---

## 📁 주요 기획 및 설계 문서
- [project_concept.md](file:///C:/Users/parkp/Workspace/personal/my-agent/design_docs/project_concept.md): 에이전트 구성 및 DB 기본 구조
- [tech_stack.md](file:///C:/Users/parkp/Workspace/personal/my-agent/design_docs/tech_stack.md): 모바일 홈 서버 최적화 기술 스택
- [supplementary_design_specs.md](file:///C:/Users/parkp/Workspace/personal/my-agent/design_docs/supplementary_design_specs.md): 비동기 DB, Git-like 버전 트리, RAG, WebSocket 상세 사양
- [implementation_roadmap.md](file:///C:/Users/parkp/Workspace/personal/my-agent/design_docs/implementation_roadmap.md): 대단계 로드맵
- [sprint_board.md](file:///C:/Users/parkp/Workspace/personal/my-agent/design_docs/sprint_board.md): **[핵심]** 마이크로 태스크 보드 및 상태 트래커
- [development_log.md](file:///C:/Users/parkp/Workspace/personal/my-agent/design_docs/development_log.md): **[핵심]** 누적 개발 일지
- [code_review_2026-07-10.md](file:///C:/Users/parkp/Workspace/personal/my-agent/design_docs/code_review_2026-07-10.md): 전체 코드베이스 리뷰 및 Sprint 4-D 수정 작업 패키지
- [remaining_work_2026-07-10.md](file:///C:/Users/parkp/Workspace/personal/my-agent/design_docs/remaining_work_2026-07-10.md): 잔여 작업 백로그 (2026-07-10, 부분 구식)
- [post_mvp_review_and_backlog_2026-07-26.md](file:///C:/Users/parkp/Workspace/personal/my-agent/design_docs/post_mvp_review_and_backlog_2026-07-26.md): **[다음 착수]** 포스트 MVP 리뷰 · 보완 사항(IMP) · 추가 아이디어(IDEA) 백로그
- [frontend_rebuild_review.md](file:///C:/Users/parkp/Workspace/personal/my-agent/design_docs/frontend_rebuild_review.md): 프론트엔드 재구현 검토 보고서 (Streamlit → Vite SPA 전환 타당성 분석)
- [frontend_rebuild_plan.md](file:///C:/Users/parkp/Workspace/personal/my-agent/design_docs/frontend_rebuild_plan.md): **[Sprint 6]** 프론트엔드 재구현 작업 계획서 (마이크로 태스크 6-A ~ 6-G)

---

## 🔒 공개 저장소 보안 유의사항
에이전트·기여자 **전체 규칙**: **[`.agents/AGENTS.md`](.agents/AGENTS.md)** (시크릿, production 가드, export, 커밋 체크리스트).

- **`.env` 는 커밋하지 마십시오** (`.gitignore` 처리). 실 API 키·텔레그램 토큰·ngrok 토큰은 로컬/서버 환경변수만 사용합니다.
- 푸시 전 시크릿 스캔: `python scripts/check_no_secrets.py`
- **프로덕션** (`ENVIRONMENT=production`): 기본 `JWT_SECRET` / 약한 admin 비밀번호 / 기본 DB 비밀번호(`password`) / `API_KEY_ENCRYPTION_SECRET` 미설정 시 **기동 거부**.
- 프로젝트 **export / admin 백업** 기본값은 **API 키 미포함**. 키 이전이 필요할 때만 `?include_secrets=true` (파일 취급 주의).
- `docker-compose.prod.yml` 은 `POSTGRES_PASSWORD`, `JWT_SECRET`, `INITIAL_ADMIN_PASSWORD`, `API_KEY_ENCRYPTION_SECRET` 을 **필수**로 요구합니다.

---

## 🚀 로컬 구동 및 빌드 가이드

### 1. 개발(Vite Hot-Reload) 모드 구동
프론트엔드 코드 수정 즉시 브라우저에 반영되는 모드입니다.
1. **백엔드 기동**:
   ```bash
   .venv\Scripts\python.exe -m uvicorn app.main:app --port 8080 --reload
   ```
2. **Vite Dev Server 기동**:
   ```bash
   cd frontend
   npm run dev
   ```
   * 브라우저에서 `http://localhost:3000`으로 접속하면 Vite가 자동으로 API 및 WS 통신을 8080 백엔드 포트로 프록시 전달합니다.

### 2. 프로덕션 빌드 및 FastAPI 통합 서빙
Vite 산출물을 빌드하여 백엔드 단일 서버(8080)로 서비스를 통합 가동합니다.
1. **프론트엔드 빌드**:
   ```bash
   cd frontend
   npm run build
   ```
   * `frontend/dist/` 디렉토리에 정적 파일들(HTML, JS, CSS)이 최적화 빌드되어 생성됩니다.
2. **FastAPI 백엔드 단독 실행**:
   ```bash
   .venv\Scripts\python.exe -m uvicorn app.main:app --port 8080
   ```
   * 브라우저에서 `http://localhost:8080`에 접속하면 별도의 프론트엔드 노드 서버 없이 소설 집필 머신 SPA가 완전 가동됩니다.

