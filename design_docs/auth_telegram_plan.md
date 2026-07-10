# 작업 계획서: 텔레그램 봇 기반 관리자 승인 시스템 구현

> **문서 버전**: v2.1  
> **최종 갱신일**: 2026-07-10  
> **관련 설계서**: `auth_telegram_design.md` v2.1  
> **관련 Sprint**: Sprint 3 (SP3-001 ~ SP3-005)

---

## 1. 전제 조건 (Prerequisites)

구현 착수 전 반드시 준비해야 할 항목:

- [ ] 텔레그램 봇 생성 (`@BotFather`) 및 API 토큰 확보
- [ ] 관리자 텔레그램 채팅 ID (`chat_id`) 확인 — `@userinfobot` 또는 `getUpdates` API 활용
- [ ] 로컬 개발용 터널 도구 준비 (Cloudflare Tunnel 또는 Ngrok) — Webhook 수신을 위해 필수
- [ ] `.env` 파일에 신규 환경 변수 추가 확인

---

## 2. 작업 단계별 상세 로드맵

### 단계 1: 환경 설정 및 설정 스키마 확장
**대응 Sprint 태스크**: SP3-001

- [ ] `.env` 파일에 환경 변수 추가:
  ```
  TELEGRAM_BOT_TOKEN=<봇 토큰>
  ADMIN_TELEGRAM_CHAT_ID=<관리자 chat_id>
  TELEGRAM_WEBHOOK_SECRET=<webhook 검증용 임의 문자열>
  ```
  > `BASE_URL`은 이미 존재 (기본값: `http://localhost:8000`). 로컬 개발 시 터널 URL로 변경 필요.
- [ ] `app/core/config.py`의 `Settings` 클래스에 필드 추가:
  ```python
  # 텔레그램 봇 관련 (신규)
  TELEGRAM_BOT_TOKEN: str = ""
  ADMIN_TELEGRAM_CHAT_ID: str = ""
  TELEGRAM_WEBHOOK_SECRET: str = ""
  ```
- [ ] 기존 SMTP 관련 필드는 `Optional`로 이미 선언되어 있으므로 변경 불필요
- [ ] `app/models.py`의 `User` 모델에 거절 이력 필드 추가:
  ```python
  rejected_at: Optional[datetime] = Field(default=None, nullable=True)
  ```
- [ ] 서버 시작하여 환경 변수 로드 및 모델 변경 정상 반영 확인

**완료 기준**: 서버가 신규 환경 변수를 정상 로드하고, 기존 기능에 영향 없음 확인

---

### 단계 2: 텔레그램 서비스 모듈 구현
**대응 Sprint 태스크**: SP3-002

- [ ] `app/services/telegram_service.py` 생성
- [ ] `TelegramBotService` 클래스 구현:
  - [ ] `__init__(token, admin_chat_id)` — 토큰 및 chat_id 초기화
  - [ ] `async _request(method, payload)` — 내부 API 호출 헬퍼
    - `httpx.AsyncClient(timeout=10.0)` 사용
    - 실패 시 최대 2회 재시도
    - 최종 실패 시 `None` 반환 (예외 미전파)
  - [ ] `async send_registration_alert(user)` — InlineKeyboard 포함 알림 발송
    - `User` 모델(SQLModel) 인스턴스를 인자로 받음
    - `user.username`, `user.email`, `user.id`, `user.created_at` 활용
  - [ ] `async send_message(chat_id, text)` — 일반 텍스트 메시지 발송
  - [ ] `async edit_message(chat_id, message_id, text)` — 메시지 텍스트 교체
  - [ ] `async answer_callback_query(callback_query_id, text)` — 콜백 쿼리 응답
  - [ ] `async set_webhook(url, secret_token)` — Webhook URL 등록
  - [ ] `async delete_webhook()` — Webhook 해제
- [ ] 단위 테스트 작성 (`tests/test_telegram.py` 일부):
  - [ ] `test_send_registration_alert_success` — 정상 발송 (httpx 응답 mock)
  - [ ] `test_send_registration_alert_api_failure` — API 실패 시 예외 미전파 확인

