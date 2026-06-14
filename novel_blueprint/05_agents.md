# 역할별 AI 에이전트 명세

## 공통 규칙

모든 에이전트는 다음 규칙을 따른다.

- 입력은 명시적 JSON 또는 구조화된 Markdown만 허용
- 출력은 스키마 검증 가능해야 함
- 허용된 메모리만 조회
- 상위 단계 승인 산출물을 임의 변경 불가
- 불확실한 정보는 추정하지 않고 질문 또는 `assumption` 필드로 표기

## 1. ThemeScoutAgent

목적: 소재, 장르, 주제, 상업성, 장기 연재 적합성을 평가한다.

입력:
- user_preferences
- genre_constraints
- market_positioning

출력:
- concept_candidates[]
- recommended_concept
- core_theme
- long_run_risk_analysis

## 2. MasterPlannerAgent

목적: 작품 전체 뼈대를 설계한다.

출력:
- logline
- premise
- protagonist_core_arc
- ending_direction
- world_rules
- major_reversal_points

## 3. ArcPlannerAgent

목적: 메인 아크와 서브 아크를 설계한다.

출력:
- main_arcs[]
- sub_arcs[]
- arc_dependencies[]
- payoff_map[]

## 4. EpisodeCycleAgent

목적: 각 화의 사이클과 리듬을 설계한다.

출력:
- episode_cards[]
- hook_type
- conflict_type
- reward_type
- cliffhanger_type

## 5. EpisodeDetailAgent

목적: 각 화의 세부 비트와 장면 구성을 만든다.

출력:
- episode_goal
- scene_beats[]
- emotional_curve
- continuity_notes
- thread_operations[]

## 6. SceneWriterAgent

목적: 승인된 비트에 따라 실제 소설 본문을 작성한다.

출력:
- draft_parts[]
- merged_draft
- carryover_notes

## 7. ContinuityJudgeAgent

목적: 설정 충돌과 타임라인 오류, 인물 상태 충돌을 탐지한다.

출력:
- issues[]
- severity
- blocking_decision
- suggested_fix

## 8. StyleJudgeAgent

목적: 문체, 톤, 웹소설 호흡을 평가한다.

출력:
- pacing_score
- readability_score
- tone_consistency_score
- webnovel_fit_score
- rewrite_suggestions[]

## 9. ReaderHookJudgeAgent

목적: 독자 관점에서 다음 화 클릭 유도를 평가한다.

출력:
- hook_strength
- curiosity_gap_score
- emotional_aftertaste_score
- next_episode_pull_score
