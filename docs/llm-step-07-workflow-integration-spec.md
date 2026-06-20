# Step 7: 워크플로우 + 메모리 통합 — 상세 작업 사양서

## 1. 목표
- 모든 워크플로우가 `llm_factory`를 받도록 변경
- 에이전트 생성 시 LLM 전달
- 메모리 컨텍스트를 프롬프트에 잘 주입

## 2. 주요 변경 파일
- `packages/orchestrator/workflows.py`
  - `build_*_workflow` 함수에 `llm_factory` 파라미터 추가
  - 각 agent 생성 시 `llm_client=llm_factory.create()` 전달

- `apps/admin/main.py` 및 `workflow_helpers.py`
  - Workflow 실행 시 LLMFactory 주입

## 3. 메모리 주입 고도화
- `load_scoped_documents` 결과를 프롬프트의 MEMORY_CONTEXT 섹션에 정리해서 넣기
- 너무 많은 컨텍스트는 top-k 제한

## 4. 수용 기준
- [ ] Admin Console에서 LLM 모드로 전체 워크플로우 실행
- [ ] 생성 결과에 RAG에서 가져온 정보가 반영됨 (assumptions 또는 본문에)
- [ ] `embedder_factory`와 `llm_factory`가 함께 잘 동작

**선행**: Step 1~6의 기반이 어느 정도 갖춰진 후