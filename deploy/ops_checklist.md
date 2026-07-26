# 운영 · 보안 · 스트레스 체크리스트 (IMP-18 ~ IMP-22)

배포 전·후 수동 확인용. 코드 가드와 병행한다.

---

## IMP-18 — 초기 관리자 비밀번호

- [ ] `INITIAL_ADMIN_PASSWORD` 가 문서 예시/기본 약값과 다름
- [ ] `ENVIRONMENT=production` 에서 약한 비밀번호로 기동 시 **거부** (`app/core/config.py`)
- [ ] 최초 로그인 후 관리자 비밀번호 변경 계획 (또는 시드 후 즉시 변경)

## IMP-19 — JWT · 브라우저 저장

- [ ] 개인 홈서버: `ACCESS_TOKEN_EXPIRE_MINUTES` 기본 7일 + localStorage 수용 가능
- [ ] 공개 서비스 검토 시: 만료 단축, HTTPS 강제, XSS 점검, (향후) refresh token
- [ ] 로그아웃 시 토큰 삭제 UI 동작 확인

## IMP-20 — 장시간 구동 스트레스

| 항목 | 확인 방법 |
| :--- | :--- |
| 동시 WebSocket | 2+ 브라우저 탭에서 집필 스트림 |
| LLM 타임아웃 | 느린 모델/잘못된 키로 실패 시 UI 에러·재시도 |
| 디스크 | `deploy/logs`, Postgres 데이터, `backups/` 용량 |
| 메모리 | PM2 `max_memory_restart` 또는 Docker 제한 |
| 재시작 | kill 후 자동 재기동 + `/health` |
| 백업 리허설 | `backup_pg.sh` → 스테이징 `restore_pg.sh` |

## IMP-21 — health 실패 알림

- [ ] cron: `deploy/scripts/healthcheck_notify.py` (5분 간격 권장)
- [ ] `TELEGRAM_BOT_TOKEN` + `ADMIN_TELEGRAM_CHAT_ID` 설정
- [ ] 앱 중지 후 알림 1회 수신 · 복구 알림 수신

## IMP-22 — Alembic

현재는 `init_db()` + soft `ALTER ... IF NOT EXISTS` 로 스키마 확장.
다음 조건이면 Alembic 정식 도입을 검토한다.

- 다중 환경(스테이징/프로덕션) 동시 스키마 버전 필요
- 되돌리기(downgrade) 가 필요한 destructive 변경
- soft-migrate 만으로 위험한 rename/type change

도입 시: `alembic init`, `env.py` 에 async SQLAlchemy URL, CI 에서 `upgrade head`.

---

## 프로덕션 시크릿 빠른 점검

```bash
# 기본 JWT 로 production 기동되면 안 됨
ENVIRONMENT=production JWT_SECRET=change-me-in-production ...  # expect refuse

python scripts/check_no_secrets.py
```
