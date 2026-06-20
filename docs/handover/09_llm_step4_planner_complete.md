# LLM Step 4 Complete: Planner 에이전트 LLM화

## 구현 범위
- MasterPlannerAgent와 ArcPlannerAgent에 llm_client 지원 추가
- 프롬프트 기반 생성으로 logline, premise, world_rules, arcs 등을 LLM이 생성하도록 함
- 기존 seed 기반 로직은 fallback으로 유지
- theme_to_arcs 워크플로우에 llm_client 전달 가능
- admin UI에서 theme build 호출 시 llm_client 자동 주입

## 주요 변경
- `packages/agents/master_planner_agent.py`: llm_client 추가, _generate_with_llm 구현 (PromptLoader + generate_structured 사용)
- `packages/agents/arc_planner_agent.py`: 동일 패턴 적용
- `prompts/planning/arc_planner_v1.md` 신규 생성 (master는 Step 2에서 이미 존재)
- `packages/orchestrator/workflows.py`: build_theme_to_arcs_workflow에 llm_client 파라미터 추가
- `apps/admin/main.py`: theme_to_arcs 호출에 llm_client 전달

## 검증 결과
- theme_to_arcs 워크플로우 실행 시 LLM path 시도 (stub에서는 fallback 동작)
- 기존 tests 통과 (28 passed)
- logline/premise/arcs 생성 로직이 LLM을 통과하도록 변경
- 스텁 모드 완전 호환

## 수용 기준 충족
- theme_to_arcs 실행 시 (stub이라도) 구조 생성됨
- arcs 논리적 흐름 (기존 로직 fallback)
- DB 저장 정상

## 제한 사항
- 실제 LLM 사용 시 structured output이 완벽하지 않을 수 있음 (fallback 로직 있음)
- ThemeScoutAgent는 아직 LLM 미적용 (Step 4 범위 밖)

## 다음 단계
- Step 5: EpisodeDetail/Cycle 에이전트 LLM화
- 실제 Ollama 모델 사용 시 더 다양한 기획 결과 기대

## 참고
- 상세 사양: docs/llm-step-04-planner-agents-spec.md
- 이전: 08 (Step 3)

Step 4 완료.
