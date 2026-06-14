# API, 작업 큐, 상태 전이 설계

## API 범주

### 작품 생성/관리 API

- `POST /novels`
- `GET /novels/{id}`
- `POST /novels/{id}/approve-stage`
- `POST /novels/{id}/replan`

### 설계 단계 API

- `POST /novels/{id}/concepts/generate`
- `POST /novels/{id}/master-plan/generate`
- `POST /novels/{id}/arcs/generate`
- `POST /novels/{id}/episodes/cycle-generate`
- `POST /episodes/{id}/detail-generate`
- `POST /episodes/{id}/draft-generate`

### 검수 API

- `POST /episodes/{id}/validate-continuity`
- `POST /episodes/{id}/validate-style`
- `POST /episodes/{id}/validate-hook`

### 메모리 API

- `POST /memory/query`
- `POST /memory/upsert`
- `POST /memory/promote-canonical`

## 작업 큐 설계

장시간 실행 작업은 비동기로 분리한다.

- generate_concepts_job
- generate_master_plan_job
- generate_arcs_job
- generate_episode_cycle_job
- generate_episode_detail_job
- write_episode_job
- validate_episode_job
- update_memory_job

## 상태 모델

- CREATED
- GENERATED
- REVIEW_PENDING
- APPROVED
- REJECTED
- LOCKED

## 실패 처리

- 에이전트 출력 스키마 검증 실패 시 재시도
- 메모리 검색 실패 시 fallback 조회 규칙 적용
- 검수 차단 시 상태를 `REJECTED`로 두고 수정 포인트 기록

## 추적성

각 job run은 다음을 기록한다.

- input snapshot
- retrieved memory ids
- prompt version
- model name
- raw output
- parsed output
- validation result
- reviewer decision
