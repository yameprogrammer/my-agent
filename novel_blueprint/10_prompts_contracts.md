# 프롬프트 및 출력 계약

## 원칙

모든 에이전트는 자유문 생성보다 구조화 출력을 우선한다. 출력 형식이 고정되지 않으면 Coding Agent가 후속 로직을 안정적으로 구현하기 어렵다.

## 공통 출력 규약

- 최상위 JSON object 반환
- 모든 배열 필드 명시
- 불확실성은 `assumptions` 배열에 기록
- 금지: 사족, 메타 발화, 설명문, 코드 펜스

## 예시 계약: EpisodeDetailAgent

입력:

```json
{
  "novel_id": "string",
  "episode_id": "string",
  "arc_summary": "string",
  "recent_episode_summaries": ["string"],
  "character_states": [],
  "open_threads": [],
  "style_rules": []
}
```

출력:

```json
{
  "episode_goal": "string",
  "episode_theme": "string",
  "hook_opening": "string",
  "scene_beats": [
    {
      "scene_order": 1,
      "objective": "string",
      "conflict": "string",
      "outcome": "string",
      "emotion_shift": "string",
      "thread_ops": []
    }
  ],
  "ending_hook": "string",
  "continuity_notes": ["string"],
  "assumptions": []
}
```

## 프롬프트 템플릿 관리

- 프롬프트는 파일로 버전 관리
- `system`, `developer`, `task`, `constraints`, `memory_context`, `output_schema` 구간 분리
- 모델 교체 시에도 동일 계약 유지

## 메모리 주입 규칙

프롬프트에 메모리를 무제한 삽입하지 않는다.

- must-have context
- relevant context
- optional references

이 세 층으로 나눠 주입한다.

## 집필 에이전트 제약

집필 에이전트는 다음을 하면 안 된다.

- 상위 설계를 임의 수정
- 결말 방향 변경
- 인물의 핵심 성격 뒤집기
- 설정에 없는 능력 추가

필요 시 `writer_warning` 필드로 리스크를 보고한다.
