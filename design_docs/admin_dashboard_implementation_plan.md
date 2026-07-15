# 웹 기반 운영자 관리 도구 (Admin Web) 구현 마이크로 플랜

본 문서는 기획 및 설계 문서를 기초로 하여 웹 기반 운영자 관리 기능을 단계별로 구현하기 위한 마이크로 수준의 개발 계획을 수립합니다.

---

## 📅 Phase 1: 백엔드 스키마 및 어드민 권한 의존성 정의
* **목표**: 어드민 API용 데이터 모델(Pydantic 스키마)을 선언하고 역할 기반 인가 계층(`get_current_admin`)을 구축합니다.

### 1.1. 스키마 정의 (`app/schemas/admin.py` 신규 생성)
* `AdminStatsResponse`: 시스템 대시보드용 요약 데이터 필드 정의 (`total_users`, `pending_users`, `total_projects`, `total_episodes`)
* `UserStatusChangeRequest`: 유저 상태 제어 액션 명세 (`action: Literal["approve", "reject", "suspend"]`)
* `UserRoleChangeRequest`: 유저 권한 제어 명세 (`is_admin: bool`)
* `AdminUserResponse`: 어드민 화면 회원 목록 렌더링용 프로필 필드 정의 (`id`, `username`, `email`, `is_active`, `is_admin`, `created_at`, `rejected_at`)
* `AdminUserListResponse`: 페이징이 포함된 회원 응답 명세 (`items: List[AdminUserResponse]`, `total: int`, `page: int`, `size: int`)

### 1.2. 보안 가드 의존성 구현 (`app/core/dependencies.py` 수정)
* `get_current_admin` 의존성 비동기 헬퍼 함수 구현:
  ```python
  async def get_current_admin(
      current_user: User = Depends(get_current_user)
  ) -> User:
      if not current_user.is_admin:
          raise HTTPException(
              status_code=status.HTTP_403_FORBIDDEN,
              detail="Access denied: Admin privilege required."
          )
      return current_user
  ```

---

## 📅 Phase 2: 어드민 API 라우터 및 데이터베이스 비동기 쿼리 구현
* **목표**: 어드민 전용 라우터를 구현하고, DB 세션을 통해 통계 및 회원 정보 상태를 조율하는 로직을 통합합니다.

### 2.1. 어드민 라우터 생성 (`app/routers/admin.py` 신규 생성)
* **`GET /api/v1/admin/stats`**:
  - `select(func.count(User.id))` 등 집계 함수를 이용한 회원/대기회원/프로젝트/에피소드 총합 통계 비동기 쿼리 수집.
* **`GET /api/v1/admin/users`**:
  - 유저이름/이메일 검색 키워드 바인딩 및 가입일 역순(DESC) 페이징 조회.
  - 검색 조건에 맞는 전체 행수(`total`) 계산 쿼리와 분할 슬라이싱(`limit`/`offset`) 데이터 쿼리를 비동기로 병렬/순차 실행.
* **`PATCH /api/v1/admin/users/{user_id}/status`**:
  - 회원 승인(`approve`): `is_active = True`, `rejected_at = None` 변경.
  - 회원 거절(`reject`): `is_active = False`, `rejected_at = datetime.utcnow()` 변경.
  - 회원 임시 정지(`suspend`): `is_active = False` 변경.
  - **자기 자신 제어 차단**: 현재 로그인한 관리자 ID(`current_admin.id`)와 변경 대상 `user_id`가 일치할 경우 `400 Bad Request` 에러를 던져 자신의 계정이 비활성화되는 불상사 방지.
* **`PATCH /api/v1/admin/users/{user_id}/role`**:
  - `is_admin` 필드 업데이트.
  - **자기 자신 권한 해제 차단**: 본인 관리자 권한을 스스로 낮추는 시도 발생 시 `400 Bad Request` 방어벽 가동.

### 2.2. 어드민 라우터 등록 및 SPA 가드 추가 (`app/main.py` 수정)
* `app.include_router(admin.router, prefix="/api/v1")`로 등록.
* **SPA Fallback API 차단 우회 리스트 업데이트**:
  - `/api/v1/admin` API 호출은 프론트엔드 HTML로 우회하지 않고 정상 404가 나가도록 차단 리스트에 추가합니다.
  - 단, 프론트엔드 `/admin` 브라우저 경로는 차단되지 않고 SPA Fallback에 의해 HTML이 서빙되도록 조율합니다.

---

## 📅 Phase 3: 테스트 및 무결성 검증
* **목표**: 일반 사용자 및 무단 접근에 대한 차단, 관리자의 정상 회원 상태 조율, 권한 자가 강등 방어 시나리오의 자동화 E2E 테스트를 완성합니다.

### 3.1. 관리자 기능 유닛 테스트 작성 (`tests/test_admin.py` 신규 생성)
* **테스트 케이스 구성**:
  1. `test_admin_stats_access_forbidden`: 일반 계정 토큰으로 stats API 요청 시 `403 Forbidden` 발생 여부 검증.
  2. `test_admin_users_pagination_and_search`: 어드민 계정으로 전체 회원 리스트 페이징 및 키워드 필터 조회 성공 여부 검증.
  3. `test_admin_user_approval_flow`: 가입 대기 유저의 승인/거절/일시정지 상태 변화 및 거절된 유저의 재승인 시 `rejected_at` 초기화 검증.
  4. `test_admin_self_modification_prevention`: 어드민이 자신의 계정을 suspend하거나 `is_admin=False`로 강등시키려 할 때 `400 Bad Request` 방어 확인.
* **테스트 수행**: `pytest tests/test_admin.py` 실행 및 유효성 확인.
