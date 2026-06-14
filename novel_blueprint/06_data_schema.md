# 데이터 모델 및 저장 구조

## 핵심 엔터티

권장 초기 테이블은 다음과 같다.

- novels
- novel_revisions
- concepts
- themes
- world_rules
- characters
- character_states
- factions
- locations
- arcs
- sub_arcs
- episodes
- episode_plans
- scenes
- scene_beats
- drafts
- memory_documents
- threads
- thread_events
- timeline_events
- validations
- generation_runs
- prompt_logs

## 주요 테이블 설명

### novels

작품의 최상위 메타 정보.

### arcs

메인 아크/미니 아크를 모두 저장하되 `arc_level`로 구분한다.

### episodes

회차 메타데이터.

예시 필드:
- episode_number
- title_working
- arc_id
- pov_character_id
- status
- target_length
- approved_revision_id

### episode_plans

화 세부 설계 저장.

### scene_beats

장면 단위 비트.

예시 필드:
- scene_order
- objective
- conflict
- outcome
- emotion_shift
- location_id
- participants

### threads

복선과 미해결 스레드.

예시 필드:
- thread_type
- planted_episode
- latest_episode
- planned_payoff_episode
- status
- importance

### timeline_events

서사상 확정된 사건 타임라인.

예시 필드:
- absolute_order
- relative_time_label
- event_summary
- participants
- consequences

### memory_documents

RAG 검색용 문서 저장소.

예시 필드:
- doc_type
- source_entity_type
- source_entity_id
- summary_text
- embedding
- metadata_json

## Revision 규칙

모든 주요 엔터티는 revision 구조를 지원해야 한다.

- 초안 생성
- 편집 수정
- 승인본 확정
- 잠금

승인본만 Canonical Memory로 승격한다.
