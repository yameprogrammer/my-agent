# 잔여 작업 목록 (Remaining Work)

> **작성일**: 2026-07-10  
> **기준 커밋 계열**: Sprint 4-D 리뷰 수정 반영 후 (`code_review_2026-07-10.md` 정합)  
> **목적**: 다음 세션/에이전트가 바로 착수할 수 있도록 **미완 항목·우선순위·검증 수칙**을 고정한다.

관련 문서:
- [code_review_2026-07-10.md](./code_review_2026-07-10.md) — 리뷰 이슈 정본
- [sprint_board.md](./sprint_board.md) — 스프린트 태스크 트래커
- [development_log.md](./development_log.md) — 인수인계 로그

---

## 1. 현재 상태 요약

| 영역 | 상태 |
| :--- | :--- |
| Sprint 1–3 | Done |
| Sprint 4-A (WebSocket) | Done |
| Sprint 4-B/C (Streamlit + HITL) | 기능 MVP Done, 보드 상태 정리 여지 있음 |
| Sprint 4-D (리뷰 수정 WP-A~E) | **Done** (Issue 9·10·14·17 등 일부 후속) |
| Sprint 5 (Termux 배포) | **To Do** |

로컬 데모 경로(가입 승인 → 프로젝트/설정 → 집필 스트림 → 승인 저장)는 동작 가능한 수준이다.  
**외부 공개·폰 서버 상시 운용 전**에는 아래 P0/P1을 처리하는 것을 권장한다.

---

## 2. 우선순위 백로그

### P0 — Sprint 5 진입 전 권장

#### RW-01. 프로젝트 API 키 at-rest 암호화 (Review Issue 9) ✅ Done
- **문제**: `Project.api_key_override` 가 PostgreSQL에 평문 저장. DB/백업 유출 시 사용자 LLM 키 노출.
- **현재**: `API_KEY_ENCRYPTION_SECRET` 설정 슬롯만 존재 (`app/core/config.py`).
- **작업**:
  1. Fernet(또는 동등)으로 저장 시 암호화, 로드 시 복호화
  2. 기존 평문 행 마이그레이션(감지 후 암호화 재저장)
  3. 응답 마스킹(`has_api_key`) 유지
- **주요 파일**: `app/models.py`, `app/routers/project.py`, `app/core/config.py`, `app/services/llm_factory.py`
- **검증**: 키 저장 후 DB 원문이 ciphertext; LLM 호출은 정상; 시크릿 미설정 시 명확한 실패/경고 정책 문서화

#### RW-02. WebSocket JWT 전달 방식 개선 (Review Issue 10) ✅ Done
- **문제**: `?token=` 쿼리 파라미터 — 프록시/ngrok/Cloudflare/액세스 로그에 토큰 남을 수 있음.
- **작업 후보**:
  - 연결 후 첫 메시지로 `{ "action": "auth", "token": "..." }` 인증, 또는
  - `Sec-WebSocket-Protocol` 서브프로토콜에 short-lived ticket
- **주요 파일**: `app/routers/websocket.py`, `ui/monitor_view.py`
- **검증**: 유효 토큰 연결, 무효/비활성 거부, UI 모니터 정상 스트림

#### RW-03. 기존 WorldSetting 임베딩 백필 ✅ Done

---

### P1 — 안정성·테스트

#### RW-04. WebSocket ConnectionManager / 동시 쓰기 직렬화 (Review Issue 17) ✅ Done

#### RW-05. Streamlit 모니터 UX 보강 (Review Issue 14) ✅ Done

#### RW-06. 텔레그램 웹훅 승인/거절 E2E 테스트 (Review Issue 5 잔여) ✅ Done

#### RW-07. Episode outline UI 연동 ✅ Done

---

### P2 — 제품 백로그 (product_spec)

Sprint 4 MVP 범위를 넘는 항목. 완료 전 Writing View “완성” 표기 금지.

