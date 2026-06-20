# LLM Step 3 Complete: SceneWriterAgent LLM화 (실제 본문 생성)

## 구현 범위
- **Step 3 목표**: SceneWriterAgent가 실제 LLM (또는 stub LLM) + 프롬프트 템플릿을 사용해 소설 산문을 생성하도록 변경. **M1 핵심 가치 달성**
- LLM path와 기존 stub path 공존 (llm_client=None이면 기존 동작)
- PromptLoader + LLMClient 통합

## 주요 변경 파일
- `packages/agents/scene_writer_agent.py`
  - llm_client: LLMClient | None 추가
  - run()에서 LLM 사용 여부 분기
  - `_generate_with_llm()` 신규: PromptLoader로 템플릿 렌더 → llm_client.generate_text() 호출
- `packages/orchestrator/workflows.py`
  - build_episode_to_draft_workflow()에 llm_client 파라미터 추가 및 writer_agent에 전달
- `tests/test_scene_writer_agent.py` - 키워드 인자 업데이트

## 동작 방식
1. llm_client 제공 시: scene_writer_v1.md 템플릿 + 메모리 컨텍스트로 프롬프트 구성 → LLM generate_text()
2. None 시: 기존 _build_draft_text() 템플릿 사용 (하위 호환)
3. 생성된 draft_text는 DB에 EPISODE_DRAFT로 저장됨
4. assumptions에 "draft_text_generated_by_llm" 기록

## 검증 결과
- 직접 에이전트 테스트: LLM path 활성화 확인 ("draft_text_generated_by_llm" in assumptions)
- episode_to_draft 워크플로우 경유 호출 성공
- 관련 테스트 (test_scene_writer_agent, test_episode_workflow) 통과
- 전체 pytest 28 passed

## 사용 방법 (현재)
```python
from packages.llm import LLMFactory
from packages.orchestrator.workflows import build_episode_to_draft_workflow

llm_client = LLMFactory(mode="stub").create()  # or "ollama"
workflow = build_episode_to_draft_workflow(repo, memory, llm_client=llm_client)
```

## 한계 (이 단계)
- generate_text 결과가 stub이라 실제 문학적 품질은 아직 낮음 (다음 단계에서 프롬프트/모델 개선)
- 구조화 출력 미사용 (텍스트 위주)
- 로깅은 Step 6에서 강화 예정

## 다음 단계 연결
- Step 4: Master/Arc Planner LLM화
- Step 7: 전체 워크플로우에 llm_factory 전파
- Admin Console에서 LLM 모드 사용 시 실제 본문 확인 가능 (UI 이미 Episode Build 지원)

## 참고
- 상세 사양서: `docs/llm-step-03-scene-writer-spec.md`
- 이전 handover: 06 (LLM base), 07 (Prompts)

---

**Step 3 완료**. 이제 LLM 경로를 통해 에피소드 본문이 생성됩니다. (M1 달성)
