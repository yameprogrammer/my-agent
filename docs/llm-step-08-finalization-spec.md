# Step 8: 마무리, 검증, 문서화 — 상세 작업 사양서

## 1. 주요 작업

### 1.1 전체 시나리오 검증
- 새 프로젝트 생성 → Story Build (LLM) → Episode Build 1~2화 (LLM) → 원고 확인 → 검수
- 5분 이내에 실제 읽을 만한 결과가 나오는지 수동 테스트

### 1.2 문서 업데이트
- `docs/usage_guide.md`
  - LLM 설정 방법 추가 (`llm_config.json`)
  - 추천 모델 목록
- `README.md` LLM 섹션 보강
- `AGENTS.md` 업데이트 (이제 generation에도 LLM 사용 명시)

### 1.3 모델 전환 가이드
- `mode: "stub"` vs `"ollama"` 전환 방법 문서화
- 모델별 프롬프트 튜닝 팁

### 1.4 테스트 강화
- `tests/`에 LLM 모드용 간단 테스트 추가 (응답 mock 또는 실제 작은 모델)
- 생성 품질에 대한 간단한 회귀 테스트 (키워드 포함 여부 등)

### 1.5 Admin Console 개선
- Workflow Execution에 "LLM 모드 사용" 토글 또는 자동 감지
- 생성 결과에 "사용 모델 / 프롬프트 버전" 표시

## 2. 수용 기준
- [ ] 전체 M3 시나리오가 LLM 모드에서 동작
- [ ] 문서가 최신 상태
- [ ] 스텁 모드와 LLM 모드 모두 테스트 통과
- [ ] 사용자가 `llm_config.json`만 수정하면 쉽게 LLM을 켤 수 있음

## 3. 선택 과제 (후속)
- Style/ReaderHook 기반 자동 재작성
- 여러 모델 전략 (planner는 강한 모델, writer는 창의 모델)
- 프롬프트 버전 관리 UI

---

**전체 계획 완료 기준**: Step 1~8의 모든 상세 사양서 체크리스트 통과 + 실제 본문 생성 확인.