# 저장소 구조와 개발 순서

## 권장 저장소 구조

```text
novel-system/
  apps/
    api/
    worker/
    admin/
  packages/
    domain/
    agents/
    memory/
    orchestrator/
    validators/
    prompts/
    schemas/
    utils/
  docs/
  migrations/
  tests/
```

## 패키지 역할

- `domain`: 엔터티, 상태 전이, 비즈니스 규칙
- `agents`: 역할별 AI 모듈
- `memory`: 저장/검색/RAG
- `orchestrator`: 단계 실행 제어
- `validators`: 검수 로직
- `prompts`: 프롬프트 템플릿 버전 관리
- `schemas`: Pydantic 스키마

## 개발 순서

### Phase 1

- DB 스키마
- Pydantic 계약
- 메모리 저장소
- 기본 CRUD API

### Phase 2

- ThemeScoutAgent
- MasterPlannerAgent
- ArcPlannerAgent

### Phase 3

- EpisodeCycleAgent
- EpisodeDetailAgent
- SceneWriterAgent

### Phase 4

- ContinuityJudgeAgent
- StyleJudgeAgent
- ReaderHookJudgeAgent

### Phase 5

- Admin UI
- 승인/재계획 플로우
- 리포트/로그 뷰어

## 테스트 전략

- 스키마 파싱 테스트
- 상태 전이 테스트
- 메모리 검색 테스트
- 프롬프트 회귀 테스트
- 샘플 소설 프로젝트 end-to-end 테스트
