# 프로젝트 개발 및 보안 규칙 (Project Rules)

본 프로젝트는 **GitHub 공개 저장소**이다.  
참여하는 모든 AI 에이전트·개발자는 아래 규칙을 **작업 전·중·커밋/푸시 직전**에 반드시 준수한다.

관련 정본:
- 보안 하드닝 이력: `design_docs/development_log.md` (2026-07-26 보안 항목)
- 백로그: `design_docs/post_mvp_review_and_backlog_2026-07-26.md`
- 시크릿 스캔: `scripts/check_no_secrets.py`
- 환경 템플릿: `.env.template` (실 키 없음)

---

## 🔒 1. 시크릿·크리덴셜 — 절대 규칙 (위반 시 작업 중단)

### 1.1 하드코딩 금지
다음에 해당하는 값을 **소스·테스트 fixture 외 문서·커밋 메시지·이슈 본문·로그 출력**에 넣지 않는다.

| 금지 대상 예시 |
| :--- |
| OpenAI / Google / Anthropic / NVIDIA (`nvapi-…`) / Tavily API 키 |
| JWT_SECRET, API_KEY_ENCRYPTION_SECRET, Fernet 키 |
| DB 비밀번호, SMTP 앱 비밀번호 |
| TELEGRAM_BOT_TOKEN, TELEGRAM_WEBHOOK_SECRET, NGROK_AUTHTOKEN |
| 실 사용자 비밀번호, 프로덕션 admin 비밀번호 |
| PEM/private key, 실제 JWT 액세스 토큰 |

- **허용**: `.env` (로컬, gitignore), OS/컨테이너 환경변수, `.env.template`의 **빈 값·플레이스홀더 설명**
- **테스트 더미만 허용**: `test-openai-key`, `nvapi-test-key`, `dummy-key` 등 **명백히 가짜**이고 짧은 값. 실 키 형태·길이를 흉내 내지 말 것.

### 1.2 설정 진입점
- 런타임 비밀: **`app/core/config.py` (Pydantic Settings) + `.env` / 환경변수** 만 사용.
- 신규 시크릿 추가 시:
  1. `config.py` 필드 추가
  2. `.env.template`에 **빈 슬롯 + 주석** (실 값 금지)
  3. `docker-compose.prod.yml`에 필요 시 전달 (기본값에 약한 비밀번호 넣지 말 것)
  4. README/AGENTS 보안 절 갱신

### 1.3 Git에 올리면 안 되는 것
커밋·스테이징 전 **반드시** 확인:

| 경로/패턴 | 비고 |
| :--- | :--- |
| `.env`, `.env.local`, `.env.production` 등 | `.gitignore` — **force add 금지** |
| `*.db`, `*.db-*` | 로컬 DB |
| `*backup*.json`, `*_export*.json`, `novel_system_backup_*.json` | API 키 포함 가능 |
| `secrets/`, `exports/`, `backups/` | |
| `.venv/`, `ngrok`, `ngrok.exe` | |
| `*.pem`, private key | |

**푸시 전 필수 명령 (에이전트가 커밋/푸시를 도울 때):**
```bash
python scripts/check_no_secrets.py
git status
git diff --cached
```
- `check_no_secrets.py` 가 실패(exit 1)하면 **커밋/푸시하지 말고** 해당 줄을 제거·로테이션한다.
- staged 목록에 `.env` 가 보이면 **즉시 unstage** 하고 작업을 멈춘다.

### 1.4 유출 사고 시
코드에 실 키가 들어갔거나 push 된 경우:
1. 해당 키를 제공사에서 **즉시 폐기·재발급**
2. git history 정리만으로 충분하다고 단정하지 말 것
3. `development_log.md`에 조치 요약 기록

---

## 🔐 2. 프로덕션·암호화·기본값 규칙

### 2.1 production 기동 가드 (깨지 말 것)
`ENVIRONMENT=production` 일 때 아래를 **약화·우회하는 패치를 하지 않는다.**

- 기본 `JWT_SECRET` (`dev-secret-key-do-not-use-in-production`) → 기동 거부
- 약한 `INITIAL_ADMIN_PASSWORD` → 기동 거부
- `API_KEY_ENCRYPTION_SECRET` 미설정 → 기동 거부
- `DATABASE_URL` 에 기본 비밀번호 `password` 포함 → 기동 거부

구현 위치: `app/core/config.py` 하단 검증 블록.

### 2.2 API 키 at-rest 암호화
- 저장: `app/core/crypto.encrypt_api_key` 경유 (`app/routers/project.py` 등).
- **production** 에서 시크릿 없이 평문 저장으로 폴백하는 로직을 **다시 넣지 말 것** (`EncryptionNotConfiguredError` 유지).
- development 평문 폴백은 로컬 편의용일 뿐, 새 기능의 기본 동작으로 문서화하지 말 것.
- API **응답**에 키 본문을 넣지 말 것. 기존처럼 `has_api_key` / `has_*_api_key` 마스킹 유지 (`app/schemas/project.py`).

### 2.3 docker-compose.prod.yml
- `POSTGRES_PASSWORD`, `JWT_SECRET`, `API_KEY_ENCRYPTION_SECRET`, `INITIAL_ADMIN_PASSWORD` 등 **필수 env** 를 기본 약한 값으로 되돌리지 말 것.
- DB 호스트 포트 공개를 기본 활성화하지 말 것 (필요 시 주석으로만 안내).

