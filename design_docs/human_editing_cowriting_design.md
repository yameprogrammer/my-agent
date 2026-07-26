# 작가 주도권 강화: Human Editing & Co-writing 설계서

> **작성일**: 2026-07-26  
> **상태**: 설계 확정 · **H1–H3·H5 구현 완료** · H4 대기  
> **목적**: AI 자동 집필 파이프라인을 유지하면서, 작가가 본문·플롯·기획·설정 전 레이어에서 **직접 수정·초안 투입·공동 집필**할 수 있는 제품 축을 정의한다.  
> **관련 문서**: [product_spec.md](./product_spec.md), [post_mvp_review_and_backlog_2026-07-26.md](./post_mvp_review_and_backlog_2026-07-26.md), [supplementary_design_specs.md](./supplementary_design_specs.md)

---

## 1. 배경과 문제 정의

### 1.1 현재 제품의 편향

본 시스템은 LangGraph 순환 집필(Plotter → RAG → Writer → Judge → Editor → Reviewer → HITL)에 강점이 있다.  
반면 작가 측 상호작용은 대체로 다음으로 제한된다.

| 가능 | 제한적 / 불가 |
| :--- | :--- |
| 설정·캐릭터 CRUD | 집필실 본문 **직접 편집·저장** |
| 회차 아웃라인 편집 | Plotter 산출 **씬 보드** 편집 후 집필 |
| HITL **자연어 피드백** → AI 재작성 | 피드백 없이 **고치고 승인** |
| 버전 **열람·최종본 승인** | 버전 **수정 저장** (author_type=user/hybrid) |
| 기획 제안 체크 적용 | 제안 문장 **인라인 수정 후 적용** |
| 시놉시스만 주고 전량 생성 | **사용자 초안** 기반 윤문·이어쓰기 |

### 1.2 product_spec 갭

`product_spec.md` Writing View는 다음을 요구한다.

- 실시간 에디터: AI 텍스트 **즉시 수정**
- 피드백: 승인 / 부분 수정 요청 / 전체 재작성

현재 SPA는 **확인 + 자연어 피드백 + 승인** 중심이며, “즉시 수정”이 빠져 있다.

### 1.3 목표 멘탈 모델

```
AI 초안  ──►  사람 손질  ──►  확정(정본)  ──►  (선택) 다음 AI 단계
     ▲              │
     └──── 사람 초안 ─┘  (윤문 / 이어쓰기 모드)
```

**작가가 최종 문장 책임자**이고, AI는 초안·확장·윤문·검수 조수다.

---

## 2. 설계 원칙

1. **모든 AI 산출물은 편집 가능해야 한다**  
   본문, 씬 보드, (가능하면) 기획 제안 텍스트, 기존 설정 행.
2. **사람 수정은 덮어쓰기보다 새 버전**  
   `Content.parent_id` 트리 + `author_type` (`ai` | `user` | `hybrid`) 유지.
3. **승인 ≠ AI 재실행**  
   “이 텍스트를 정본으로”와 “AI에게 다시 고쳐라”를 UI·API에서 분리.
4. **피드백은 보조, 직접 편집이 기본 경로**  
   자연어 재작성은 비용·통제 측면에서 2순위.
5. **레이어별 동일 패턴**  
   `AI 초안 → (선택) 사람 편집 → 확정/적용 → (선택) 다음 AI`.
6. **기존 파이프라인 비파괴**  
   `from_scratch` 완전 자동 모드는 유지. co-writing은 모드·옵트인 확장.
7. **보안·소유권**  
   기존 `check_project_owner` / JWT / 응답 마스킹 규칙(`.agents/AGENTS.md`) 준수. 본문에 시크릿 로깅 금지.

---

## 3. 현황 매핑 (As-Is)

| 레이어 | 백엔드 | 프론트 | 평가 |
| :--- | :--- | :--- | :---: |
| 시놉시스 | Project update | settings 탭 | ✅ |
| WorldSetting / Character | CRUD + brainstorm apply/update | 모달 CRUD, 기획 체크 적용 | ✅ / △ 제안 인라인 약함 |
| Episode.outline | CRUD | 회차 폼 | ✅ |
| Content 버전 | POST create, GET list, PUT approve | 열람·승인만 | △ API O / UI 편집 X |
| 집필 WS | start_writing, submit_feedback, approve | 뷰어 + 피드백 | △ 시드 초안 X |
| Plotter scenes | AgentState.scenes | 상태 이벤트 수준 | ❌ 편집 UI 없음 |