**완료 기준**: 모든 메서드가 비동기(`async def`)로 구현되고, API 실패가 예외로 전파되지 않음을 테스트로 검증

---

### 단계 3: 텔레그램 Webhook 라우터 구현
**대응 Sprint 태스크**: SP3-003

- [ ] `app/routers/telegram.py` 생성
- [ ] `POST /auth/telegram/webhook` 엔드포인트 구현:
  - [ ] `X-Telegram-Bot-Api-Secret-Token` 헤더 검증 → 불일치 시 `403`
  - [ ] `callback_query.from.id`(int→str 변환) 와 `ADMIN_TELEGRAM_CHAT_ID` 대조
  - [ ] `callback_data` 파싱 (`approve_{user_id}` / `reject_{user_id}`)
  - [ ] 승인 처리: `User.is_active = True` → `session.add()` → `session.commit()`
  - [ ] 거절 처리: `User.rejected_at = datetime.utcnow()` → `session.add()` → `session.commit()`
  - [ ] 이미 처리된 요청에 대한 멱등성 보장 로직 (유저 미존재, 이미 active, 이미 rejected)
  - [ ] `answerCallbackQuery` + `editMessageText` 응답 (TelegramBotService 활용)
- [ ] `app/main.py`에 라우터 등록:
  ```python
  from app.routers import telegram
  app.include_router(telegram.router)
  ```
- [ ] 단위 테스트 작성 (`tests/test_telegram.py` 추가):
  - [ ] `test_webhook_approve_success`
  - [ ] `test_webhook_reject_success`
  - [ ] `test_webhook_invalid_secret` → 403
  - [ ] `test_webhook_unauthorized_user` → 무시
  - [ ] `test_webhook_already_approved` → 멱등 처리
  - [ ] `test_webhook_already_rejected` → 멱등 처리
  - [ ] `test_webhook_nonexistent_user` → 안전 처리
  - [ ] `test_webhook_invalid_callback_data` → 무시

**완료 기준**: 모든 정상/예외 시나리오의 테스트 통과

---

### 단계 4: 기존 인증 흐름 수정 및 이메일 서비스 교체
**대응 Sprint 태스크**: SP3-004

- [ ] `app/routers/auth.py` 수정:
  - [ ] `email_service` import 제거 (L24~L27)
  - [ ] `telegram_service` import 추가
  - [ ] `register()` 함수에서:
    - `BackgroundTasks` 매개변수 제거 (더 이상 불필요)
    - `background_tasks.add_task(send_registration_request_to_admin, ...)` 제거 (L86~L91)
    - 거절된 유저(`rejected_at` 설정됨) 재가입 시 기존 레코드 덮어쓰기 로직 추가
    - `try/await telegram.send_registration_alert(db_user)` 추가
  - [ ] `login()` 함수에 거절 상태 체크 추가:
    - `user.rejected_at`이 설정되어 있으면 403 + "계정이 거절되었습니다. 재가입해 주세요." 반환
  - [ ] `GET /approve/{user_id}` 엔드포인트 **전체 제거** (L143~L200)
  - [ ] `_html_result_page()` 헬퍼 함수 **제거** (L220~L271)
  - [ ] `HTMLResponse`, `send_approval_notification_to_user` import 제거
- [ ] `app/main.py` lifespan 수정:
  - [ ] Startup: `set_webhook()` 호출 추가 (TELEGRAM_BOT_TOKEN이 설정된 경우에만)
  - [ ] Shutdown: `delete_webhook()` 호출 추가
- [ ] `tests/test_auth.py` 수정:
  - [ ] `email_service` 모킹을 `telegram_service` 모킹으로 교체
  - [ ] `test_register_sends_telegram_alert` 추가
  - [ ] `test_register_succeeds_on_alert_failure` 추가
  - [ ] `test_login_rejected_user` 추가 (거절 유저 로그인 → 403)
  - [ ] `test_rejected_user_reregister` 추가 (거절 유저 재가입 → 덮어쓰기)
  - [ ] 기존 `test_auth_full_workflow` 버그 수정: `is_active=True`로 변경 후 로그인 성공을 검증하도록 수정

**완료 기준**: 기존 가입/로그인 테스트 + 신규 텔레그램 연동 테스트 모두 통과

