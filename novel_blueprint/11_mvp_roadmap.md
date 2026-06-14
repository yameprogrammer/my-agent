# MVP 구현 로드맵

## MVP 목표

첫 번째 목표는 150~200화를 완성하는 것이 아니라, 20~30화를 안정적으로 설계·집필·검수하는 시스템을 만드는 것이다. 장편 시스템은 초반부터 전체 스케일을 다 구현하기보다 짧은 구간에서 연속성과 반복 가능한 절차를 검증하는 편이 더 현실적이다.[cite:11][cite:22]

## MVP 범위

- 단일 작품 프로젝트 생성
- 소재/주제 생성
- 전체 설계 생성
- 3개 메인 아크 생성
- 20화 회차 카드 생성
- 각 화 세부 설계
- 각 화 초안 집필
- 기본 연속성 검수
- Story Bible 갱신

## MVP 제외

- 다중 작품 동시 운영
- 고급 대시보드 시각화
- 실제 시장 트렌드 자동 수집
- RL 기반 자동 최적화

## 단계별 구현

### Step 1

DB와 스키마, Memory CRUD, 문서 임베딩 저장 구현

### Step 2

ThemeScoutAgent와 MasterPlannerAgent 구현

### Step 3

ArcPlannerAgent와 EpisodeCycleAgent 구현

### Step 4

EpisodeDetailAgent와 SceneWriterAgent 구현

### Step 5

ContinuityJudgeAgent 구현

### Step 6

간단한 승인 UI 구현

### Step 7

샘플 프로젝트로 10화 E2E 테스트

## 확장 로드맵

- 시즌2/권 단위 운영
- 장르별 프롬프트 팩
- 독자 반응 시뮬레이터 고도화
- 자동 재계획 엔진
- 문체 학습/작가별 스타일 팩