**재활용 자산**

- `POST /projects/{pid}/episodes/{eid}/contents` — 이미 `text`, `parent_id`, `author_type`, `version_tag`
- `author_type` 배지 UI (`episodes.js` getAuthorBadge)
- HITL `interrupt_before=["user_review"]` + draft 브로드캐스트
- Brainstorm `change_type=update` + apply upsert

---

## 4. 목표 아키텍처 (To-Be)

### 4.1 레이어별 코라이팅 루프

```mermaid
flowchart TB
  subgraph Lore["설정 / 캐릭터"]
    L1[AI 기획 제안] --> L2[인라인 편집]
    L2 --> L3[DB 적용]
    L3 --> L4[수동 CRUD]
  end

  subgraph Plot["플롯"]
    P1[회차 outline 사람 작성] --> P2[Plotter 씬 보드]
    P2 --> P3[씬 보드 사람 편집]
    P3 --> P4[Writer 진입]
  end

  subgraph Body["본문"]
    B0[사람 초안 seed] --> B1
    B1[Writer / 윤문] --> B2[집필실 에디터]
    B2 --> B3[Content 버전 저장]
    B3 --> B4[최종본 승인]
    B2 -->|자연어 피드백| B1
  end
```

### 4.2 집필 모드 (`write_mode`)

| mode | 설명 | Plotter | Writer 입력 |
| :--- | :--- | :---: | :--- |
| `from_scratch` | 기존과 동일 전량 생성 | O | outline + lore |
| `polish_draft` | 사용자 초안 윤문·정교화 | 스킵 권장 | seed_draft + lore |
| `continue_draft` | 초안 유지, 이후 분량 생성 | 선택 | seed_draft + “이어쓸 것” 지시 |
| `scenes_locked` | 사람이 확정한 scenes 로 Writer만 | 스킵 | scenes + lore |

기본값은 `from_scratch` (하위 호환).

### 4.3 HITL 확장 액션 (WebSocket)

| action | 의미 |
| :--- | :--- |
| `submit_feedback` | 기존 — AI Editor 경로 (user_feedback) |
| `approve` | 기존 — 현재 graph draft 저장·종료 |
| **`save_human_edit`** (신규) | 클라이언트가 보낸 `edited_text` 로 Content 버전 생성 후, 선택적으로 approve |
| **`approve_edited`** (신규 또는 save 옵션) | 편집본을 draft로 확정·승인, graph resume save 또는 REST 병행 |

권장 단순화:

1. **REST로 버전 저장** (`POST contents`, author_type=user|hybrid)  
2. **REST로 승인** (`PUT .../approve`)  
3. WS는 진행 중 스트림·피드백·기존 approve 유지  

집필실 waiting_user 에서는 REST 저장+승인 후 UI를 done 으로 맞추거나, WS `approve` 전에 state draft 를 사람 텍스트로 패치하는 노드를 추가한다.  
**1차 구현은 REST 우선** (그래프 복잡도 최소화).

### 4.4 데이터·스키마

#### Content (기존 유지, 규약 강화)

| 필드 | 규약 |
| :--- | :--- |
| `author_type` | `ai` 자동 생성 · `user` 순수 사람 · `hybrid` AI 기반 사람 수정 |
| `parent_id` | 편집 시 원본 Content.id |
| `version_tag` | 예: `v1.0`, `v1.1-human`, `v1.2-polish` |
| `is_approved` | 회차당 하나 (기존 approve 로직) |

`ContentCreate.author_type` 스키마 description 을 `user \| ai \| hybrid` 로 문서화 (코드 기본값은 user 유지 가능).

#### Episode (선택 확장 — Phase B+)

| 필드 | 용도 |
| :--- | :--- |
| `writer_notes` 또는 기존 `outline` 활용 | 작가 메모 (이미 outline 있음) |
| (선택) `seed_draft` 미저장 시 | 클라이언트만 보관하거나 Content 초안 버전으로 저장 권장 |

초안은 **Content 로 저장**하는 편이 버전 관리와 일치한다 (`author_type=user`, 미승인).

#### AgentState (Phase B)

```python
# 추가 필드 (개념)
write_mode: str          # from_scratch | polish_draft | continue_draft | scenes_locked
seed_draft: str          # 사용자 초안
scenes_locked: bool      # True 면 plotter 스킵
```

