# 상세 설계서: 텔레그램 봇 기반 관리자 승인 시스템

> **문서 버전**: v2.1  
> **최종 갱신일**: 2026-07-10  
> **관련 요구사항**: `auth_telegram_integration.md` v2.1

---

## 1. 아키텍처 개요

기존의 SMTP 이메일 발송 체계를 텔레그램 봇 API로 대체하여, 관리자가 실시간 푸시 알림을 받고 챗봇 인터페이스 내에서 즉시 사용자를 승인/거절하는 구조로 설계한다.

### 1.1 컴포넌트 다이어그램

```
┌──────────┐     ┌──────────────┐     ┌────────────────────┐     ┌───────────┐
│  User    │────▶│  FastAPI      │────▶│  Telegram Bot API  │────▶│  Admin    │
│ (Client) │     │  Server       │     │  (api.telegram.org)│     │(Telegram) │
└──────────┘     └──────┬───────┘     └────────┬───────────┘     └─────┬─────┘
                        │                       │                       │
                        │◀──── Webhook ◀────────┘◀──── Button Click ────┘
                        │
                 ┌──────▼───────┐
                 │ PostgreSQL   │
                 │ (asyncpg)    │
                 └──────────────┘
```

---

## 2. 데이터 흐름 (Sequence Diagram)

### 2.1 가입 요청 및 알림 흐름

```
User                    FastAPI Server              Telegram Bot API         Admin
 │                           │                            │                    │
 │  POST /auth/register      │                            │                    │
 │──────────────────────────▶│                            │                    │
 │                           │  INSERT User(is_active=F)  │                    │
 │                           │───────── DB ───────────▶   │                    │
 │                           │                            │                    │
 │                           │  sendMessage(InlineKeyboard)│                    │
 │                           │───────────────────────────▶│                    │
 │                           │                            │  Push Notification │
 │  201 Created              │                            │──────────────────▶│
 │◀──────────────────────────│                            │                    │
```

> **중요**: 텔레그램 알림 전송 실패 시에도 가입 응답은 `201 Created` 반환 (best-effort 알림)

### 2.2 승인/거절 처리 흐름

```
Admin              Telegram Bot API         FastAPI Server                    DB
 │                      │                        │                            │
 │  Click [✅ 승인]      │                        │                            │
 │─────────────────────▶│                        │                            │
 │                      │  POST /auth/telegram/  │                            │
 │                      │  webhook               │                            │
 │                      │  (X-Telegram-Bot-Api-  │                            │
 │                      │   Secret-Token: xxx)   │                            │
 │                      │───────────────────────▶│                            │
 │                      │                        │  1. Verify secret_token    │
 │                      │                        │  2. Verify from.id ==     │
 │                      │                        │     ADMIN_CHAT_ID         │
 │                      │                        │  3. Parse callback_data   │
 │                      │                        │  4. UPDATE user status    │
 │                      │                        │───────────────────────────▶│
 │                      │                        │                            │
 │                      │  answerCallbackQuery    │                            │
 │                      │◀───────────────────────│                            │
 │                      │  editMessageText       │                            │
 │                      │◀───────────────────────│                            │
 │  "✅ 승인 완료"        │                        │                            │
 │◀─────────────────────│                        │                            │
```

---

## 3. 상세 설계

### 3.1 User 모델 변경 (`app/models.py`)

거절 이력 관리를 위해 `User` 모델에 필드를 추가한다.

```python
class User(SQLModel, table=True):
    # ... 기존 필드 유지 ...
    
    # 거절 이력 관리 (신규 추가)
    rejected_at: Optional[datetime] = Field(default=None, nullable=True)  # 거절된 시각, None이면 미거절
```

> **상태 조합 해석**:
> | `is_active` | `rejected_at` | 상태 |
> |-------------|---------------|------|
> | `False` | `None` | 승인 대기 중 |
> | `True` | `None` | 승인 완료 (정상 사용자) |
> | `False` | `datetime` | 거절됨 |