### 2.4 TESTING 플래그
- `TESTING=True` 는 **pytest 전용**. 프로덕션·docker-compose.prod 에 넣지 말 것.
- TESTING 분기에서 인증·소유권 검사를 영구 제거하는 변경 금지 (테스트 픽스처로만 우회).

---

## 📦 3. Export / Backup / 마이그레이션 보안

| 기능 | 기본 동작 | 규칙 |
| :--- | :--- | :--- |
| `GET /migration/export/{id}` | **API 키 제외** | 기본을 “키 포함”으로 바꾸지 말 것 |
| `GET /admin/backup` | **API 키 제외** | 동일 |
| 키 포함이 필요할 때만 | `include_secrets=true` | 옵트인 유지. 로그·이슈에 파일 내용 붙이지 말 것 |

- `export_project_data(..., include_secrets=False)` 기본값 유지 (`app/services/migration.py`).
- 백업 JSON을 레포·PR·채팅에 첨부하지 말 것.
- import 시 키가 없는 export 는 정상이다. 키는 대상 환경에서 다시 입력하도록 UX/문서를 맞출 것.

---

## 🛡️ 4. 인증·인가·표면 노출

1. **소유권 가드**: 프로젝트/회차/설정 CRUD 는 `check_project_owner` 또는 동일 패턴 유지. 새 엔드포인트에 소유권 검사 누락 금지.
2. **Admin API**: `get_current_admin` 필수. 일반 유저 접근 경로 만들지 말 것.
3. **WebSocket**: JWT 를 URL 쿼리로 되돌리지 말 것. 첫 메시지 `auth` + 토큰 방식 유지.
4. **텔레그램 웹훅**: secret 헤더 fail-closed, 관리자 chat id 검증 유지. secret 빈 문자열로 set_webhook 하지 말 것.
5. **헬스체크**: DB 장애 시 503 유지 (로드밸런서가 실패를 알 수 있게).
6. **시크릿 로깅 금지**: `logger.info(api_key)`, 예외 메시지에 키/토큰 전체 출력 금지. 필요 시 앞 4자 마스킹 정도만.

---

## 🏗️ 5. 코드 품질 및 비동기

1. **Async Only**: LLM, DB, 외부 HTTP 는 `async/await`.
2. **단위 테스트**: 신규 기능은 `tests/` 에 테스트. 시크릿 관련 변경은 `tests/test_security_hardening.py` 또는 동등 테스트 갱신.
3. **기존 패턴 준수**: 라우터 분리, `LLMFactory.get_model_for_agent`, 암호화 헬퍼 재사용 — 우회 복붙 금지.

---

## ✅ 6. 에이전트 작업 체크리스트

### 작업 시작 시
- [ ] `README.md` + 본 파일(`.agents/AGENTS.md`) + `sprint_board.md` / `development_log.md` 확인
- [ ] 실 `.env` 내용을 코드/PR/로그에 붙여 넣지 않을 것

### 기능 구현 중
- [ ] 새 시크릿 → config + `.env.template`(빈 값) 만
- [ ] 사용자 LLM 키 저장 → `encrypt_api_key` / 응답 마스킹
- [ ] export·다운로드·백업에 키 기본 포함 여부 재검토 (기본 제외)
- [ ] production 가드·TESTING 우회를 “편의”로 제거하지 않음

### 커밋·푸시 전 (에이전트가 git 조작 시)
- [ ] `python scripts/check_no_secrets.py` 통과
- [ ] `git status` 에 `.env`, `*.db`, `*backup*.json` 없음
- [ ] diff 에 실 키·토큰·비밀번호 없음
- [ ] 커밋 메시지에 시크릿 없음
- [ ] 사용자가 명시적으로 요청하지 않으면 **push / force-push 하지 않음** (일반 git 안전 규칙)

### 완료 시
- [ ] `development_log.md` 에 변경 요약 (시크릿 값 없이)
- [ ] 보안 관련이면 본 AGENTS.md 규칙과 모순되지 않는지 재확인

---

## 🚫 7. 명시적 금지 목록 (자주 하는 실수)

1. “임시로” `.env` 를 레포에 복사해 커밋
2. `docker-compose.prod.yml` 에 `password` / `admin-pass-123!` 를 다시 기본값으로 넣기
3. export 기본값을 `include_secrets=True` 로 변경
4. `encrypt_api_key` 를 건너뛰고 DB에 평문 키 저장
5. ProjectResponse 에 `api_key_override` 평문 필드 추가
6. README/이슈에 본인 서버의 실 토큰·BASE_URL+웹훅 시크릿 동시 노출
7. 프로덕션 이미지에 `TESTING=True` 또는 기본 JWT 로 기동되게 만들기
8. “디버그용”으로 키 전체를 print / logger

---

## 📌 8. 공개 레포 멘탈 모델

> 이 저장소를 clone 하는 **모든 사람**이 소스의 기본값·문자열을 본다.  
> 기본 비밀번호·기본 JWT 는 **이미 공개된 값**으로 취급한다.  
> 보호는 **환경변수·암호화·가드·키 미포함 export** 로만 한다.

규칙을 바꿔야 할 보안 설계 변경이 있으면, 코드만 바꾸지 말고 **본 파일과 README 보안 절을 함께 갱신**한다.