---

## 5. 기능 패키지 (FP) 정의

### FP-A. 본문 Human Edit (P0) — 최우선

**작가 가치**: AI/기존 원고를 직접 고쳐 정본으로 만든다.

| 항목 | 명세 |
| :--- | :--- |
| UI | 회차 버전 「원문 보기」→ **편집** 토글; textarea; 「새 버전으로 저장」; 「저장 후 최종본 승인」 |
| API | 기존 `POST .../contents` + `PUT .../approve` |
| payload | `parent_id`, `text`, `author_type=hybrid|user`, `version_tag` 자동 제안 |
| 집필실 | waiting_user 패널에 「본문 직접 수정」→ 동일 REST → 로컬 draft 갱신 + 승인 버튼 |

**비범위 (A)**: diff 뷰, 문단 단위 AI, 그래프 state 패치.

### FP-B. 집필실 인라인 에디터 + HITL 통합 (P0)

| 항목 | 명세 |
| :--- | :--- |
| UI | 좌측 draft 영역을 읽기 전용 뷰 / 편집 모드 전환 |
| 동작 | 편집 중 스트림 수신 시 충돌 정책: 편집 중이면 스트림 덮어쓰기 금지, 토스트 안내 |
| 저장 | FP-A REST |
| 승인 | 편집본 저장 후 approve REST 또는 기존 WS approve (저장된 승인본이 우선) |

### FP-C. 사용자 초안 기반 모드 (P1)

| 항목 | 명세 |
| :--- | :--- |
| UI | 집필 시작 전: 모드 선택 + 초안 textarea (또는 기존 Content 선택) |
| WS | `start_writing` payload 확장: `write_mode`, `seed_draft`, `seed_content_id` |
| Graph | `polish_draft` / `continue_draft`: plotter 스킵 또는 약화; writer/editor 프롬프트에 seed 주입 |
| 저장 | 완료 시 author_type=`hybrid` 권장 |

### FP-D. 씬 보드 Human Gate (P1)

| 항목 | 명세 |
| :--- | :--- |
| UI | Plotter 완료 후 또는 집필 전: 씬 카드 목록 (제목, plot, tension, pace) 편집·추가·삭제·순서 |
| 확정 | 「이 씬으로 집필」→ `scenes_locked` + writer 진입 |
| 상태 | 확정 scenes 를 thread state 에 기록; 체크포인트 재개 가능 |

### FP-E. 기획 제안 인라인 편집 (P1)

| 항목 | 명세 |
| :--- | :--- |
| UI | brainstorm 카드 필드 contenteditable / input |
| Apply | 수정된 name/description/keyword 를 apply payload 에 포함 |
| 기존 | change_type update / create 유지 |

### FP-F. 고급 Co-writing (P2)

- AI 안 ↔ 내 수정 **diff / 대조 편집기** (product_spec)
- 선택 구간 + 지시 → 부분 재작성 API
- 버전 트리 시각화·롤백
- 문단 코멘트 스레드

---

## 6. API · WebSocket 계약 (구현 시 준수)

### 6.1 REST — Content (1차, 기존 활용)

```http
POST /api/projects/{project_id}/episodes/{episode_id}/contents
Authorization: Bearer <jwt>
Content-Type: application/json

{
  "parent_id": 12,
  "version_tag": "v1.1-human",
  "text": "작가가 수정한 본문...",
  "author_type": "hybrid"
}
```

```http
PUT /api/projects/{project_id}/episodes/{episode_id}/contents/{content_id}/approve
```

선택 추가 (편의, Phase B):

```http
POST /api/projects/{project_id}/episodes/{episode_id}/contents/{content_id}/fork
# body: { "text": "...", "author_type": "hybrid", "version_tag": "..." }
# 서버가 parent_id=content_id 로 생성
```

### 6.2 WebSocket — start_writing 확장 (Phase C)

```json
{
  "action": "start_writing",
  "write_mode": "from_scratch",
  "seed_draft": null,
  "seed_content_id": null,
  "scenes": null
}
```

| 필드 | 기본 | 설명 |
| :--- | :--- | :--- |
| write_mode | `from_scratch` | 상단 표 참고 |
| seed_draft | null | 평문 초안 |
| seed_content_id | null | 있으면 서버가 Content.text 로드 |
| scenes | null | non-null 이면 scenes_locked 경로 |

