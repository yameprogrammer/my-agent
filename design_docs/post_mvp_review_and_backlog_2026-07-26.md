# 포스트 MVP 구현 리뷰 · 보완 사항 · 추가 아이디어 백로그

> **작성일**: 2026-07-26  
> **목적**: 문서·코드베이스 대조 리뷰 결과를 고정하고, 보완 사항과 추가 아이디어를 우선순위별로 착수 가능하게 정리한다.  
> **범위**: Sprint 1–6 및 후속 기능(Admin, Research, Migration, Download) 반영 시점 기준  
> **대상 독자**: 이어받는 개발 에이전트 / 프로젝트 오너

관련 문서:
- [sprint_board.md](./sprint_board.md) — 스프린트 태스크 트래커
- [development_log.md](./development_log.md) — 누적 개발 일지
- [remaining_work_2026-07-10.md](./remaining_work_2026-07-10.md) — 이전 잔여 작업 (부분 구식, 본 문서가 후속 정본)
- [product_spec.md](./product_spec.md) — 고급 UX 요구사항
- [tech_stack.md](./tech_stack.md) — 배포 아키텍처
- [code_review_2026-07-10.md](./code_review_2026-07-10.md) — Sprint 4-D 코드 리뷰 정본

---

## 1. 한 줄 결론

| 관점 | 평가 |
| :--- | :--- |
| **로컬 MVP 완성도** | 높음 — 가입 승인 → 기획 → 집필 스트림 → HITL 승인 풀사이클 가능 |
| **제품 완성도** | 중상 — 다운로드·백업 UI, 회차 간 연속성, Termux 배포가 빠져 “거의 다 됨” 상태 |
| **문서 신뢰도** | 중 — 로그는 최신, 보드 상단 요약·구 remaining_work는 드리프트 |
| **프로덕션 준비** | 중하 — Docker 뼈대는 있으나 Sprint 5 운영 체계 미완 |
| **장편 품질 엔진** | 중 — 회차 내 루프는 탄탄, 회차 간·작품 단위 기억은 약함 |

**다음 가치의 ROI 상위:**

1. ~~다운로드 SPA~~ → **IMP-01 Done**
2. **작가 주도권 — Human Editing / Co-writing** → [human_editing_cowriting_design.md](./human_editing_cowriting_design.md) (H1~H6)
3. 마이그레이션 SPA UI (IMP-02)
4. 회차 간 연속성 (IMP-07)
5. Sprint 5 배포·백업 체계

---

## 2. 현재 구현 상태 (2026-07-26 스냅샷)

### 2.1 스프린트·기능 매트릭스

| 영역 | 상태 | 비고 |
| :--- | :---: | :--- |
| Sprint 1 — DB·FastAPI·JWT | ✅ Done | PostgreSQL + pgvector, SQLModel |
| Sprint 2 — 프로젝트/설정/캐릭터/회차 CRUD | ✅ Done | 소유권 가드 포함 |
| Sprint 3 — 에이전트·LangGraph·RAG | ✅ Done | Plotter→RAG→Writer→Judge→Editor, 하이브리드 RAG |
| Sprint 4 — WebSocket·HITL·리뷰 수정 | ✅ Done | Reviewer, Editor→Judge 루프 정합 |
| Sprint 5 — Termux 배포 | ⚪ To Do | PM2, Nginx, Tunnel, pg_dump |
| Sprint 6 — Vite SPA | ✅ Done | 단일 포트 정적 서빙 (`frontend/dist`) |
| Reviewer + 에이전트별 LLM | ✅ Done | Project 컬럼 오버라이드 |
| AI 기획 파트너 / 기획·플롯 검수 | ✅ Done | Brainstorm + PlanningAuditor + PlotAuditor |
| 고증 참고 자료 + 리서치 에이전트 | ✅ Done | `ReferenceMaterial`, Tavily 경로 |
| Admin 웹 포털 | ✅ Done | 통계, 회원 승인, 시스템 백업/복원 |
| 프로젝트 마이그레이션 API | ✅ Backend | export/import — **SPA UI 없음** |
| 소설 다중 포맷 다운로드 API | ✅ Backend | TXT/EPUB/PDF/DOCX — **SPA UI 없음** |
| Custom OpenAI 호환 API | ✅ Done | `API_KEY::BASE_URL` 오버로드 |
| 추론 스트림·가로 Stepper UI | ✅ Done | 집필 모니터 |

