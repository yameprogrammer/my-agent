# 신규 구현 기능 종합 코드 리뷰 리포트 (Code Review Report)

본 리포트는 최근 구현된 **소설 마이그레이션(Export/Import)**, **멀티포맷 다운로드 컴파일러**, **웹 어드민 포털 및 부트스트랩 시딩** 기능에 대해 퍼포먼스, 오류 위험성, 보안 관점에서의 정밀 코드 리뷰 및 개선 가이드라인을 제공합니다.

---

## 📈 1. 퍼포먼스 개선 가능 항목 (Performance Optimization)

### 1.1. 어드민 대시보드 통계 조회 병렬화 (stats API)
* **현상**: [routers/admin.py](file:///C:/Users/parkp/Workspace/personal/my-agent/app/routers/admin.py#L28-L43)의 `get_admin_stats` 엔드포인트는 총 유저 수, 대기 회원 수, 프로젝트 수, 에피소드 수를 조회할 때 4개의 쿼리를 순차적으로 `await` 하고 있습니다.
* **리스크**: DB 응답 지연 시간이 50ms라면 API 전체 대기 시간이 200ms 이상으로 늘어납니다.
* **개선안**: `asyncio.gather`를 사용해 4개의 카운트 쿼리를 병렬 실행하여 응답 지연을 대폭 단축합니다.
```python
# AS-IS (순차 대기)
total_users = (await session.execute(select(func.count(User.id)))).scalar() or 0
pending_users = (await session.execute(select(func.count(User.id)).where(...))).scalar() or 0

# TO-BE (병렬 실행)
import asyncio
results = await asyncio.gather(
    session.execute(select(func.count(User.id))),
    session.execute(select(func.count(User.id)).where(User.is_active == False, User.rejected_at == None)),
    session.execute(select(func.count(Project.id))),
    session.execute(select(func.count(Episode.id)))
)
total_users = results[0].scalar() or 0
pending_users = results[1].scalar() or 0
```

---

## ⚠️ 2. 오류 위험성 분석 (Robustness & Bug Prevention)

### 2.1. 마이그레이션 가져오기 시 버전 트리 정렬의 일관성 보장
* **현상**: [services/migration.py](file:///C:/Users/parkp/Workspace/personal/my-agent/app/services/migration.py#L187)의 `import_project_data`는 Content의 `parent_id`를 복구하기 위해 `created_at` 정렬에 의존하고 있습니다.
* **리스크**: 덤프 파일을 타 시스템에서 수동 편집했거나, DB 밀리초 정밀도 누락 등으로 생성 시각이 완전히 동일할 경우 자식 노드가 부모 노드보다 먼저 루프에 유입될 수 있습니다. 이 경우 `new_parent_id`가 `None`으로 복원되어 버전 분기 트리 구조가 끊어집니다.
* **개선안**: 단순 `created_at` 정렬에서 한 단계 나아가, `parent_id`가 없는 노드(루트 노드)를 우선 배치하거나 토폴로지 정렬(Topological Sort) 안전 장치를 가미해 순서를 무결하게 보장해야 합니다.
```python
# TO-BE: parent_id 여부를 1차 정렬 키로 적용 (None이 먼저 오도록 처리)
sorted_contents = sorted(
    ep_data.contents, 
    key=lambda c: (0 if c.old_parent_id is None else 1, c.created_at)
)
```

---

## 🔒 3. 보안 취약성 진단 (Security & Credentials)

### 3.1. 마이그레이션 JSON 평문 API Key 노출 방어
* **현상**: `export_project_data` 서비스는 DB에 Fernet으로 암호화되어 있던 타사 LLM API Key들을 복호화하여 평문(Plaintext) 상태로 JSON 다운로드 스트림에 실어 보냅니다.
* **리스크**: 사용자가 다운로드 받은 JSON 백업본을 외부에 분실하거나 실수로 타인에게 제공할 경우 API Key 도용 과금 리스크가 발생합니다.
* **개선안**: 내보내기 시 API Key 필드를 완전히 배제(Exclude)하는 옵션을 기본값(`exclude_keys=True`)으로 탑재하고, 필요할 경우 사용자의 명시적인 체크 및 암호 입력을 통해서만 API Key 복호화 덤프를 진행하게 하는 가드 장치가 필요합니다.

### 3.2. 초기 부트스트랩 어드민 비밀번호 기본값 유출 가드
* **현상**: [config.py](file:///C:/Users/parkp/Workspace/personal/my-agent/app/core/config.py#L55)에 기본 패스워드가 하드코딩(`admin-pass-123!`)되어 있습니다.
* **리스크**: 배포 담당자가 실 배포 시 `.env` 환경 변수로 관리자 비밀번호를 덮어씌우는 설정을 누락하면, 누구나 관리자 페이지에 기본 자격증명으로 로그인해 모든 회원의 정보 및 권한을 조작할 수 있는 심각한 위험이 있습니다.
* **개선안**: 프로덕션 모드(`ENVIRONMENT == "production"`)일 때 만약 `INITIAL_ADMIN_PASSWORD`가 기본값 그대로인 경우 서버 구동을 비정상 종료(`ValueError`) 시켜 안전하게 Fail-Closed 시켜야 합니다.
```python
# main.py lifespan의 seed_initial_admin 내부
if settings.ENVIRONMENT == "production" and settings.INITIAL_ADMIN_PASSWORD == "admin-pass-123!":
    raise ValueError("⚠️ 보안 경고: 프로덕션 환경에서는 기본 관리자 패스워드를 사용할 수 없습니다. .env 파일을 구성하세요.")
```
