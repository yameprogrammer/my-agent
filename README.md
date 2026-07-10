# AI 소설 집필 에이전틱 머신 (Novel Writing Agent Project)

본 프로젝트는 AI API와 LangGraph 워크플로우를 활용하여 갤럭시 Z 폴드 4 (Termux) 환경에서 동작하는 완전 자동화 에이전틱 소설 집필 머신을 구축합니다.

---

## 👥 에이전트 협업 및 인수인계 가이드
본 프로젝트는 **에이전틱 개발 방식(Agentic Development)**으로 진행되며, 작업 도중 에이전트가 교체되거나 다른 세션에서 개발을 이어받을 수 있습니다. 
다음 에이전트는 아래 지침에 따라 작업을 인수인계 받으십시오.

1. **현재 상태 확인**: 
   - [sprint_board.md](file:///C:/Users/parkp/Workspace/personal/my-agent/design_docs/sprint_board.md)를 열어 현재 어떤 스프린트와 태스크가 진행 중(`In Progress`)인지 확인하십시오.
2. **구현 히스토리 확인**:
   - [development_log.md](file:///C:/Users/parkp/Workspace/personal/my-agent/design_docs/development_log.md)에서 이전 에이전트가 작성한 개발 기록, 이슈 사항, 해결 방법을 확인하십시오.
3. **태스크 수행 수칙**:
   - 코드를 작성할 때는 `sprint_board.md`에 명시된 **"구현/검증 수칙"**을 철저히 준수해야 합니다.
   - 각 마이크로 태스크 완료 시 반드시 테스트(단위 테스트 스크립트 작성 및 실행)를 거친 후 완료 처리하십시오.
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
- [remaining_work_2026-07-10.md](file:///C:/Users/parkp/Workspace/personal/my-agent/design_docs/remaining_work_2026-07-10.md): **[다음 착수]** 잔여 작업 백로그 (보안·WS·배포·product_spec)