> **문서 주의**: `sprint_board.md` 상단 요약 표는 6-C~6-G를 To Do로 남길 수 있다. **하단 상세 섹션과 development_log 기준 Done이 정본**이다. 작업 착수 시 상단 표를 동기화할 것.

### 2.2 정상 동작 경로 (로컬)

```
회원가입 (is_active=False)
  → 텔레그램/Admin 승인
  → 로그인
  → 프로젝트 생성 (LLM 프로바이더/모델)
  → 세계관·캐릭터·(선택) 참고 자료 / AI 기획 파트너
  → 회차 생성
  → 집필실 WebSocket: start_writing → 스트림 → Reviewer 점수
  → HITL 승인 또는 피드백 재교정
  → Content 버전 저장 (is_approved)
```

### 2.3 검증 환경 메모

- 통합 테스트는 **PostgreSQL(Docker) 기동**이 전제다. DB 미기동 시 health `503`, CRUD/WS E2E `ConnectionRefusedError`가 발생한다.
- 권장: `docker compose up -d` 후 `pytest` 실행.
- 프론트 개발: Vite `:3000` + API `:8080` 프록시 / 프로덕션: `npm run build` 후 FastAPI 단독 서빙.

### 2.4 코드 구조 현황 (본선 vs 부선)

| 경로 | 역할 | 권장 취급 |
| :--- | :--- | :--- |
| `app/` | FastAPI 본선 백엔드 | **유지·확장** |
| `frontend/` | Vite SPA 본선 UI | **유지·확장** |
| `ui/` | 레거시 Streamlit | 보관 또는 폐기 결정 후 문서화 |
| `packages/`, `src/my_agent/`, `apps/admin/` | `__pycache__`만 존재, git 미추적 | **고아 실험 잔재** — 삭제 또는 소스 복원·문서화 |
| `tests/` | pytest E2E·단위 | DB 의존 통합 테스트 다수 |
| `docker-compose*.yml`, `Dockerfile` | 로컬/프로덕션 뼈대 | Sprint 5에서 운영 런북 보강 |

---

## 3. 문서 vs 코드 드리프트

| 항목 | 문서/기대 | 실제 | 조치 |
| :--- | :--- | :--- | :--- |
| Sprint 6 상단 요약 | 일부 To Do로 보일 수 있음 | 구현·로그상 Done | 보드 상단 동기화 |
| `remaining_work_2026-07-10.md` | Sprint 5 직전 P0 중심 | 이후 Admin/Research/Migration/Sprint6 추가됨 | **본 문서를 후속 백로그 정본**으로 사용 |
| product_spec 고급 UX | 완성 조건 | RW-08~12 대부분 미구현 | “완성” 표기 금지, 별도 스프린트 |
| 실험 패키지 계층 | 아키텍처 확장 흔적 | 소스 없음·pycache only | 정리 또는 의도 문서화 |
| Streamlit UI | Sprint 4 산출 | SPA가 본선 | README에 레거시 명시 |

---

## 4. 보완 사항 백로그 (우선순위)

### 4.1 P0 — 제품 완성 체감 · 배포 전 필수

#### IMP-01. 소설 다운로드 SPA UI 연동 ✅ Done (2026-07-26)

| 항목 | 내용 |
| :--- | :--- |
| **현황** | `GET /projects/{project_id}/download?format=` (txt/epub/pdf/docx) 백엔드 구현됨 (`app/routers/project.py`, `app/services/compiler.py`) |
| **구현** | SPA: 프로젝트 헤더「원고 내보내기」+ 대시보드 카드「내보내기」→ 포맷 모달(TXT/EPUB/PDF/DOCX); `downloadBlob` JWT blob 다운로드 |
| **검증** | 파일명 Content-Disposition 파싱 단위 테스트; 수동: 회차 있는 프로젝트 4포맷 / 회차 없으면 토스트 에러 |
| **파일** | `frontend/src/api/client.js`, `pages/project.js`, `pages/dashboard.js`, `components/modal.js` |

#### IMP-02. 프로젝트 마이그레이션 SPA UI 연동

