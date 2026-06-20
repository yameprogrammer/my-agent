# Step 5: Episode 상세 계획 에이전트 LLM화 — 상세 작업 사양서

## 1. 대상
- `EpisodeCycleAgent`
- `EpisodeDetailAgent`

## 2. 목표
- episode_card (제목, objective, hook, cliffhanger)
- scene_beats (objective, conflict, outcome, emotion_shift)를 창의적으로 생성

## 3. 주요 작업
- LLMClient 주입
- `_build_episode_card` LLM화
- `_build_scene_beat` LLM화
- continuity 고려한 입력(이전 에피소드 요약) 주입

## 4. 프롬프트
- `prompts/episode/episode_cycle_v1.md`
- `prompts/episode/episode_detail_v1.md`

## 5. 수용 기준
- [ ] 각 화의 제목과 갈등이 다양함
- [ ] scene_beats가 3~6개 생성되고 감정 변화가 있음
- [ ] episode_to_draft 호출 시 상세 비트가 의미 있음

**선행 단계**: Step 3, 4