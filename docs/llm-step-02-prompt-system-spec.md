# Step 2: 프롬프트 템플릿 시스템 — 상세 작업 사양서

## 1. 목적
- 프롬프트를 하드코드에서 분리하여 관리
- 버전 관리, 재사용, A/B 테스트가 가능하게 함
- `novel_blueprint/10_prompts_contracts.md`의 원칙(시스템/태스크/제약/메모리/출력스키마 분리)을 구현
- Step 3(SceneWriter)에서 바로 사용할 수 있는 템플릿 제공

## 2. 주요 파일/디렉토리

- `prompts/` (프로젝트 루트에 생성 권장)
- `packages/prompts/prompt_loader.py`
- `packages/prompts/__init__.py`

추천 구조:
```
prompts/
  system/
    base_novel_writer.md
  planning/
    master_planner.md
    arc_planner.md
  episode/
    scene_writer.md
    episode_detail.md
    episode_cycle.md
  judge/
    continuity_judge.md
```

## 3. 상세 작업

### 3.1 PromptLoader 구현
- 템플릿 로드 (파일 읽기)
- 변수 치환 (Jinja2 추천, 없으면 str.format + dict)
- `render(template_name: str, **variables) -> str`

### 3.2 템플릿 섹션 규약 (모든 템플릿에 적용)
각 템플릿은 다음 섹션으로 나눈다:

```
# SYSTEM
당신은 웹소설 작가입니다. ...

# TASK
다음 정보를 바탕으로 ...

# CONSTRAINTS
- 상위 계획(arc, premise)을 절대 변경하지 마십시오.
- ...

# MEMORY_CONTEXT
{retrieved_context}

# OUTPUT_SCHEMA
JSON 형식으로만 응답하십시오. 스키마:
{output_schema_description}
```

### 3.3 기본 템플릿 최소 제공 (Step 3를 위해)
- `prompts/episode/scene_writer_v1.md`
- `prompts/planning/master_planner_v1.md` (선택)

### 3.4 SceneWriter 템플릿 예시 스케치 (v1)
```
# SYSTEM
당신은 한국 웹소설 전문 작가입니다. 몰입감 있고 생생한 산문을 작성합니다.

# TASK
아래 에피소드 카드와 장면 비트를 바탕으로 {episode_number}화의 본문을 작성하세요.

에피소드 제목: {title_working}
목표: {objective}
갈등: {conflict}
화말 훅: {cliffhanger}

장면 비트:
{% for beat in scene_beats %}
- 장면 {beat.scene_order}: {beat.objective} / {beat.conflict} → {beat.outcome}
{% endfor %}

# CONSTRAINTS
- 800~1200자 정도의 자연스러운 한국어 산문
- 상위 arc와 premise를 존중
- 대사와 묘사를 적절히 섞음
- writer_warning 필드에 위험 요소 기록

# OUTPUT
{
  "draft_text": "...",
  "ending_hook": "...",
  "writer_warning": []
}
```

## 4. 코드 스케치

```python
# packages/prompts/prompt_loader.py
from pathlib import Path
import json

class PromptLoader:
    def __init__(self, base_path: str = "prompts"):
        self.base_path = Path(base_path)

    def render(self, name: str, **kwargs) -> str:
        path = self.base_path / (name + ".md")
        template = path.read_text(encoding="utf-8")
        # 간단 치환 or Jinja2
        return template.format(**kwargs)
```

## 5. 수용 기준
- [ ] `prompts/episode/scene_writer_v1.md` 파일 존재
- [ ] `PromptLoader().render("episode/scene_writer_v1", episode_card=..., scene_beats=...)` 정상 동작
- [ ] 템플릿에 `{{ }}` 또는 `.format` 치환 지원
- [ ] `prompt_version`을 템플릿 메타에 포함 (예: `v1`)
- [ ] 기존 에이전트에 영향을 주지 않음

## 6. 테스트
- `tests/test_prompt_loader.py` 작성
- 템플릿 렌더링 결과에 필수 키워드가 포함되는지 검증

## 7. 다음 단계
Step 2 완료 후 **Step 3**에서 이 템플릿을 사용해 실제 LLM 호출을 연결한다.