### 3.2 환경 변수 확장 (`app/core/config.py`)

현재 `Settings` 클래스에 다음 필드를 추가한다. 기존 SMTP 필드는 `Optional`로 이미 선언되어 있으므로 변경 불필요.

```python
class Settings(BaseSettings):
    # ... 기존 필드 유지 ...
    
    # 텔레그램 봇 관련 (신규 추가)
    TELEGRAM_BOT_TOKEN: str = ""
    ADMIN_TELEGRAM_CHAT_ID: str = ""
    TELEGRAM_WEBHOOK_SECRET: str = ""  # Webhook 검증용 시크릿
    # BASE_URL: str = "http://localhost:8000"  ← 이미 존재 (Webhook URL 구성에 활용)
```

> **주의**: `TELEGRAM_BOT_TOKEN`이 빈 문자열이면 텔레그램 관련 기능을 비활성화하는 가드 로직을 서비스 계층에서 처리한다.

### 3.3 Telegram Bot 서비스 모듈 (`app/services/telegram_service.py`)

#### 클래스 설계

```python
import logging
import httpx
from typing import Optional

logger = logging.getLogger(__name__)


class TelegramBotService:
    """텔레그램 Bot API를 통한 관리자 알림 서비스.
    
    모든 외부 API 호출은 async/await + httpx.AsyncClient 패턴으로 구현하여
    프로젝트의 Async Only 규칙을 준수한다.
    """
    
    BASE_URL = "https://api.telegram.org/bot{token}"
    TIMEOUT = 10.0  # 초
    MAX_RETRIES = 2
    
    def __init__(self, token: str, admin_chat_id: str):
        self.token = token
        self.admin_chat_id = admin_chat_id
        self.api_url = self.BASE_URL.format(token=token)
```

#### 핵심 메서드

| 메서드 | 설명 | 반환 |
|--------|------|------|
| `async _request(method, payload)` | 내부 API 호출 헬퍼 (타임아웃, 재시도, 로깅) | `dict \| None` |
| `async send_registration_alert(user)` | 가입 알림 + 인라인 키보드 발송 | `None` |
| `async send_message(chat_id, text)` | 일반 텍스트 메시지 발송 | `dict \| None` |
| `async edit_message(chat_id, message_id, text)` | 기존 메시지 텍스트 교체 (버튼 제거) | `dict \| None` |
| `async answer_callback_query(callback_query_id, text)` | 콜백 쿼리 응답 (토스트 알림) | `dict \| None` |
| `async set_webhook(url, secret_token)` | Webhook URL 등록 | `dict \| None` |
| `async delete_webhook()` | Webhook 해제 | `dict \| None` |

#### 알림 메시지 포맷

```
📋 새로운 가입 요청

👤 사용자명: {username}
📧 이메일: {email or "미입력"}
🆔 ID: #{user_id}
🕐 요청 시각: {created_at} (KST)

처리해 주세요:
```

인라인 키보드:
```json
{
  "inline_keyboard": [[
    {"text": "✅ 승인", "callback_data": "approve_{user_id}"},
    {"text": "❌ 거절", "callback_data": "reject_{user_id}"}
  ]]
}
```

#### 에러 핸들링 전략

```python
async def _request(self, method: str, payload: dict) -> dict | None:
    """내부 API 호출 헬퍼. 실패 시 None 반환 (best-effort).
    
    가입 프로세스의 안정성을 위해 예외를 호출자에게 전파하지 않는다.
    """
    url = f"{self.api_url}/{method}"
    for attempt in range(self.MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                return resp.json()
        except (httpx.HTTPError, httpx.TimeoutException) as e:
            logger.warning(
                "Telegram API 호출 실패 (시도 %d/%d): %s %s",
                attempt + 1, self.MAX_RETRIES + 1, method, e
            )
    logger.error("Telegram API 최종 실패: %s", method)
    return None
```

### 3.4 Webhook 콜백 라우터 (`app/routers/telegram.py`)

#### 엔드포인트 설계