| 항목 | 내용 |
| :--- | :--- |
| **현황** | `GET/POST` migration export·import API 구현 (`app/routers/migration.py`, `app/services/migration.py`) |
| **공백** | SPA에서 내보내기/가져오기 UX 없음 |
| **작업** | JSON(또는 ZIP) 다운로드 + 파일 업로드 복원 플로우; 소유권·중복 처리 안내 |
| **검증** | export → 타 계정/클린 DB import → 설정·캐릭터·회차·버전 트리 복원 |
| **파일 후보** | `frontend/src/pages/settings.js` 또는 `dashboard.js` |

#### IMP-03. 의존성 명시 누락 해소

| 항목 | 내용 |
| :--- | :--- |
| **현황** | 리서치 경로에서 `tavily` import; Fernet은 `cryptography` 의존 |
| **공백** | `requirements.txt`에 `tavily-python`(또는 사용 패키지명), `cryptography` 명시 여부 불완전할 수 있음 |
| **작업** | 실제 import 기준으로 requirements 보강; Docker 이미지 재빌드 스모크 |
| **검증** | 클린 venv / Docker 빌드 후 import 및 리서치 엔드포인트 기동 |

#### IMP-04. Sprint 5-A — 프로세스·리버스 프록시

| 항목 | 내용 |
| :--- | :--- |
| **목표** | Termux/홈서버에서 API(+정적 SPA) 상시 운용 |
| **작업** | PM2 ecosystem (uvicorn), 자동 재시작, 로그 로테이션; Nginx 리버스 프록시·보안 헤더 |
| **검증** | 크래시 후 재기동; `/health` 프록시 경유 200; 정적 SPA 로드 |
| **보드** | Sprint 5-A / 구 RW-13, RW-14 |

#### IMP-05. Sprint 5-B — 외부 접속·DB 백업·시크릿

| 항목 | 내용 |
| :--- | :--- |
| **작업** | Cloudflare Tunnel(또는 Tailscale) HTTPS; `pg_dump` 주기 백업·보관 정책; 프로덕션 비밀번호·JWT·암호화 시크릿 분리 |
| **주의** | `docker-compose.prod.yml` 기본 `postgres/password` 사용 금지 문서화 |
| **검증** | 외부 HTTPS 접속; 백업 파일 복원 리허설; production 기본 JWT로 기동 거부 |
| **보드** | Sprint 5-B / 구 RW-15~18 |

#### IMP-06. 문서·보드 동기화

| 항목 | 내용 |
| :--- | :--- |
| **작업** | `sprint_board.md` 상단 Sprint 6 상태 Done 확정; README 문서 목록에 본 파일 링크; 구 remaining_work 상단에 “후속 정본” 배너 |
| **검증** | 신규 에이전트가 보드만 보고도 다음 착수점을 오인하지 않음 |

---

### 4.2 P1 — 장편 품질·안정성 (핵심 차별화)

#### IMP-07. 회차 간 연속성 (이전 회차 컨텍스트)

| 항목 | 내용 |
| :--- | :--- |
| **문제** | 회차 내 씬은 `draft`로 이어지나, **이전 회차 승인본은 Plotter/Writer에 주입되지 않음** |
| **리스크** | 2화 이후 톤·사건·인물 상태 단절 |
| **제안 설계** | (A) 승인 시 자동 에피소드 요약 저장 테이블/필드 → (B) 다음 회차 Plotter·Writer에 직전 N화 요약 주입 |
| **검증** | 1화 승인 후 2화 기획 프롬프트에 1화 결말/훅이 포함되는지 단위·수동 스모크 |
| **우선도** | 장편 목표 시 **P1 최상위** |

#### IMP-08. Plotter 컨텍스트 토큰 최적화

| 항목 | 내용 |
| :--- | :--- |
| **문제** | Plotter가 전 캐릭터·전 세계관 **전문**을 일괄 주입. 설정집 성장 시 비용·품질 악화 |
| **제안** | 중요도 필터, outline 기반 RAG, 아크 요약 메모리 계층, Writer와 동일한 하이브리드 검색 재사용 |
| **검증** | 설정 50+건 프로젝트에서 토큰 추정 감소 + 기획 품질 수동 비교 |

#### IMP-09. Content 버전 트리 UX 보강