---

### 단계 5: 정리, 검증, 문서 업데이트
**대응 Sprint 태스크**: SP3-005

- [ ] `app/services/email_service.py` 파일 삭제 (253줄)
- [ ] `.env`에서 SMTP 관련 환경 변수는 유지 (삭제하지 않음 — 향후 별도 정리)
- [ ] 전체 테스트 실행 확인: `pytest`
- [ ] E2E 통합 테스트 수행 (수동):
  - [ ] 가입 → 텔레그램 알림 도착 확인
  - [ ] ✅ 승인 클릭 → DB `is_active=True` → 로그인 성공
  - [ ] ❌ 거절 클릭 → DB `rejected_at` 설정 → 로그인 차단 확인 → 재가입 가능 확인
  - [ ] 텔레그램 API 장애 시뮬레이션 → 가입만 성공, 알림 누락
- [ ] 문서 업데이트:
  - [ ] `design_docs/sprint_board.md` — 해당 태스크 완료 처리
  - [ ] `design_docs/development_log.md` — 작업 내역 기록
  - [ ] `README.md` — 텔레그램 봇 설정 안내 추가

**완료 기준**: E2E 테스트 전 시나리오 통과, `pytest` 전체 통과, 문서 갱신 완료

---

## 3. 작업 순서 의존성

```
단계 1 (환경 설정)
  │
  ▼
단계 2 (텔레그램 서비스)
  │
  ▼
단계 3 (Webhook 라우터)  ← 단계 2에 의존
  │
  ▼
단계 4 (기존 코드 교체)  ← 단계 2, 3에 의존
  │
  ▼
단계 5 (정리 및 검증)   ← 전체 완료 후
```

> **원칙**: 각 단계 완료 후 테스트를 통과한 뒤에만 다음 단계로 진행.
> 기존 기능이 깨지지 않도록 점진적으로 전환한다.

---

## 4. 성공 기준 (Definition of Done)

| # | 기준 | 검증 방법 |
|---|------|----------|
| 1 | 관리자가 텔레그램 버튼 클릭 한 번으로 사용자를 승인할 수 있어야 함 | E2E 테스트 |
| 2 | 관리자가 텔레그램 버튼 클릭 한 번으로 사용자를 거절할 수 있어야 함 | E2E 테스트 |
| 3 | 승인 전까지는 로그인이 엄격히 차단되어야 함 (`is_active=False` → 403) | 단위 테스트 |
| 3-1 | 거절된 유저 로그인 시 "거절됨" 메시지가 반환되어야 함 | 단위 테스트 |
| 3-2 | 거절된 유저가 재가입 시 기존 레코드가 갱신되어 승인 대기 상태가 되어야 함 | 단위 테스트 |
| 4 | 관리자에게 승인/거절 결과가 실시간으로 피드백되어야 함 | E2E 테스트 |
| 5 | 모든 환경 설정은 `.env`를 통해 관리되어 보안성이 유지되어야 함 | 코드 리뷰 |
| 6 | 텔레그램 API 장애 시 가입 프로세스에 영향 없어야 함 | 단위 테스트 |
| 7 | Webhook 엔드포인트는 `secret_token` 검증으로 보호되어야 함 | 단위 테스트 |
| 8 | 모든 외부 API 호출이 `async/await`로 구현되어야 함 (Async Only 규칙) | 코드 리뷰 |
| 9 | 중복 콜백 처리 시 멱등성이 보장되어야 함 | 단위 테스트 |
| 10 | 기존 인증 관련 테스트가 모두 통과해야 함 | `pytest` |
| 11 | 기존 인증 없는 `GET /approve/{user_id}` 보안 취약점이 해소되어야 함 | 코드 리뷰 |

---

## 5. 예상 소요 시간

| 단계 | 예상 시간 |
|------|----------|
| 단계 1: 환경 설정 | 15분 |
| 단계 2: 텔레그램 서비스 | 45분 |
| 단계 3: Webhook 라우터 | 45분 |
| 단계 4: 기존 코드 교체 | 30분 |
| 단계 5: 정리 및 검증 | 30분 |
| **합계** | **약 2시간 45분** |