```python
from fastapi import APIRouter, Request, HTTPException, Depends, status
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

from app.core.config import settings
from app.core.database import get_async_session
from app.models import User
from app.services.telegram_service import TelegramBotService

router = APIRouter(prefix="/auth/telegram", tags=["Telegram"])


@router.post("/webhook")
async def telegram_webhook(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
):
    """텔레그램 봇의 Webhook을 처리한다.
    
    보안 검증:
    1. X-Telegram-Bot-Api-Secret-Token 헤더 확인
    2. callback_query.from.id와 ADMIN_TELEGRAM_CHAT_ID 대조
    3. user_id의 존재 및 미승인 상태 확인
    """
```

#### 콜백 처리 로직 (의사코드)

```
1. 요청 헤더에서 secret_token 추출 및 검증
   └─ 불일치 시: 403 Forbidden 반환

2. 요청 본문에서 callback_query 추출
   └─ callback_query 없음: 200 OK 반환 (일반 메시지 등 무시)

3. callback_query.from.id 를 str로 변환 후 ADMIN_TELEGRAM_CHAT_ID 비교
   └─ 불일치 시: answerCallbackQuery("⛔ 권한이 없습니다") 후 200 OK

4. callback_data 파싱 → (action, user_id)
   └─ action: "approve" | "reject"
   └─ 파싱 실패: 200 OK (무시)

5. DB에서 user_id로 User 조회 (select(User).where(User.id == user_id))
   └─ 미존재 또는 이미 처리됨 (is_active=True 또는 rejected_at이 설정됨):
      answerCallbackQuery("⚠️ 이미 처리된 요청입니다")
      editMessageText("⚠️ 이미 처리된 요청입니다.")
      200 OK 반환

6-A. action == "approve":
   └─ User.is_active = True → session.add(user) → await session.commit()
   └─ answerCallbackQuery("✅ 승인 완료!")
   └─ editMessageText("✅ {username} 승인 완료 ({timestamp})")

6-B. action == "reject":
   └─ User.rejected_at = datetime.utcnow() → session.add(user) → await session.commit()
   └─ answerCallbackQuery("❌ 거절 완료!")
   └─ editMessageText("❌ {username} 거절 완료 ({timestamp})")

7. 200 OK 반환 (Telegram은 항상 200을 기대)
```

> **멱등성 보장**: 이미 승인된(`is_active=True`) 유저나 이미 거절된(`rejected_at` 설정된) 유저에 대한 중복 콜백은 안전하게 무시

### 3.5 기존 인증 라우터 수정 (`app/routers/auth.py`)

#### 변경 전 (현재 코드 L24~L27, L86~L91, L143~L200, L220~L271)

```python
# === import (제거 대상) ===
from app.services.email_service import (
    send_registration_request_to_admin,
    send_approval_notification_to_user,
)

# === register 내 이메일 발송 (교체 대상) ===
background_tasks.add_task(
    send_registration_request_to_admin,
    username=db_user.username,
    user_email=db_user.email,
    user_id=db_user.id,
)

# === approve 엔드포인트 (제거 대상) ===
@router.get("/approve/{user_id}", ...)
async def approve_user(user_id: int, ...):
    ...

# === HTML 헬퍼 (제거 대상) ===
def _html_result_page(title, message, success):
    ...
```

#### 변경 후