| 항목 | 내용 |
| :--- | :--- |
| **현황** | DB `parent_id` 트리 + 목록·최종 승인 UI |
| **공백** | diff, 롤백, 브랜치 비교, 트리 시각화 (`product_spec` 버전 히스토리) |
| **최소 구현** | “이 버전으로 되돌리기(신규 Content 복제)” + 두 버전 텍스트 diff 모달 |
| **검증** | 승인본 변경 후 이전 버전 복원 가능 |

#### IMP-10. API 키 암호화 production 정책 강화

| 항목 | 내용 |
| :--- | :--- |
| **현황** | `API_KEY_ENCRYPTION_SECRET` 없으면 평문 폴백 (`app/core/crypto.py`) |
| **제안** | `ENVIRONMENT=production` 시 시크릿 미설정이면 기동 거부 또는 키 저장 API 거부 |
| **검증** | production 설정에서 평문 저장 경로가 막히는지 |

#### IMP-11. 참고 자료(Reference) 검색 정밀도

| 항목 | 내용 |
| :--- | :--- |
| **현황** | 제목 키워드 매칭 + force_reference_ids + 최신 N건 폴백; WorldSetting과 달리 임베딩 컬럼 없음 |
| **제안** | Reference 임베딩 컬럼 또는 별도 청크 테이블; 씬 plot 시맨틱 검색 |
| **검증** | 강제 ID 없이도 관련 고증이 Writer lore_context에 포함 |

#### IMP-12. 고아 코드·레거시 정리

| 항목 | 내용 |
| :--- | :--- |
| **대상** | `packages/`, `src/my_agent/`, `apps/admin/` pycache; 선택적으로 `ui/` Streamlit |
| **작업** | (옵션 A) 삭제 + .gitignore; (옵션 B) 실험 브랜치/문서로 “차세대 오케스트레이터” 의도 남기기 |
| **검증** | git status clean, 본선 테스트 영향 없음 |

---

### 4.2b Human Editing & Co-writing (작가 주도권) — 설계 정본

> **정본**: [human_editing_cowriting_design.md](./human_editing_cowriting_design.md)

| Phase | 범위 | 우선도 | 상태 |
| :--- | :--- | :---: | :---: |
| **H1** | 본문 편집 → Content 버전 저장·승인 (회차 탭) | P0 | ✅ Done (2026-07-26) |
| **H2** | 집필실 인라인 에디터 + HITL 「고치고 승인」 | P0 | ✅ Done (2026-07-26) |
| **H3** | 사용자 초안 윤문/이어쓰기 (`write_mode`) | P1 | ✅ Done (2026-07-26) |
| **H4** | Plotter 씬 보드 사람 확정 게이트 | P1 | ⚪ To Do |
| **H5** | 기획 제안 인라인 편집 후 적용 | P1 | ⚪ To Do |
| **H6** | diff 대조·부분 재작성·버전 트리 (고급) | P2 | ⚪ To Do |

product_spec Writing View「즉시 수정」은 **H1–H2** 로 부분 충족 목표.

### 4.3 P2 — product_spec 고급 UX (의도적 백로그)

Sprint 4–6 MVP “완성” 표기와 분리한다. 상세 UX: [product_spec.md](./product_spec.md).  
Human edit 본선은 §4.2b / `human_editing_cowriting_design.md` 를 따른다.

| ID | 항목 | 현재 | 제안 |
| :--- | :--- | :--- | :--- |
| **IMP-13** / RW-08 | AI 제안 ↔ 사용자 피드백 대조 편집기 | 미구현 | H6 / 좌우 분할 diff |
| **IMP-14** / RW-09 | 인터랙티브 플롯 맵 / 씬 타임라인 | 상태 이벤트 수준 | H4 씬 보드와 연계 |
| **IMP-15** / RW-10 | 회차 긴장도·전개 속도 UI | 에이전트 내부 필드 | H4 씬 카드 tension/pace |
| **IMP-16** / RW-11 | 버전 히스토리 롤백 UI | 목록·승인만 | H1 버전 저장 후 H6 트리 |
| **IMP-17** / RW-12 | 스트림 본문 인라인 수동 수정 | 보기 위주 | **H1–H2** |

---

### 4.4 P3 — 운영·보안 디테일