응답 이벤트는 기존 `status_changed`, `text_stream`, `requires_user_review`, `done` 유지.

### 6.3 소유권·검증

- 모든 REST/WS: 프로젝트 소유 + episode 소속 검증 (기존 패턴)
- seed_content_id 는 해당 episode 소속이어야 함
- text 최대 길이: 구현 시 상한 검토 (예: 500k chars) — DoS 방지

---

## 7. UI/UX 명세 요약

### 7.1 회차 탭 (episodes.js)

- 버전 카드: [원문 보기] [✏️ 편집·저장] [최종본 승인]
- 편집 모달: 큰 textarea, 글자 수, parent 버전 표시, author_type 자동 hybrid(부모가 ai일 때)
- 빈 회차: [✍️ 직접 초안 작성] → user Content 생성 → 이후 「이 초안으로 윤문」진입 가능

### 7.2 집필 모니터 (writing-monitor.js)

- 헤더 모드: 전량 생성 | 초안 윤문 | 이어쓰기
- 초안 입력 영역 (윤문/이어쓰기 시)
- draft 패널: 보기 / 편집 토글
- HITL: [승인] [피드백 후 AI 수정] [내 수정 저장] [수정본 승인]

### 7.3 기획 파트너 (brainstorm.js)

- 카드 필드 인라인 편집
- 배지: 신규 / 기존 수정 / **직접 편집됨**

### 7.4 씬 보드 (신규 컴포넌트 또는 모니터 서브뷰)

- 카드 리스트 DnD 순서 (1차는 위/아래 버튼으로도 충분)
- 필드: title, plot, tension, pace
- [이 구성으로 집필 시작]

---

## 8. 구현 작업 계획 (마이크로 태스크)

> 스프린트 가칭: **Sprint 7-H — Human Editing & Co-writing**  
> 보드 반영 시 `sprint_board.md` 에 섹션 추가.

### Phase H1 — FP-A 본문 편집 저장 (P0) ⏱ 예상 0.5–1일

| Task ID | 작업 | 검증 수칙 |
| :--- | :--- | :--- |
| **H1-1** | `ContentCreate` author_type 문서·검증 (`ai\|user\|hybrid`) | 스키마/테스트 |
| **H1-2** | episodes.js: 버전 편집 모달 + POST contents + 목록 갱신 | 수동: 저장 후 배지 hybrid/user, parent 연결 |
| **H1-3** | 「저장 후 최종본 승인」 원클릭 | approve API 후 is_approved UI |
| **H1-4** | 「직접 초안 작성」(parent 없음, author_type=user) | 빈 회차에서 초안 생성 |
| **H1-5** | pytest: content create hybrid fork E2E (기존 auth fixture) | tests 통과 |

### Phase H2 — FP-B 집필실 에디터 (P0) ⏱ 예상 1일

| Task ID | 작업 | 검증 수칙 |
| :--- | :--- | :--- |
| **H2-1** | writing-monitor draft 편집 토글·textarea 바인딩 | 편집 후 로컬 상태 유지 |
| **H2-2** | waiting_user: 수정 저장 / 수정본 승인 REST 연동 | DB 버전 증가, 승인본 일치 |
| **H2-3** | 스트림 vs 편집 충돌 가드 | 편집 중 덮어쓰기 방지 토스트 |
| **H2-4** | 문서·개발 로그 갱신 | IMP/HE 항목 Done 표기 |

### Phase H3 — FP-C 초안 윤문 모드 (P1) ⏱ 예상 1.5–2일

| Task ID | 작업 | 검증 수칙 |
| :--- | :--- | :--- |
| **H3-1** | AgentState + start_writing payload `write_mode`/`seed_*` | 하위 호환 from_scratch |
| **H3-2** | graph 분기: polish/continue 시 plotter 스킵 | 단위 테스트 route |
| **H3-3** | Writer/Editor 프롬프트 seed 주입 | mock agent 테스트 |
| **H3-4** | 모니터 UI 모드 선택 + 초안 입력 | 수동 스모크 |
| **H3-5** | seed_content_id 로드·소유권 검증 | 403/400 케이스 |

### Phase H4 — FP-D 씬 보드 게이트 (P1) ⏱ 예상 1.5–2일