```python
# === import (교체) ===
from app.services.telegram_service import TelegramBotService

# === register 내 텔레그램 알림 ===
# BackgroundTasks 대신 직접 await (httpx는 네이티브 async이므로)

# 1. 거절된 유저가 재가입하는 경우 처리
statement = select(User).where(User.username == user_in.username)
existing = (await session.execute(statement)).scalar_one_or_none()
if existing and existing.rejected_at:
    # 거절된 유저의 재가입: 기존 레코드 덮어쓰기
    existing.hashed_password = hash_password(user_in.password)
    existing.email = user_in.email
    existing.rejected_at = None  # 거절 상태 초기화
    db_user = existing
else:
    # 신규 가입 (기존 로직)
    ...

# 2. 텔레그램 알림
try:
    telegram = TelegramBotService(
        settings.TELEGRAM_BOT_TOKEN,
        settings.ADMIN_TELEGRAM_CHAT_ID,
    )
    await telegram.send_registration_alert(db_user)
except Exception:
    logger.warning("텔레그램 관리자 알림 전송 실패 (가입은 정상 처리됨)")

# === login 내 거절 상태 체크 추가 ===
if user.rejected_at:
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="계정이 거절되었습니다. 재가입해 주세요.",
    )

# GET /approve/{user_id} 엔드포인트 → 삭제
# _html_result_page() 헬퍼 → 삭제
# send_approval_notification_to_user import → 삭제
```

> **설계 결정**: 이메일은 `BackgroundTasks` + `run_in_executor`로 호출했으나, `httpx.AsyncClient`는 네이티브 비동기이므로 직접 `await`로 호출한다. `send_registration_alert` 내부에서 에러를 삼키므로 호출부의 `try/except`는 추가 안전장치 역할.

### 3.6 Webhook 라이프사이클 (`app/main.py`)

현재 lifespan에 `init_db()` 호출이 있다. 여기에 Webhook 등록/해제를 추가한다.

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    
    # Telegram Webhook 등록 (토큰이 설정된 경우에만)
    telegram = None
    if settings.TELEGRAM_BOT_TOKEN:
        telegram = TelegramBotService(
            settings.TELEGRAM_BOT_TOKEN,
            settings.ADMIN_TELEGRAM_CHAT_ID,
        )
        webhook_url = f"{settings.BASE_URL}/auth/telegram/webhook"
        await telegram.set_webhook(webhook_url, settings.TELEGRAM_WEBHOOK_SECRET)
        logger.info("Telegram webhook 등록: %s", webhook_url)
    
    yield
    
    # Shutdown
    if telegram:
        await telegram.delete_webhook()
        logger.info("Telegram webhook 해제 완료")
```

### 3.7 라우터 등록 (`app/main.py`)

```python
from app.routers import auth, telegram  # conversations, project 등 기존 라우터도 유지

