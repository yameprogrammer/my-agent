# 시스템 아키텍처

## 아키텍처 개요

시스템은 멀티 에이전트 + 외부 메모리 + 검수 게이트 구조로 설계한다. 장편 생성에서 단일 생성기보다 계획 에이전트, 장별 분배 에이전트, 동적 히스토리 압축을 사용하는 구조가 더 높은 일관성과 완성도를 보인다는 연구가 있다.[cite:22]

## 주요 컴포넌트

### 1. Orchestrator

역할별 에이전트 실행 순서를 통제한다. 상태 머신 기반으로 `DRAFT -> REVIEW -> APPROVED -> LOCKED` 같은 전이 규칙을 적용한다.

### 2. Agent Runtime

각 역할별 에이전트를 독립 모듈로 실행한다.

- ThemeScoutAgent
- MasterPlannerAgent
- ArcPlannerAgent
- EpisodeCycleAgent
- EpisodeDetailAgent
- SceneWriterAgent
- ContinuityJudgeAgent
- StyleJudgeAgent
- ReaderHookJudgeAgent

### 3. Memory Service

Story Bible과 회차 상태를 저장하고, 메타데이터 필터 + 벡터 검색 + 관계 조회를 지원한다. 장편 툴과 가이드들은 캐릭터 레지스트리, 용어집, 지속 스레드 같은 별도 상태 저장소를 사용한다.[cite:14][cite:17]

### 4. Validation Service

생성 산출물의 품질 검사와 설정 충돌 탐지를 수행한다. 플롯 스레드 추적과 orphan thread 탐지 같은 분석 기능은 장편 생성 툴에서 중요한 보조 계층으로 사용된다.[cite:14]

### 5. Author Console

사용자가 작품 상태를 시각적으로 확인하고 승인/수정하는 내부 콘솔이다.

## 권장 실행 형태

초기에는 단일 모놀리식 백엔드로 구현한다. 다음 구성으로 충분하다.

- FastAPI 앱 1개
- PostgreSQL 1개
- Vector Store 1개
- Worker 프로세스 1개 이상
- 관리자 UI 1개

확장 시에는 Orchestrator, Memory, Validation을 서비스 분리할 수 있다.

## 상태 전이 예시

- 작품 아이디어 생성 완료 -> 전체 설계 대기
- 전체 설계 승인 -> 아크 설계 가능
- 아크 설계 승인 -> 회차 사이클 생성 가능
- 회차 사이클 승인 -> 화 세부 설계 가능
- 화 세부 설계 승인 -> 집필 가능
- 집필 초안 생성 -> 검수 대기
- 검수 통과 -> 승인
- 검수 실패 -> 재생성 또는 인간 수정

## 설계 원칙

- 단계 산출물 잠금: 상위 승인 산출물은 하위 단계에서 직접 변경하지 않는다.
- 모든 변경은 revision을 남긴다.
- 생성 입력은 명시적이어야 하며 암묵적 문맥 사용을 최소화한다.
- 검색된 메모리와 실제 프롬프트에 사용된 메모리를 분리 기록한다.
