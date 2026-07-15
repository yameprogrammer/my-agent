# 코드 리뷰 개선 사항 리팩토링 개발 계획서 (Implementation Plan)

본 문서는 신규 구현된 어드민 포털 및 마이그레이션, 시딩 모듈에 대하여 코드 리뷰를 통해 발견된 성능, 보안, 오류 가능성 개선 과제를 실제로 완수하기 위한 마이크로 플랜을 다룹니다.

---

## 📅 Phase 1: 어드민 통계 API (stats) 쿼리 병렬 최적화
* **목표**: 순차 대기 방식으로 인한 DB I/O 레이턴시를 병렬화(`asyncio.gather`) 기법으로 튜닝합니다.

### 1.1. 라우터 코드 수정 (`app/routers/admin.py` 리팩토링)
* **수정 위치**: `get_admin_stats` 비동기 함수 내부
* **리팩토링 사양**:
  - `total_users_stmt`, `pending_users_stmt`, `total_projects_stmt`, `total_episodes_stmt` SQLModel 쿼리 구문을 먼저 선언합니다.
  - `asyncio.gather`를 호출하여 4개의 비동기 `session.execute` 작업을 병렬로 처리합니다.
  - 취합된 결과를 각각 언패킹하여 응답 모델을 생성합니다.

---

## 📅 Phase 2: 마이그레이션 이관 시 버전 트리 정렬 무결성 보강
* **목표**: 데이터 생성 시각(`created_at`)이 동일하거나 뒤바뀌어 유입될 경우, 트리 루트 노드가 무조건 먼저 삽입되도록 정렬 규칙을 튜플 키로 강화합니다.

### 2.1. 이관 서비스 코드 수정 (`app/services/migration.py` 리팩토링)
* **수정 위치**: `import_project_data` 내부 `sorted_contents` 정의 부분
* **리팩토링 사양**:
  - `key` 함수를 `lambda c: (0 if c.old_parent_id is None else 1, c.created_at)` 으로 지정합니다.
  - 이를 통해 parent_id가 없는(트리의 조상 노드) 항목이 시간 값보다 우선순위로 항상 먼저 DB에 삽입되어 `content_id_map` 사전에 등록되도록 보장합니다.

---

## 📅 Phase 3: 프로덕션 배포 기본 비밀번호 유출 Fail-Closed 가드 이식
* **목표**: 부주의한 프로덕션 배포 시, 하드코딩된 기본 관리자 자격증명 그대로 띄워지는 보안 사고를 원천 방지합니다.

### 3.1. 기동 시딩 스크립트 수정 (`app/main.py` 리팩토링)
* **수정 위치**: `seed_initial_admin` 비동기 함수 시작 부분
* **리팩토링 사양**:
  - `settings.ENVIRONMENT == "production"` 여부와 `settings.INITIAL_ADMIN_PASSWORD == "admin-pass-123!"` 여부를 동시에 만족하는지 감시합니다.
  - 만족할 경우, "보안 위배 경고"와 함께 `ValueError` 예외를 발생시키며 즉시 FastAPI 서버의 초기 구동을 기각(Fail-Closed) 처리합니다.

---

## 📅 Phase 4: 테스트 및 리그레션 검증
* **목표**: 개선된 최적화 및 보안 가드가 기존 마이그레이션/어드민 E2E 테스트 스위트와 완벽히 호환되는지 점검합니다.

### 4.1. 단위 테스트 검증
* `pytest tests/test_admin.py tests/test_migration.py` 재실행을 통해 리팩토링으로 인한 기존 로직 파손(Regression)이 없는지 정량적으로 검출합니다.