| ID | 항목 | 설명 |
| :--- | :--- | :--- |
| **IMP-18** | 초기 관리자 비밀번호 | 기본값 존재 — 프로덕션 강제 변경·로그 경고 유지 |
| **IMP-19** | JWT 7일 + localStorage | 개인 홈서버는 수용 가능; 공개 서비스 시 refresh/짧은 만료 검토 |
| **IMP-20** | 장시간 구동 스트레스 체크리스트 | 동시 WS, LLM 타임아웃, 디스크(로그·DB) |
| **IMP-21** | health 실패 알림 | `/health` 실패 시 텔레그램 관리자 알림 |
| **IMP-22** | Alembic 정식 마이그레이션 | ad-hoc 스크립트 한계 돌파 시 도입 |

---

## 5. 추가 아이디어 (신규 기능·제품 확장)

보완(기존 구멍 메우기)과 별도로, **제품 경쟁력·장편 품질**을 올리는 아이디어다.

### 5.1 장편 서사 엔진 (High Impact)

| ID | 아이디어 | 설명 | 기대 효과 |
| :--- | :--- | :--- | :--- |
| **IDEA-01** | 에피소드 요약 메모리 | 승인 시 요약 자동 생성·저장, 다음 회차 주입 | IMP-07 구현체 |
| **IDEA-02** | 캐릭터 상태 트래킹 | 위치·관계·아크 진행·부상/사망 등 상태 스냅샷 | OOC·설정 붕괴 감소 |
| **IDEA-03** | 복선 레지스트리 | 심은 복선 / 회수 여부 / 목표 회차 / Judge 연동 | 장편 만족도 |
| **IDEA-04** | 멀티 에피소드 아크 플래너 | 작품 전체 아크 → 회차 outline 일괄 생성 | 단편 머신 → 장편 머신 |
| **IDEA-05** | 회차 말미 훅 강제 옵션 | Reader-hook 점수를 회차 종료 조건에 반영 | 연재형 호흡 |

> 참고: 로컬에 `master_planner` / `arc_planner` 등 **실험 pycache 흔적**이 있으나 소스는 본선에 없음. IDEA-04 착수 시 기존 실험 의도를 재설계하는 편이 안전하다.

### 5.2 집필실 UX (Medium–High)

| ID | 아이디어 | 설명 |
| :--- | :--- | :--- |
| **IDEA-06** | 씬 단위 재집필 | 전체 회차 재실행 없이 특정 씬만 Writer→Judge |
| **IDEA-07** | 체크포인트 이어쓰기 UI | LangGraph thread 재개 상태를 “이어서 집필”로 명시 |
| **IDEA-08** | 스타일 가이드 업로드 | 문체 샘플 문단 → Writer/Editor 고정 system 지시 |
| **IDEA-09** | 작가 메모 / 회차 노트 | outline과 별도 free-form 메모를 RAG에 포함 |
| **IDEA-10** | 집필 중단·취소 | 진행 중 그래프 soft-cancel, 부분 draft 보존 |

### 5.3 비용·관측성 (Medium)

| ID | 아이디어 | 설명 |
| :--- | :--- | :--- |
| **IDEA-11** | 토큰·비용 대시보드 | 회차·에이전트별 대략 사용량 (개인 API 키 사용자 핵심) |
| **IDEA-12** | 에이전트 호출 로그 | 프롬프트 해시·latency·실패 원인 (개인정보 마스킹) |
| **IDEA-13** | 저비용 모드 | Plotter/Judge는 소형 모델, Writer만 대형 모델 프리셋 원터치 |

### 5.4 콘텐츠 입출력 (Medium)

| ID | 아이디어 | 설명 |
| :--- | :--- | :--- |
| **IDEA-14** | 연재 플랫폼 투고 포맷 프리셋 | 문장 길이·빈 줄·화수 표기 (카카오페이지 등 관례) |
| **IDEA-15** | 회차 단위 다운로드 | 프로젝트 전체가 아닌 선택 회차만 |
| **IDEA-16** | 외부 원고 import | 기존 텍스트를 Content v1으로 넣고 AI 퇴고만 수행 |
| **IDEA-17** | 세계관 그래프 시각화 | 키워드 관계(장소–인물–아이템) 간단 노드 맵 |

### 5.5 협업·멀티 프로젝트 (Low–Medium)

| ID | 아이디어 | 설명 |
| :--- | :--- | :--- |
| **IDEA-18** | 프로젝트 공유 읽기 전용 링크 | 검토자용 (인증 티켓) |
| **IDEA-19** | 템플릿 프로젝트 | 장르별 시놉시스·캐릭터 스켈레톤 |
| **IDEA-20** | 프롬프트 버전 관리 | 에이전트 시스템 프롬프트를 DB/파일로 A/B |