| ID | 항목 |
| :--- | :--- |
| RW-08 | AI 제안 ↔ 사용자 피드백 대조 편집기 |
| RW-09 | 인터랙티브 플롯 맵 / 씬 타임라인 |
| RW-10 | 회차 긴장도·전개 속도 UI 컨트롤러 (WS start 파라미터 연동) |
| RW-11 | Content 버전 히스토리 조회·롤백 UI |
| RW-12 | 씬 단위 진행 바 / 스트림 본문 인라인 수동 수정 |

상세 UX: [product_spec.md](./product_spec.md)

---

### P3 — Sprint 5 배포·운영

보드 태스크 **5-A / 5-B** 와 동일. 코드 P0(RW-01~03) 이후 착수 권장.

| ID | 항목 | 보드 |
| :--- | :--- | :--- |
| RW-13 | PM2 프로세스 관리 (API + Streamlit), 자동 재시작, 로그 로테이션 | 5-A |
| RW-14 | Nginx 리버스 프록시, 보안 헤더 | 5-A |
| RW-15 | Cloudflare Tunnel (또는 Tailscale) HTTPS 외부 접속 | 5-B |
| RW-16 | `pg_dump` 주기 백업 + 보관 정책 | 5-B |
| RW-17 | docker-compose/환경 기본 비밀번호·시크릿 프로덕션 분리 | 5-B |
| RW-18 | 장시간 구동 스트레스 테스트 체크리스트 | 5-B |

아키텍처 참고: [tech_stack.md](./tech_stack.md)

---

## 3. 운영 체크리스트 (배포 시 필수)

코드 작업과 별도로, 기동 전 확인:

| 항목 | 요구 |
| :--- | :--- |
| `ENVIRONMENT` | 프로덕션은 `production` |
| `JWT_SECRET` | **기본값 금지** — production 에서 기본값이면 기동 거부 |
| `TELEGRAM_BOT_TOKEN` / `ADMIN_TELEGRAM_CHAT_ID` | 승인 플로우 사용 시 설정 |
| `TELEGRAM_WEBHOOK_SECRET` | **8자 이상** — 미충족 시 set_webhook 스킵 (fail-closed) |
| `OPENAI_API_KEY` | 시맨틱 RAG·임베딩 사용 시 필요 (없으면 키워드 RAG만) |
| `DATABASE_URL` | 프로덕션 자격증명, 기본 `postgres/password` 사용 금지 |
| `BASE_URL` | 웹훅 등록용 공개 HTTPS URL |

---

## 4. 권장 작업 순서

```
RW-01 (API 키 암호화)
  → RW-02 (WS 토큰)
  → RW-03 (임베딩 백필)
  → RW-04 / RW-06 (동시성·텔레그램 E2E)
  → RW-05 / RW-07 (UI 폴리시)
  → Sprint 5 (RW-13~18)
  → product_spec 고급 UX (RW-08~12)  // 병행 가능, 배포와 독립
```

---

## 5. 보드 반영 가이드

다음 세션 시작 시:

1. 본 문서에서 착수할 **RW-ID** 선택
2. `sprint_board.md` 에 해당 태스크를 In Progress 로 옮기거나 Sprint 5 하위에 마이크로 태스크 추가
3. 완료 시 `development_log.md` 에 로그 + 본 문서 해당 항목에 `✅ Done` 표시
4. 리뷰 이슈와 대응되는 항목은 `code_review_2026-07-10.md` Status 도 `resolved` 로 동기화

---

## 6. 오늘(2026-07-10) 완료분 (참고)

- 전체 코드베이스 리뷰 문서화
- Sprint 4-D: 에이전트 루프(A1), HITL draft, RAG 임베딩, 인증 테스트, WS is_active, health 503, JWT/webhook 가드, requirements, outline 스키마 등
- pytest: 28 passed / 1 skipped (리뷰 수정 시점 기준)

이 문서는 **미완 작업만** 추적한다. 완료 이슈 상세는 `code_review_2026-07-10.md` 를 본다.
