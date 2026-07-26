# Deploy Runbook (Sprint 5 / IMP-04 · IMP-05)

Termux·홈서버·일반 Linux 호스트에서 **FastAPI + 빌드된 SPA** 를 상시 운용하기 위한 샘플 설정입니다.  
프로덕션 시크릿은 **절대 git 에 넣지 마십시오.** `.env` / 환경변수만 사용합니다.

관련: [post_mvp_review_and_backlog](../design_docs/post_mvp_review_and_backlog_2026-07-26.md) § IMP-04, IMP-05 · [docker-compose.prod.yml](../docker-compose.prod.yml)

---

## 1. 사전 조건

| 항목 | 요구 |
| :--- | :--- |
| `ENVIRONMENT` | `production` |
| `JWT_SECRET` | 기본값 금지 |
| `API_KEY_ENCRYPTION_SECRET` | Fernet 키 (미설정 시 기동 거부) |
| `INITIAL_ADMIN_PASSWORD` | 약한 기본값 금지 |
| `DATABASE_URL` / `POSTGRES_PASSWORD` | 기본 `password` 금지 |
| SPA 빌드 | `cd frontend && npm run build` → `frontend/dist` |

Fernet 키 생성:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

## 2. 옵션 A — Docker Compose (권장 홈서버)

```bash
export POSTGRES_PASSWORD='...'
export JWT_SECRET='...'
export INITIAL_ADMIN_PASSWORD='...'
export API_KEY_ENCRYPTION_SECRET='...'
# 선택: TELEGRAM_*, OPENAI_*, BASE_URL, ...

docker compose -f docker-compose.prod.yml up -d --build
curl -sf http://127.0.0.1:8080/health
```

---

## 3. 옵션 B — PM2 + Uvicorn (IMP-04)

1. venv 및 의존성 설치, `frontend` 빌드 완료.
2. 저장소 루트에 `.env` 배치 (git ignore).
3. `deploy/ecosystem.config.cjs` 의 `cwd` / 파이썬 경로를 환경에 맞게 수정.
4. 기동:

```bash
npm install -g pm2   # 또는 로컬
pm2 start deploy/ecosystem.config.cjs
pm2 save
pm2 logs novel-agent
```

로그: `deploy/logs/` (로테이션은 PM2 max_size 설정 참고).

---

## 4. Nginx 리버스 프록시 (IMP-04)

샘플: `deploy/nginx-novel-agent.conf`

- 업스트림 `127.0.0.1:8080`
- 보안 헤더, WebSocket `/ws` 업그레이드
- (선택) TLS 는 Cloudflare Tunnel 또는 certbot

```bash
sudo cp deploy/nginx-novel-agent.conf /etc/nginx/sites-available/novel-agent
sudo ln -sf /etc/nginx/sites-available/novel-agent /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

---

## 5. Cloudflare Tunnel (IMP-05)

샘플: `deploy/cloudflared-config.example.yml`

1. [Zero Trust](https://one.dash.cloudflare.com/) 에서 Tunnel 생성 후 토큰/자격증명 확보.
2. `cloudflared tunnel run --token $TUNNEL_TOKEN` 또는 config 파일 사용.
3. `BASE_URL` 을 공개 HTTPS 로 맞추고 텔레그램 웹훅 재등록.

Tailscale 로 내부망만 노출하는 경우 Tunnel 생략 가능.

---

## 6. DB 백업 (IMP-05)

| 스크립트 | 용도 |
| :--- | :--- |
| `deploy/scripts/backup_pg.sh` | `pg_dump` → `backups/` (`.gitignore`) |
| `deploy/scripts/restore_pg.sh` | 덤프 복원 리허설 |
| `deploy/scripts/healthcheck_notify.py` | `/health` 실패 시 텔레그램 (cron) |

보관 정책 예: 일 1회, 로컬 7일 보관 후 삭제.  
**백업 파일에 API 키 JSON export 가 섞이지 않도록** admin export 기본 `include_secrets=false` 유지.

cron 예:

```cron
0 3 * * * /path/to/my-agent/deploy/scripts/backup_pg.sh >> /path/to/my-agent/deploy/logs/backup.log 2>&1
*/5 * * * * cd /path/to/my-agent && .venv/bin/python deploy/scripts/healthcheck_notify.py
```

---

## 7. 기동 후 검증 체크리스트

- [ ] `GET /health` → 200, DB ok
- [ ] 정적 SPA 로드 (로그인 화면)
- [ ] production 기본 JWT / 약한 admin / 평문 crypto → **기동 거부** 확인
- [ ] 프로세스 강제 종료 후 PM2/Docker 재기동
- [ ] (외부) HTTPS 로 로그인·WebSocket 집필 스트림
- [ ] `backup_pg.sh` 실행 후 `restore_pg.sh` 스테이징 리허설

---

## 8. 스트레스·운영 (IMP-20)

상세: [ops_checklist.md](./ops_checklist.md)
