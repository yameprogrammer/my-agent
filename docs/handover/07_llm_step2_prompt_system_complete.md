# LLM Step 2 Complete: 프롬프트 템플릿 시스템

## 구현 범위
- Step 2 목표: 프롬프트 템플릿을 코드에서 분리하고 버전 관리 + 재사용 가능한 시스템 구축
- `novel_blueprint/10_prompts_contracts.md` 의 섹션 분리 원칙(system/task/constraints/memory/output_schema) 구현
- PromptLoader를 통해 변수 치환 지원

## 변경/생성된 파일 및 구조
- `prompts/` (프로젝트 루트)
  - `system/base_novel_writer.md`
  - `episode/scene_writer_v1.md`
  - `planning/master_planner_v1.md`
- `packages/prompts/__init__.py`
- `packages/prompts/prompt_loader.py` — `PromptLoader` 클래스

## 주요 기능
- `PromptLoader(base_path="prompts").render("episode/scene_writer_v1", **variables)`
- `render_with_sections()` 로 # SYSTEM, # TASK 등 자동 파싱
- str.format 기반 치환 (누락 변수는 안전하게 빈 문자열 처리)
- Template 파일은 Markdown으로 관리, 버전(_v1) 포함

## 검증 결과
- 정상 렌더링 확인 (변수 치환 성공)
- sections 파싱 (system, task, constraints, memory_context, output_schema) 동작
- 기존 테스트에 영향 없음 (28 passed)

## 사용 예시
```python
from packages.prompts import PromptLoader

loader = PromptLoader()
prompt = loader.render(
    "episode/scene_writer_v1",
    episode_number=5,
    title_working="...",
    ...
)
```

## 운영 가이드
- 새로운 템플릿은 `prompts/` 하위에 추가
- LLM 호출 시 system + task 등을 결합하여 사용 예정 (Step 3+)
- 기본 템플릿은 LLM 호출 시 base_novel_writer와 episode 템플릿을 조합 가능

## 향후 연결
- Step 3에서 SceneWriterAgent가 이 템플릿을 사용해 LLM에 전달
- 프롬프트 버전 관리를 위해 `prompt_version` 필드와 함께 로깅 예정

## 참고
- 상세 사양서: `docs/llm-step-02-prompt-system-spec.md`
- 전체 계획: `docs/llm-implementation-plan.md`

---

**Step 2 완료**. 이제 프롬프트 기반 생성의 기반이 마련되었습니다.
