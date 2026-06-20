# Step 4: Planner 에이전트 LLM화 — 상세 작업 사양서

## 1. 대상 에이전트
- `MasterPlannerAgent`
- `ArcPlannerAgent`

## 2. 작업 목표
- logline, premise, world_rules, main_arcs, sub_arcs 등을 LLM이 창의적으로 생성
- 기존 seed 기반 스텁은 "seed inspiration" 또는 완전 fallback으로 전환

## 3. 주요 변경
### MasterPlannerAgent
- `llm_client` 주입
- `_build_world_rules`, `_build_reversal_points` 등을 LLM 호출로 대체
- Structured output: `MasterPlannerOutput`

### ArcPlannerAgent
- `llm_client` 주입
- `_build_main_arcs`, `_build_sub_arcs` LLM화

## 4. 프롬프트 전략
- `prompts/planning/master_planner_v1.md`
- `prompts/planning/arc_planner_v1.md`
- 반드시 `logline`, `premise`, `main_arcs[]` 같은 필드를 강제

## 5. 수용 기준
- [ ] theme_to_arcs 실행 시 logline/premise가 매 실행마다 다름
- [ ] arcs가 논리적 흐름과 갈등 escalation을 가짐
- [ ] 기존 `list_arcs` 결과가 DB에 정상 저장
- [ ] 스텁 모드와 호환

## 6. 파일 변경
- `packages/agents/master_planner_agent.py`
- `packages/agents/arc_planner_agent.py`
- 프롬프트 파일 2개
- 필요시 agent_schemas에 추가 필드

**선행**: Step 1, 2 (Step 3와 병행 가능)