### 5.6 아키텍처·엔지니어링 (지속 개선)

| ID | 아이디어 | 설명 |
| :--- | :--- | :--- |
| **IDEA-21** | `agents.py` 모듈 분리 | 역할별 파일로 유지보수성 확보 |
| **IDEA-22** | 프론트 부분 TypeScript화 | 페이지 비대화 대응 |
| **IDEA-23** | 동시 집필 큐 | Termux 리소스 한도 내 프로젝트당 1 워크플로 |
| **IDEA-24** | `deploy/` 런북 폴더 | PM2·nginx·cloudflared·backup cron 샘플 일괄 |

---

## 6. 권장 착수 순서

```
[즉시 / 1–2일]
  IMP-06 문서·보드 동기화
  IMP-01 다운로드 UI
  IMP-02 마이그레이션 UI
  IMP-03 requirements 보강
  IMP-12 고아 아티팩트 정리 (선택)

[품질 점프]
  IMP-07 / IDEA-01 회차 요약 메모리
  IMP-08 Plotter 컨텍스트 축소
  IMP-09 버전 롤백·diff (최소)

[배포]
  IMP-04 Sprint 5-A
  IMP-05 Sprint 5-B
  IMP-10 production 암호화 강제
  IMP-20 스트레스 체크리스트

[병행 가능 / 이후]
  product_spec UX (IMP-13~17)
  장편 엔진 (IDEA-02~05)
  관측성·비용 (IDEA-11~13)
```

### 권장 스프린트 묶음 (제안)

| 제안 스프린트 | 범위 | 목표 |
| :--- | :--- | :--- |
| **Sprint 7 — Ship Gaps** | IMP-01, 02, 03, 06, (12) | “백엔드만 있는 기능” 제거, 문서 정합 |
| **Sprint 8 — Longform Memory** | IMP-07, 08, IDEA-01 | 2화 이후 품질 |
| **Sprint 5 (재개)** | IMP-04, 05, 10, 20 | 폰/홈서버 상시 운용 |
| **Sprint 9 — Author UX** | IMP-09, 13~17, IDEA-06~08 | 작가 도구화 |
| **Sprint 10 — Arc Engine** | IDEA-02~05 | 장편 차별화 |

---

## 7. 운영 체크리스트 (배포 시 필수 — 유지)

코드 작업과 별도로 기동 전 확인:

| 항목 | 요구 |
| :--- | :--- |
| `ENVIRONMENT` | 프로덕션은 `production` |
| `JWT_SECRET` | 기본값 금지 — production 기동 거부 |
| `API_KEY_ENCRYPTION_SECRET` | Fernet 키; production 평문 폴백 금지 권장 (IMP-10) |
| `TELEGRAM_BOT_TOKEN` / `ADMIN_TELEGRAM_CHAT_ID` | 승인 플로우 사용 시 |
| `TELEGRAM_WEBHOOK_SECRET` | 8자 이상 — fail-closed |
| `OPENAI_API_KEY` | 시맨틱 RAG·임베딩 (없으면 키워드 RAG) |
| `TAVILY_API_KEY` | 리서치 에이전트 실검색 |
| `DATABASE_URL` | 프로덕션 자격증명, 기본 password 금지 |
| `BASE_URL` | 웹훅용 공개 HTTPS URL |
| `INITIAL_ADMIN_PASSWORD` | 기본값 변경 |

---

## 8. 완료 처리 규칙

1. 착수 시 `sprint_board.md`에 Task ID(IMP-xx / IDEA-xx)를 마이크로 태스크로 옮기거나 신규 스프린트 섹션을 만든다.
2. 완료 시 본 문서 해당 행에 `✅ Done` 및 완료일을 표기한다.
3. `development_log.md`에 수행 내용·검증 결과·handoff를 남긴다.
4. product_spec 항목을 끝내지 않은 채 “Writing View 완성”으로 표기하지 않는다.

---

## 9. 변경 이력

| 날짜 | 내용 |
| :--- | :--- |
| 2026-07-26 | 초안 작성 — 포스트 MVP 리뷰, 보완(IMP)·아이디어(IDEA) 백로그, 권장 순서 고정 |