| Task ID | 작업 | 검증 수칙 |
| :--- | :--- | :--- |
| **H4-1** | Plotter 후 interrupt 또는 클라이언트 측 씬 확정 UX 결정 (권장: 클라이언트 확정 후 scenes_locked start) | 설계 ADR 한 줄 로그 |
| **H4-2** | 씬 보드 UI 컴포넌트 | 편집·순서 |
| **H4-3** | start_writing scenes 주입 경로 | Writer가 확정 씬만 사용 |
| **H4-4** | E2E: outline → 수동 씬 → 집필 | 통합 테스트 또는 수동 체크리스트 |

### Phase H5 — FP-E 기획 인라인 편집 (P1) ⏱ 예상 0.5일

| Task ID | 작업 | 검증 수칙 |
| :--- | :--- | :--- |
| **H5-1** | brainstorm 카드 필드 편집 | apply 시 수정문 반영 |
| **H5-2** | apply API 가 클라이언트 수정 필드를 존중하는지 확인 | 단위/E2E |

### Phase H6 — FP-F 고급 (P2, 백로그)

| Task ID | 작업 |
| :--- | :--- |
| **H6-1** | diff 대조 편집기 |
| **H6-2** | 선택 구간 부분 재작성 |
| **H6-3** | 버전 트리 시각화 |

---

## 9. 권장 착수 순서

```
H1 (본문 편집 저장)     ← 즉시 체감, API 준비됨
  → H2 (집필실 에디터)  ← HITL과 연결
  → H3 (초안 윤문)      ← “내 글 기반” 코라이팅
  → H5 (기획 인라인)    ← 저비용 정합
  → H4 (씬 보드)        ← 그래프 변경 동반
  → H6 (고급)
```

IMP-02(마이그레이션 UI) 등과 **병행 가능**. 작가 주도권 ROI 는 H1–H3 이 더 높다.

---

## 10. 테스트 · 완료 기준

### 10.1 H1 완료 정의

- [ ] 임의의 Content 버전을 편집해 새 버전이 생기고 parent_id 가 연결된다
- [ ] author_type 이 user/hybrid 로 저장·표시된다
- [ ] 저장 후 최종본 승인 시 해당 텍스트가 다운로드/컴파일에 사용된다
- [ ] 타 유저 episode 에 write 시 403

### 10.2 H2 완료 정의

- [ ] waiting_user 에서 본문 수정 후 AI 재실행 없이 승인 가능하다
- [ ] 편집 중 스트림이 작성 중 텍스트를 침묵 덮어쓰지 않는다

### 10.3 H3 완료 정의

- [ ] polish_draft 로 넣은 초안의 핵심 문장·사건이 결과 draft 에 반영된다 (수동 품질 스모크)
- [ ] write_mode 생략 시 기존 from_scratch 와 동일 동작

---

## 11. 리스크와 완화

| 리스크 | 완화 |
| :--- | :--- |
| 장문 textarea 성능 | 가상 스크롤은 후순위; 우선 단일 textarea + max length |
| Graph state 와 DB 버전 불일치 | H1–H2 는 REST 정본; WS draft 는 표시용 |
| polish 모드 품질 편차 | 프롬프트에 “삭제 금지 핵심 / 윤문 범위” 명시 |
| 씬 보드 + checkpoint 복잡도 | H4 는 클라이언트 확정 scenes 주입부터 |
| 자동 저장 유실 | 명시적 저장 버튼; 이탈 시 beforeunload 경고 (H2) |

---

## 12. 명시적 비목표 (이 설계 범위 밖)

- 실시간 협업 커서 (다중 작가 OT/CRDT)
- 모바일 네이티브 앱
- 외부 워드프로세서 플러그인
- AI 없이 동작하는 완전 오프라인 전용 에디터

---

## 13. 문서·보드 연동

| 문서 | 조치 |
| :--- | :--- |
| 본 파일 | 설계·계획 정본 |
| `post_mvp_review_and_backlog_2026-07-26.md` | HE/IMP 교차 참조, RW-12 연결 |
| `sprint_board.md` | 착수 시 Sprint 7-H 섹션 추가 |
| `development_log.md` | 페이즈 완료 시 로그 |
| `product_spec.md` | Writing View 충족은 H1–H2 이후 “부분 충족” 표기 가능 |

---

## 14. 변경 이력

| 날짜 | 내용 |
| :--- | :--- |
| 2026-07-26 | 초안 — 문제 정의, 원칙, FP-A~F, Phase H1–H6, API/WS 계약, 검증 기준 |