app.include_router(auth.router)
app.include_router(telegram.router)
# ... 기존 라우터들 ...
```

---

## 4. 영향도 분석 및 리스크 관리

### 4.1 영향 범위

| 구분 | 대상 | 변경 수준 | 상세 |
|------|------|----------|------|
| 수정 | `app/models.py` | 소 | `rejected_at` 필드 추가 |
| 수정 | `app/core/config.py` | 소 | 필드 3개 추가 |
| 수정 | `app/routers/auth.py` | 중 | email→telegram 교체, approve 엔드포인트 제거, 거절 재가입 로직, 로그인 거절 체크 |
| 수정 | `app/main.py` | 소 | 라우터 등록 + lifespan 확장 |
| 신규 | `app/services/telegram_service.py` | 대 | 전체 신규 (~120줄) |
| 신규 | `app/routers/telegram.py` | 대 | 전체 신규 (~100줄) |
| 신규 | `tests/test_telegram.py` | 대 | 전체 신규 (~250줄) |
| 삭제 | `app/services/email_service.py` | - | 파일 삭제 (253줄) |
| 수정 | `tests/test_auth.py` | 중 | email_service 모킹 → telegram_service 모킹 교체 + 기존 버그 수정 |

### 4.2 리스크 및 대응

| 리스크 | 영향도 | 대응 방안 |
|--------|--------|----------|
| 텔레그램 API 장애/지연 | 중 | 알림은 best-effort로 처리, 가입 프로세스와 분리 |
| Webhook 외부 노출 필요 | 고 | 로컬: Cloudflare Tunnel / Ngrok. 프로덕션: `BASE_URL`(이미 존재)에 도메인 지정 |
| Callback 재전송/중복 호출 | 중 | 멱등성 보장 로직 (is_active 확인 + 존재 여부 확인) |
| 관리자 chat_id 변경 | 저 | `.env` 수정 + 서버 재시작 |
| `test_auth.py` 깨짐 | 중 | email_service 모킹을 telegram_service 모킹으로 교체 |
| 거절된 유저 레코드 누적 | 저 | 거절 레코드가 DB에 남지만, 재가입 시 덮어쓰기로 무한 누적 방지 |

---

## 5. 검증 시나리오

### 5.1 정상 케이스

| # | 시나리오 | 기대 결과 |
|---|---------|----------|
| 1 | 신규 유저 가입 | 관리자 텔레그램으로 즉시 인라인 키보드 포함 알림 도착 |
| 2 | [✅ 승인] 클릭 | DB `is_active=True`, 관리자 메시지 "✅ 승인 완료"로 변경 |
| 3 | [❌ 거절] 클릭 | `rejected_at` 설정, 관리자 메시지 "❌ 거절 완료"로 변경 |
| 4 | 승인된 유저 로그인 | 정상 JWT 토큰 발급 (`POST /auth/login`) |
| 5 | 거절된 유저 로그인 | 403 "계정이 거절되었습니다. 재가입해 주세요." |
| 6 | 거절 후 동일 username 재가입 | 기존 레코드 덮어쓰기 (`rejected_at=None`, 비밀번호 갱신) 후 승인 대기 |

### 5.2 예외 케이스

| # | 시나리오 | 기대 결과 |
|---|---------|----------|
| 7 | 텔레그램 API 장애 중 가입 | 가입은 성공(201), 알림만 누락 (로그 경고) |
| 8 | 이미 승인된 유저의 승인 버튼 재클릭 | "⚠️ 이미 처리된 요청" 메시지 표시 |
| 9 | 이미 거절된 유저의 거절 버튼 재클릭 | "⚠️ 이미 처리된 요청" 메시지 표시 |
| 10 | 잘못된 secret_token으로 webhook 호출 | 403 Forbidden |
| 11 | 비관리자가 버튼 클릭 (다른 텔레그램 유저) | "⛔ 권한 없음" 응답, DB 무변경 |
| 12 | 존재하지 않는 user_id의 콜백 | "⚠️ 이미 처리된 요청" 메시지 표시 |

### 5.3 단위 테스트 범위

```
tests/test_telegram.py
├── test_send_registration_alert_success    # 정상 알림 발송 (httpx mock)
├── test_send_registration_alert_api_failure # API 실패 시 예외 미전파
├── test_webhook_approve_success            # 정상 승인 콜백 처리
├── test_webhook_reject_success             # 정상 거절 콜백 (rejected_at 설정 확인)
├── test_webhook_invalid_secret             # 잘못된 시크릿 → 403
├── test_webhook_unauthorized_user          # 비관리자 → 무시
├── test_webhook_already_approved           # 승인된 유저 재콜백 → 멱등 처리
├── test_webhook_already_rejected           # 거절된 유저 재콜백 → 멱등 처리
├── test_webhook_nonexistent_user           # 존재하지 않는 유저 → 안전 처리
└── test_webhook_invalid_callback_data      # 잘못된 데이터 포맷 → 무시

tests/test_auth.py (수정 — 기존 버그 함께 수정)
├── test_register_sends_telegram_alert      # 가입 시 텔레그램 알림 호출 확인
├── test_register_succeeds_on_alert_failure # 알림 실패 시에도 가입 성공
├── test_login_rejected_user               # 거절된 유저 로그인 → 403 + 거절 메시지
├── test_rejected_user_reregister           # 거절된 유저 재가입 → 덮어쓰기 성공
└── test_auth_full_workflow_fix             # 기존 버그 수정: is_active=True 후 로그인 성공 확인
```

> **기존 버그 수정**: 현재 `test_auth.py`의 `test_auth_full_workflow`에서 `is_active=False` 상태로 로그인을 시도하여 200을 기대하는 버그가 있다. 이번 작업에서 함께 수정한다: 승인(`is_active=True`) 후 로그인 성공을 검증하는 흐름으로 변경.
