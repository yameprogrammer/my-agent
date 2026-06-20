# Step 6: 생성 로깅 및 프롬프트 이력 추적 — 상세 작업 사양서

## 1. 목적
- 어떤 프롬프트로, 어떤 모델로, 어떤 결과를 냈는지 기록
- 디버깅과 품질 개선을 위한 데이터 축적
- 기존 테이블 (`generation_runs`, `prompt_logs`)을 실제로 사용

## 2. 작업 내용

### 2.1 Repository 확장 (`src/my_agent/repository.py`)
- `create_generation_run(novel_id, run_type, ...)` 구현
- `create_prompt_log(...)` 구현

### 2.2 각 Agent에 로깅 추가
주요 필드:
- run_type: "master_planner", "scene_write", "episode_detail" 등
- model_name
- prompt_version
- raw_output (LLM 원문)
- parsed_output_json
- retrieved_memory_ids

### 2.3 Workflow 레벨 로깅
`packages/orchestrator/workflows.py`에서 각 단계 완료 시점에 기록

### 2.4 Admin Console 개선
- System Logs 메뉴에서 raw 프롬프트 일부 표시
- generation_runs 클릭 시 상세 보기

## 3. 수용 기준
- [ ] LLM 모드로 워크플로우 실행 후 `list_generation_runs()`에 레코드 쌓임
- [ ] prompt_logs에 실제 프롬프트 텍스트 저장
- [ ] UI에서 이전 실행 로그 확인 가능

**선행**: 최소 Step 3 완료 후 작업 추천