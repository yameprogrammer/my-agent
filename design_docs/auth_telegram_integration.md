# 요구사항 정의서: 관리자 승인 체계의 텔레그램 전환

> **문서 버전**: v2.1  
> **최종 갱신일**: 2026-07-10  
> **작성자**: Gemma4 → Claude Opus 4.6 (리뷰 및 보완)  
> **관련 Sprint**: Sprint 3 (SP3-001 ~ SP3-005)

---

## 1. 개요

현재의 이메일(SMTP) 기반 관리자 승인 시스템은 다음과 같은 문제점이 있다:

| 문제점 | 설명 |
|--------|------|
| 설정 번거로움 | SMTP 호스트/포트/인증 등 다수의 환경 변수 필요 |
| 낮은 실시간성 | 이메일 확인까지 수분~수시간 소요 |
| 스팸 분류 | 인증 이메일이 스팸으로 분류될 위험 |
| 보안 미비 | 현재 `GET /approve/{user_id}` 엔드포인트에 인증/인가 검증이 없음 — user_id를 알면 누구나 계정 활성화 가능 |

> **참고**: 현재 `email_service.py`는 `smtplib`를 `run_in_executor`로 래핑하여 비동기 패턴을 유지하고 있으나, `auth.py`에서는 `BackgroundTasks`를 통해 호출하고 있어 비동기 래핑의 이점이 제한적이다.

이를 해결하기 위해 **텔레그램 봇(Telegram Bot)**을 활용하여 관리자가 모바일 환경에서 즉각적으로 가입 요청을 확인하고 승인/거절할 수 있는 체계로 전환한다.

---

## 2. 핵심 요구사항

### 2.1 관리자 알림 (Admin Notification)

- **트리거**: 사용자가 `POST /auth/register`를 통해 회원가입 요청을 보냈을 때.
- **채널**: 설정된 관리자의 텔레그램 채팅방 (`ADMIN_TELEGRAM_CHAT_ID`).
- **알림 내용**:
  - 신규 가입자의 정보: **Username**, **Email**, **User ID**
  - 가입 요청 시간 (KST 기준)
  - 즉시 처리 가능한 **[✅ 승인]** 및 **[❌ 거절]** 인라인 버튼
- **비기능 요구사항**:
  - 텔레그램 API 호출은 반드시 `async/await` 패턴으로 구현 (`httpx.AsyncClient` 사용)
  - API 호출 실패 시 가입 자체는 정상 완료되어야 함 (알림 전송은 best-effort)

### 2.2 승인 프로세스 (Approval Process)

1. 관리자가 **[✅ 승인]** 버튼 클릭
2. 텔레그램 봇이 서버의 Webhook 엔드포인트 호출 (Callback Query)
3. 서버가 요청의 유효성 검증 (Telegram `X-Telegram-Bot-Api-Secret-Token` 헤더 확인)
4. `User.is_active = True`로 DB 업데이트
5. 관리자에게 처리 결과 알림 (`editMessageText`로 기존 버튼을 결과 메시지로 교체)

### 2.3 거절 프로세스 (Rejection Process)

1. 관리자가 **[❌ 거절]** 버튼 클릭
2. 텔레그램 봇이 서버의 Webhook 엔드포인트 호출 (Callback Query)
3. 서버가 요청의 유효성 검증
4. **거절 정책**: 해당 유저 레코드를 **삭제하지 않고** 거절 이력을 기록
   - `User.rejected_at = datetime.utcnow()` 설정 (거절 시각 기록)
   - `User.is_active`는 `False` 유지
   - 거절된 유저가 동일 username/email로 **재가입 시**: 기존 거절 레코드를 덮어쓰기 (비밀번호 갱신 + `rejected_at = None` 초기화)
5. 관리자에게 거절 처리 결과 알림 (`editMessageText`)

> **모델 변경 필요**: `User` 모델에 `rejected_at: Optional[datetime] = None` 필드 추가

### 2.4 사용자 알림 (User Notification)

- 관리자 승인/거절 시 사용자에게 **별도 알림을 보내지 않는다**
- 사용자는 로그인 시도를 통해 승인 여부를 직접 확인
- 기존 이메일 승인 알림(`send_approval_notification_to_user`)도 함께 제거
- 거절된 사용자가 로그인 시도 시: "계정이 거절되었습니다. 재가입해 주세요." 메시지 반환

### 2.5 보안 요구사항

| 항목 | 요구사항 |
|------|----------|
| 환경 변수 관리 | `TELEGRAM_BOT_TOKEN`, `ADMIN_TELEGRAM_CHAT_ID`, `TELEGRAM_WEBHOOK_SECRET` 은 `.env`에서만 관리 |
| Webhook 인증 | Telegram `setWebhook` 시 `secret_token` 파라미터 설정, 수신 시 `X-Telegram-Bot-Api-Secret-Token` 헤더와 대조 검증 |
| Callback 변조 방지 | `callback_data`에서 추출한 `user_id`가 실제 DB에 존재하고 미처리(`is_active=False` 이고 `rejected_at=None`) 상태인지 검증 |
| 관리자 검증 | Callback Query의 `from.id`가 `ADMIN_TELEGRAM_CHAT_ID`와 일치하는지 확인하여 비인가 사용자의 버튼 클릭 차단 |
| 기존 취약점 해소 | 현재 인증 없이 노출된 `GET /auth/approve/{user_id}` 엔드포인트를 **제거** |

### 2.6 에러 핸들링 및 복원력

- **텔레그램 API 호출 실패**: 
  - 가입 알림 전송 실패 시 로깅만 수행, 가입 프로세스는 정상 완료 (알림은 best-effort)
  - HTTP 타임아웃: 10초 제한
  - 재시도: 최대 2회 (단순 재시도)
- **Webhook Callback 처리 실패**:
  - 이미 처리된(중복) 콜백 요청에 대해 멱등성(idempotency) 보장
  - 존재하지 않는 `user_id` 콜백 시 관리자에게 "이미 처리된 요청" 안내 메시지 응답

---

## 3. 현재 코드베이스 영향도 분석

### 3.1 수정 대상 파일

| 파일 | 변경 내용 |
|------|----------|
| `app/models.py` | `User` 모델에 `rejected_at: Optional[datetime] = None` 필드 추가 |
| `app/core/config.py` | `TELEGRAM_BOT_TOKEN`, `ADMIN_TELEGRAM_CHAT_ID`, `TELEGRAM_WEBHOOK_SECRET` 필드 추가. SMTP 관련 필드에 `Optional` 유지 |
| `app/routers/auth.py` | `BackgroundTasks` + `send_registration_request_to_admin()` 호출을 `telegram_service` 호출로 교체. `GET /approve/{user_id}` 엔드포인트 및 `_html_result_page()` 헬퍼 제거. 거절된 유저 재가입 로직 추가. 로그인 시 거절 상태 체크 추가 |
| `app/main.py` | `telegram.router` 등록 추가. lifespan에 Webhook 등록/해제 로직 추가 |
| `requirements.txt` | 추가 패키지 불필요 (`httpx` 이미 포함) |
| `.env` | `TELEGRAM_BOT_TOKEN`, `ADMIN_TELEGRAM_CHAT_ID`, `TELEGRAM_WEBHOOK_SECRET` 추가 |

### 3.2 신규 생성 파일

| 파일 | 용도 |
|------|------|
| `app/services/telegram_service.py` | 텔레그램 Bot API 호출 서비스 모듈 |
| `app/routers/telegram.py` | Webhook 콜백 처리 라우터 |
| `tests/test_telegram.py` | 텔레그램 서비스/라우터 단위 테스트 |

### 3.3 제거/폐기 대상

| 파일/코드 | 처리 방식 |
|-----------|----------|
| `app/services/email_service.py` | 파일 삭제 |
| `app/routers/auth.py` 내 `GET /approve/{user_id}` | 엔드포인트 제거 |
| `app/routers/auth.py` 내 `_html_result_page()` | 헬퍼 함수 제거 |
| `app/routers/auth.py` 내 `email_service` import | import 제거 |
| `app/core/config.py` 내 SMTP 관련 필드 | Phase 1에서는 `Optional` 유지 (기존과 동일), 향후 별도 정리 |
| `.env` 내 SMTP 관련 환경 변수 | 유지 (향후 별도 정리) |

---

## 4. 기대 효과

| 영역 | 개선 내용 |
|------|----------|
| **운영 효율성** | SMTP 서버 설정 및 유지보수 비용 제거 |
| **반응 속도** | 이메일 확인 과정 없이 푸시 알림을 통해 즉각적인 유저 승인 가능 |
| **UX 개선** | 복잡한 링크 클릭-브라우저 이동 과정 없이 챗봇 인터페이스 내에서 모든 관리 수행 |
| **보안 강화** | Webhook secret 검증 + 관리자 ID 검증 이중 보안 체계 (기존 인증 없는 approve 엔드포인트 제거) |
| **코드 품질** | `smtplib` + `run_in_executor` 래핑 → 네이티브 `async httpx` 호출로 전환 |

---

## 5. 범위 외 (Out of Scope)

본 스프린트에서는 다음 사항을 **포함하지 않는다**:

- 사용자별 텔레그램 연동 (사용자→봇 알림)
- 다중 관리자 지원 (관리자 그룹 채팅 등)
- 텔레그램 봇 명령어 기반 관리 인터페이스 (`/list_pending` 등)
- 사용자 대상 승인/거절 알림 (사용자가 직접 로그인하여 확인)
- User 모델의 `is_admin` 필드를 활용한 권한 체계 개선 (별도 작업으로 분리)
