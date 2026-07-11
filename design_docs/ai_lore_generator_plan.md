# AI 세계관 & 캐릭터 공동 기획 에이전트 — 실무 구현 청사진 v2

> **목적**: 프로젝트 시놉시스를 기반으로 AI가 세계관(Lorebook)과 캐릭터를 추천 기획하고,
> 사용자 피드백을 반영해 점진적으로 고도화한 뒤, 선택 항목만 DB에 영속화하는 기능.

---

## 0. 기존 코드 패턴 요약 (구현 시 반드시 준수)

본 섹션은 기존 코드베이스를 분석하여 도출한 **실제 패턴**입니다.
계획서의 모든 코드는 이 패턴을 100% 따릅니다.

| 항목 | 실제 패턴 |
|------|-----------|
| **에이전트 클래스** | `SYSTEM_PROMPT` 클래스 상수 → `__init__(self, model: BaseChatModel)` → `self.chain = prompt \| structured_model` → `async def run(...)` |
| **구조화 출력 스키마** | `agents.py` 파일 상단에 `Pydantic BaseModel`로 정의 |
| **`check_project_owner`** | **FastAPI Depends가 아님**. 일반 async 함수로 직접 호출: `project = await check_project_owner(project_id, current_user, session)` |
| **`get_current_user`** | FastAPI `Depends`로 주입: `current_user: User = Depends(get_current_user)` |
| **`LLMFactory.get_model_for_agent`** | `(project_orm_instance, "agent_type_str")` → 내부에서 복호화까지 처리 |
| **`WorldSetting` 모델** | `id`, `project_id`, `keyword`, `category`, `description`, `embedding` — **`is_active` 필드 없음** |
| **`Character` 모델** | `id`, `project_id`, `name`, `description`, `importance` |
| **`ui/api_client.py`** | 동기 `requests` 라이브러리 사용. `requests.Response` 원시 반환 |
| **에러 핸들링** | 에이전트 내부에는 try/except 없음. 라우터에서 `HTTPException`으로 포장 |

> [!CAUTION]
> 이전 계획서의 오류 목록:
> - `WorldSetting` 생성 시 `is_active=True` 사용 → **필드 존재하지 않음** (제거)
> - `check_project_owner`를 `Depends()`로 사용 → **일반 함수** (직접 호출로 수정)
> - 스키마를 `app/schemas/project.py`에 추가 → 에이전트 출력 스키마는 `app/services/agents.py` 상단에 위치 (프로젝트 관례)
> - 라우터 import에 `from app.core.dependencies import check_project_owner` 누락 → 추가
> - 브레인스토밍 라우터를 `project.py`에 합치려 함 → **별도 라우터 파일로 분리**가 기존 구조와 일관 (character.py, episode.py 등 분리 패턴)

---

## 1. 아키텍처 및 데이터 흐름

```mermaid
sequenceDiagram
    autonumber
    actor User as 사용자 (Streamlit)
    participant UI as ui/project_view.py
    participant Client as ui/api_client.py
    participant Router as app/routers/brainstorm.py
    participant Deps as app/core/dependencies.py
    participant Factory as app/services/llm_factory.py
    participant Agent as BrainstormAgent
    database DB as PostgreSQL

    User->>UI: [💡 AI 기획 파트너] 탭 → 피드백 입력 → [🤖 기획 기동] 클릭
    UI->>Client: post_brainstorm(project_id, payload)
    Client->>Router: POST /projects/{id}/brainstorm (JSON body)
    Router->>Deps: await check_project_owner(project_id, current_user, session)
    Deps-->>Router: Project ORM 인스턴스 반환
    Router->>Factory: LLMFactory.get_model_for_agent(project, "plotter")
    Factory-->>Router: BaseChatModel 인스턴스
    Router->>Agent: BrainstormAgent(model).run(title, synopsis, instruction, lores, chars)
    Agent->>Agent: 프롬프트 조합 → with_structured_output → ainvoke
    Agent-->>Router: BrainstormResult (Pydantic)
    Router-->>Client: 200 OK (JSON)
    Client-->>UI: requests.Response
    UI->>UI: session_state에 결과 저장 → 체크박스/편집 폼 렌더링

    Note over User, UI: 사용자가 만족할 때까지 피드백 루프 반복

    User->>UI: 체크박스 선택 → [💾 저장] 클릭
    UI->>Client: apply_brainstorm(project_id, payload)
    Client->>Router: POST /projects/{id}/brainstorm/apply (JSON body)
    Router->>Deps: await check_project_owner(...)
    Router->>DB: WorldSetting / Character 벌크 INSERT
    Router->>DB: await session.commit()
    Router-->>Client: 200 OK
    Client-->>UI: 성공 응답
    UI->>User: 토스트 알림 + 세계관/캐릭터 탭 자동 리프레시
```

---

## 2. 파일별 상세 작업 명세

### Task 1: 에이전트 출력 스키마 & BrainstormAgent 추가

**대상 파일**: `app/services/agents.py`
**작업 위치**: 파일 상단 기존 스키마(ScenePlan, EpisodePlan 등) 뒤에 추가, 파일 하단에 클래스 추가

#### 2.1.1 출력 스키마 (파일 상단, 기존 `ReviewReport` 클래스 뒤)

```python
# ── Brainstorm 출력 스키마 ──────────────────────────────────────
class LoreSuggestion(BaseModel):
    keyword: str = Field(description="세계관 키워드 (예: 오르비스 제국, 마나 크리스탈)")
    category: str = Field(description="카테고리: 'lore', 'location', 'item' 중 하나")
    description: str = Field(description="세계관 설정에 대한 구체적인 설명 (2~4문장)")

class CharacterSuggestion(BaseModel):
    name: str = Field(description="캐릭터 이름")
    importance: str = Field(description="중요도: 'protagonist', 'deuteragonist', 'major', 'minor' 중 하나")
    description: str = Field(description="외양, 성격, 배경, 동기 등 상세 묘사 (3~5문장)")

class BrainstormResult(BaseModel):
    lores: List[LoreSuggestion] = Field(description="추천 세계관 설정 목록 (3~5개)")
    characters: List[CharacterSuggestion] = Field(description="추천 캐릭터 목록 (3~4명)")
```

#### 2.1.2 BrainstormAgent 클래스 (파일 하단, 기존 `ReviewerAgent` 뒤)

```python
class BrainstormAgent:
    """프로젝트 시놉시스 기반 세계관 & 캐릭터 공동 기획 에이전트."""

    SYSTEM_PROMPT = """당신은 베스트셀러 웹소설과 판타지 소설을 기획하는 전문 스토리 아키텍트입니다.
사용자가 제공하는 소설 프로젝트의 제목과 시놉시스를 깊이 분석하여, 그 세계관을 풍성하게 만들 매력적인 설정과 캐릭터를 추천 및 기획합니다.

[작동 규칙]
1. 시놉시스와 자연스럽게 연결되며 작품의 깊이를 더해줄 세계관 설정(Lorebook) 3~5개와 개성 넘치는 캐릭터 3~4명을 기획하세요.
2. 만약 기존 기획안과 사용자 피드백이 주어진다면, 피드백을 충실히 반영하여 기존 기획안을 수정·개선·확장하세요.
3. 세계관 카테고리는 반드시 'lore'(역사/법칙), 'location'(지리/공간), 'item'(아이템/마법 도구) 중 하나만 사용하세요.
4. 캐릭터 중요도는 반드시 'protagonist', 'deuteragonist', 'major', 'minor' 중 하나만 사용하세요.
5. 모든 설명은 소설 집필 시 바로 활용될 수 있을 만큼 구체적이고 매력적으로 작성하세요.
6. 기존 세계관/캐릭터가 있을 경우 서로 모순이 없도록 통합적으로 설계하세요."""

    def __init__(self, model: BaseChatModel):
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.SYSTEM_PROMPT),
            ("human", (
                "[소설 기본 정보]\n"
                "- 제목: {title}\n"
                "- 시놉시스: {synopsis}\n\n"
                "[이전 기획안 (있을 경우)]\n"
                "- 기존 세계관:\n{existing_lores}\n"
                "- 기존 캐릭터:\n{existing_characters}\n\n"
                "[사용자 피드백 / 추가 요청]\n"
                "{instruction}\n\n"
                "위 정보를 종합하여, 매력적인 세계관 설정과 등장인물 시트를 작성해 주세요."
            ))
        ])
        structured_model = model.with_structured_output(BrainstormResult)
        self.chain = prompt | structured_model

    async def run(
        self,
        project_title: str,
        project_synopsis: str,
        user_instruction: Optional[str] = None,
        current_lores: Optional[List[dict]] = None,
        current_characters: Optional[List[dict]] = None,
    ) -> BrainstormResult:
        # 기존 기획안을 사람이 읽기 쉬운 문자열로 직렬화
        lores_str = "(없음)"
        if current_lores:
            lores_str = "\n".join(
                f"  - [{l['category']}] {l['keyword']}: {l['description']}"
                for l in current_lores
            )

        chars_str = "(없음)"
        if current_characters:
            chars_str = "\n".join(
                f"  - {c['name']} ({c['importance']}): {c['description']}"
                for c in current_characters
            )

        instruction_str = user_instruction or "시놉시스를 분석하여 기본 세계관과 캐릭터를 자유롭게 창작해 주세요."

        result = await self.chain.ainvoke({
            "title": project_title,
            "synopsis": project_synopsis,
            "existing_lores": lores_str,
            "existing_characters": chars_str,
            "instruction": instruction_str,
        })
        return result
```

> [!IMPORTANT]
> **`current_lores`, `current_characters` 파라미터 타입이 `List[dict]`인 이유**:
> UI(Streamlit)의 `st.session_state`에서 넘어오는 데이터는 Pydantic 모델이 아닌 plain dict이므로,
> 라우터에서 dict 그대로 에이전트에 전달하는 것이 가장 간결합니다.
> 에이전트 내부에서는 문자열 직렬화만 수행하므로 dict로 충분합니다.

---

### Task 2: 요청/응답 DTO 추가

**대상 파일**: `app/schemas/project.py`
**작업 위치**: 파일 하단에 추가

```python
# ── Brainstorm DTO ──────────────────────────────────────────────
class BrainstormLoreItem(BaseModel):
    keyword: str
    category: str
    description: str

class BrainstormCharItem(BaseModel):
    name: str
    importance: str
    description: str

class BrainstormRequest(BaseModel):
    user_instruction: Optional[str] = None
    current_lores: Optional[list] = Field(default_factory=list)
    current_characters: Optional[list] = Field(default_factory=list)

class BrainstormApplyRequest(BaseModel):
    lores: list = Field(default_factory=list)
    characters: list = Field(default_factory=list)
```

> [!NOTE]
> `BrainstormLoreItem`, `BrainstormCharItem`은 `/brainstorm/apply` 엔드포인트의
> 요청 유효성 검증용으로도 사용할 수 있지만, MVP에서는 plain list로 수신하여 코드 단순성을 유지합니다.
> 향후 `List[BrainstormLoreItem]`으로 타입을 강화할 수 있습니다.

---

### Task 3: 브레인스토밍 전용 라우터 신설

**대상 파일**: `app/routers/brainstorm.py` ← **신규 생성**

> [!IMPORTANT]
> 기존 프로젝트 구조에서 `character.py`, `episode.py`, `world_setting.py` 등
> 서브 리소스별로 라우터를 분리하는 패턴을 따릅니다.
> `project.py`에 합치지 않고 별도 파일로 분리합니다.

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_async_session
from app.core.dependencies import get_current_user, check_project_owner
from app.models import User, WorldSetting, Character
from app.schemas.project import BrainstormRequest, BrainstormApplyRequest
from app.services.llm_factory import LLMFactory
from app.services.agents import BrainstormAgent

router = APIRouter(
    prefix="/projects/{project_id}/brainstorm",
    tags=["Brainstorm"],
)


@router.post("")
async def brainstorm_lore_and_characters(
    project_id: int,
    req: BrainstormRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """AI 기획 에이전트가 세계관 설정과 캐릭터를 추천 생성합니다."""

    # 1. 소유권 검증 및 프로젝트 ORM 획득
    project = await check_project_owner(project_id, current_user, session)

    # 2. 시놉시스 검증
    if not project.synopsis or not project.synopsis.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="프로젝트 시놉시스가 비어 있습니다. [프로젝트 설정]에서 시놉시스를 먼저 입력해 주세요.",
        )

    # 3. 기획(Plotter) 에이전트 전용 LLM 로드 (Fallback 적용)
    try:
        model = LLMFactory.get_model_for_agent(project, "plotter")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"LLM 모델 생성 실패: {e}. 프로젝트 설정에서 API Key가 올바르게 설정되어 있는지 확인하세요.",
        )

    # 4. 에이전트 구동
    agent = BrainstormAgent(model)
    try:
        result = await agent.run(
            project_title=project.title,
            project_synopsis=project.synopsis,
            user_instruction=req.user_instruction,
            current_lores=req.current_lores,
            current_characters=req.current_characters,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"브레인스토밍 에이전트 실행 중 오류: {e}",
        )

    # 5. Pydantic → dict 변환 후 반환
    return result.model_dump()


@router.post("/apply")
async def apply_brainstorm_results(
    project_id: int,
    req: BrainstormApplyRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """사용자가 선택한 기획안을 프로젝트 DB에 일괄 저장합니다."""

    # 1. 소유권 검증
    await check_project_owner(project_id, current_user, session)

    # 2. 세계관 일괄 저장
    added_lores = 0
    for lore in req.lores:
        db_lore = WorldSetting(
            project_id=project_id,
            keyword=lore["keyword"],
            category=lore["category"],
            description=lore["description"],
        )
        session.add(db_lore)
        added_lores += 1

    # 3. 캐릭터 일괄 저장
    added_characters = 0
    for char in req.characters:
        db_char = Character(
            project_id=project_id,
            name=char["name"],
            importance=char["importance"],
            description=char["description"],
        )
        session.add(db_char)
        added_characters += 1

    # 4. 커밋
    try:
        await session.commit()
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"데이터베이스 저장 실패: {e}",
        )

    return {
        "status": "success",
        "added_lores": added_lores,
        "added_characters": added_characters,
    }
```

---

### Task 4: 라우터 등록

**대상 파일**: `app/main.py`
**작업 내용**: 기존 라우터 import 블록에 1줄 추가, `app.include_router()` 블록에 1줄 추가

```python
# import 블록에 추가
from app.routers import brainstorm

# include_router 블록에 추가
app.include_router(brainstorm.router)
```

> [!NOTE]
> 기존에 `from app.routers import project, character, episode, ...` 패턴으로
> 임포트하고 있으므로 동일 패턴을 따릅니다.

---

### Task 5: API 클라이언트 함수 추가

**대상 파일**: `ui/api_client.py`
**작업 위치**: 파일 하단에 2개 함수 추가

```python
# ── Brainstorm API ──────────────────────────────────────────────
def post_brainstorm(project_id, payload):
    """AI 기획 에이전트 호출 (세계관 + 캐릭터 추천 생성)"""
    return requests.post(
        f"{BASE_URL}/projects/{project_id}/brainstorm",
        json=payload,
        headers=get_headers(),
    )

def apply_brainstorm(project_id, payload):
    """선택된 기획안을 프로젝트 DB에 일괄 저장"""
    return requests.post(
        f"{BASE_URL}/projects/{project_id}/brainstorm/apply",
        json=payload,
        headers=get_headers(),
    )
```

---

### Task 6: Streamlit UI — 신규 탭 추가

**대상 파일**: `ui/project_view.py`

#### 6.1 탭 선언 변경 (기존 4탭 → 5탭)

**변경 전** (line 16):
```python
tab1, tab2, tab3, tab4 = st.tabs(["세계관 (Lorebook)", "캐릭터 시트", "회차 관리", "프로젝트 설정"])
```

**변경 후**:
```python
tab0, tab1, tab2, tab3, tab4 = st.tabs(["💡 AI 기획 파트너", "세계관 (Lorebook)", "캐릭터 시트", "회차 관리", "프로젝트 설정"])
```

> [!IMPORTANT]
> **`tab0`을 첫 번째 탭으로 배치하는 이유**:
> 프로젝트 진입 직후 가장 먼저 해야 하는 작업이 세계관/캐릭터 기획이므로
> 사용자 동선상 가장 앞에 노출되어야 합니다.
> 기존 `tab1~tab4`의 변수명과 내부 코드에는 변경 없이 유지합니다.

#### 6.2 신규 탭 렌더링 블록 (기존 `with tab1:` 바로 위에 삽입)

```python
with tab0:
    st.subheader("💡 AI 기획 파트너")
    st.caption("프로젝트 시놉시스를 분석하여 세계관 설정집과 등장인물 시트 초안을 AI와 함께 만듭니다.")

    # ── 시놉시스 미입력 가드 ──
    synopsis_text = p.get("synopsis", "") if p else ""
    if not synopsis_text or not synopsis_text.strip():
        st.warning("⚠️ 프로젝트 시놉시스가 비어 있습니다. [프로젝트 설정] 탭에서 시놉시스를 먼저 입력해 주세요.")
    else:
        with st.expander("📖 현재 시놉시스 확인", expanded=False):
            st.markdown(synopsis_text)

        # ── 피드백 입력 ──
        user_feedback = st.text_area(
            "🎯 기획 방향 지시 및 피드백",
            placeholder="예: '주인공 가문을 마검사 혈통으로 설정해줘', '북유럽 신화 느낌의 지명을 사용해줘', '라이벌 캐릭터를 1명 추가해줘'",
            key="bs_feedback_input",
        )

        col_gen, col_clear = st.columns([3, 1])
        with col_gen:
            generate_clicked = st.button(
                "🤖 AI 공동 기획 기동" if not st.session_state.get("bs_lores") else "🔄 피드백 반영 재기획",
                type="primary",
                use_container_width=True,
            )
        with col_clear:
            if st.session_state.get("bs_lores") or st.session_state.get("bs_chars"):
                if st.button("🗑️ 초기화", use_container_width=True):
                    st.session_state["bs_lores"] = []
                    st.session_state["bs_chars"] = []
                    st.rerun()

        if generate_clicked:
            with st.spinner("에이전트가 세계관과 캐릭터를 구상하는 중입니다..."):
                payload = {
                    "user_instruction": user_feedback if user_feedback else None,
                    "current_lores": st.session_state.get("bs_lores", []),
                    "current_characters": st.session_state.get("bs_chars", []),
                }
                try:
                    res = api_client.post_brainstorm(project_id, payload)
                    if res.status_code == 200:
                        data = res.json()
                        st.session_state["bs_lores"] = data.get("lores", [])
                        st.session_state["bs_chars"] = data.get("characters", [])
                        st.rerun()
                    else:
                        error_detail = res.json().get("detail", res.text) if res.headers.get("content-type", "").startswith("application/json") else res.text
                        st.error(f"기획 생성 실패: {error_detail}")
                except Exception as e:
                    st.error(f"API 요청 오류: {e}")

        # ── 기획안 결과 뷰어 ──
        bs_lores = st.session_state.get("bs_lores", [])
        bs_chars = st.session_state.get("bs_chars", [])

        if bs_lores or bs_chars:
            st.markdown("---")
            st.markdown("### 📝 제안된 기획안 검토")
            st.caption("체크박스를 해제하면 저장 시 제외됩니다. 텍스트를 직접 수정할 수도 있습니다.")

            left_col, right_col = st.columns(2)
            selected_lores = []
            selected_chars = []

            with left_col:
                st.markdown("#### 🌍 추천 세계관 설정")
                category_options = ["lore", "location", "item"]
                for i, lore in enumerate(bs_lores):
                    with st.container(border=True):
                        keep = st.checkbox(f"세계관 #{i+1} 포함", value=True, key=f"keep_lore_{i}")
                        kw = st.text_input("키워드", value=lore.get("keyword", ""), key=f"bs_lk_{i}")
                        try:
                            cat_idx = category_options.index(lore.get("category", "lore"))
                        except ValueError:
                            cat_idx = 0
                        cat = st.selectbox("카테고리", category_options, index=cat_idx, key=f"bs_lc_{i}")
                        desc = st.text_area("설명", value=lore.get("description", ""), key=f"bs_ld_{i}", height=120)
                        if keep:
                            selected_lores.append({"keyword": kw, "category": cat, "description": desc})

            with right_col:
                st.markdown("#### 👥 추천 등장인물")
                importance_options = ["protagonist", "deuteragonist", "major", "minor"]
                for i, char in enumerate(bs_chars):
                    with st.container(border=True):
                        keep = st.checkbox(f"캐릭터 #{i+1} 포함", value=True, key=f"keep_char_{i}")
                        name = st.text_input("이름", value=char.get("name", ""), key=f"bs_cn_{i}")
                        try:
                            imp_idx = importance_options.index(char.get("importance", "minor"))
                        except ValueError:
                            imp_idx = 3
                        imp = st.selectbox("중요도", importance_options, index=imp_idx, key=f"bs_ci_{i}")
                        desc = st.text_area("묘사", value=char.get("description", ""), key=f"bs_cd_{i}", height=120)
                        if keep:
                            selected_chars.append({"name": name, "importance": imp, "description": desc})

            st.markdown("---")

            # ── 저장 요약 & 확인 ──
            st.info(f"💾 저장 대상: 세계관 설정 **{len(selected_lores)}개**, 캐릭터 **{len(selected_chars)}명**")

            if st.button("💾 선택한 기획안을 프로젝트에 영구 저장", type="primary", use_container_width=True):
                if not selected_lores and not selected_chars:
                    st.warning("저장할 항목이 없습니다. 체크박스를 1개 이상 선택해 주세요.")
                else:
                    with st.spinner("데이터베이스에 저장하는 중..."):
                        try:
                            res = api_client.apply_brainstorm(
                                project_id,
                                {"lores": selected_lores, "characters": selected_chars},
                            )
                            if res.status_code == 200:
                                result = res.json()
                                st.success(
                                    f"✅ 저장 완료! 세계관 {result['added_lores']}개, "
                                    f"캐릭터 {result['added_characters']}명이 프로젝트에 추가되었습니다."
                                )
                                # 세션 버퍼 클리어
                                st.session_state["bs_lores"] = []
                                st.session_state["bs_chars"] = []
                                st.rerun()
                            else:
                                st.error(f"저장 실패: {res.text}")
                        except Exception as e:
                            st.error(f"API 요청 오류: {e}")
```

> [!NOTE]
> **`p` 변수 참조**: 기존 코드에서 `tab4`(프로젝트 설정) 내에서 `p = p_res.json()`으로
> 프로젝트 정보를 로드하고 있습니다. `tab0`에서도 시놉시스를 참조해야 하므로,
> 프로젝트 정보 로딩 로직을 **탭 바깥(상단)으로 끌어올려** 모든 탭에서 공유하도록
> 리팩토링이 필요합니다. (현재 line 161~170의 프로젝트 조회 블록을 line 16 앞으로 이동)

---

### Task 7: 프로젝트 정보 로딩 리팩토링

**대상 파일**: `ui/project_view.py`

현재 프로젝트 정보(`p`)는 `tab4` 내부에서만 로드됩니다.
`tab0`에서 시놉시스를 참조해야 하므로 로딩을 탭 선언 전으로 이동합니다.

**변경 전** (line 159~170, tab4 내부):
```python
with tab4:
    st.subheader("⚙️ 프로젝트 LLM 및 정보 설정")
    try:
        p_res = api_client.get_project(project_id)
        if p_res.status_code == 200:
            p = p_res.json()
        else:
            st.error("프로젝트 상세 정보를 조회하지 못했습니다.")
            p = {}
    except Exception as e:
        st.error(f"오류 발생: {e}")
        p = {}
```

**변경 후** — 프로젝트 데이터 로딩을 `render()` 함수 진입 직후, 탭 선언 직전으로 이동:
```python
def render(project_id, project_title):
    st.title(f"📚 {project_title}")

    # ... 대시보드 버튼 ...

    # ── 프로젝트 정보 로딩 (모든 탭에서 공유) ──
    try:
        p_res = api_client.get_project(project_id)
        if p_res.status_code == 200:
            p = p_res.json()
        else:
            st.error("프로젝트 상세 정보를 조회하지 못했습니다.")
            p = {}
    except Exception as e:
        st.error(f"오류 발생: {e}")
        p = {}

    tab0, tab1, tab2, tab3, tab4 = st.tabs([...])

    with tab0:
        # ... AI 기획 파트너 (p 변수 사용 가능) ...

    # ...

    with tab4:
        st.subheader("⚙️ 프로젝트 LLM 및 정보 설정")
        # p 변수는 이미 로드됨 — 기존 try/except 블록 제거
        if p:
            # ... 이하 기존 코드 유지 ...
```

---

## 3. Session State 관리 명세

| 변수명 | 타입 | 초기값 | 용도 |
|--------|------|--------|------|
| `bs_lores` | `List[dict]` | `[]` | AI가 추천한 세계관 설정 임시 보관 |
| `bs_chars` | `List[dict]` | `[]` | AI가 추천한 캐릭터 임시 보관 |
| `bs_feedback_input` | `str` | `""` | Streamlit widget key (자동 관리) |

> [!NOTE]
> 이전 버전에 있던 `bs_instruction`, `bs_loading`은 불필요합니다.
> - `bs_instruction`: Streamlit의 `text_area` widget이 `key`를 통해 자동으로 상태 관리합니다.
> - `bs_loading`: `st.spinner`를 사용하므로 별도 플래그가 필요 없습니다.

---

## 4. 예외 케이스 대응 전략

| # | 시나리오 | 대응 레이어 | 처리 방식 |
|---|----------|------------|-----------|
| 1 | 시놉시스 미입력 | UI (`tab0`) + 백엔드 | UI: `st.warning` + 버튼 숨김. 백엔드: `400 Bad Request` |
| 2 | API Key 미설정 | 백엔드 라우터 | `LLMFactory` 예외 → `400` 응답 + 설정 안내 메시지 |
| 3 | LLM 구조화 출력 파싱 실패 | 백엔드 라우터 | `except Exception` → `500` 응답 + UI에서 재시도 유도 |
| 4 | LLM이 잘못된 카테고리/중요도 반환 | UI 렌더링 | `selectbox` index에 `try/except ValueError` → 기본값 fallback |
| 5 | 저장할 항목이 0개인 상태로 저장 클릭 | UI | `st.warning("저장할 항목이 없습니다")` 표시 |
| 6 | DB 커밋 실패 | 백엔드 라우터 | `await session.rollback()` → `500` 응답 |
| 7 | 피드백 루프에서 이전 기획안 체크박스 key 충돌 | UI | 세션 클리어 후 `st.rerun()`으로 위젯 키 초기화 |

---

## 5. 작업 순서 체크리스트

구현은 아래 순서대로 진행하며, 각 단계가 완료된 후 다음 단계로 넘어갑니다.

- [ ] **Step 1**: `app/services/agents.py` — 스키마 3개 + `BrainstormAgent` 클래스 추가
- [ ] **Step 2**: `app/schemas/project.py` — `BrainstormRequest`, `BrainstormApplyRequest` DTO 추가
- [ ] **Step 3**: `app/routers/brainstorm.py` — 신규 파일 생성 (2개 엔드포인트)
- [ ] **Step 4**: `app/main.py` — 라우터 import 및 등록 1줄씩 추가
- [ ] **Step 5**: `ui/api_client.py` — `post_brainstorm`, `apply_brainstorm` 함수 2개 추가
- [ ] **Step 6**: `ui/project_view.py` — 프로젝트 정보 로딩 리팩토링 (tab4 내부 → 상단 공통)
- [ ] **Step 7**: `ui/project_view.py` — 탭 5개로 확장 + `tab0` AI 기획 파트너 UI 렌더링
- [ ] **Step 8**: `tests/test_agents.py` — `BrainstormAgent` 단위 테스트 추가 (모킹)
- [ ] **Step 9**: 로컬 E2E 수동 테스트 (Docker 기동 → run_local_test.py → 브레인스토밍 실행)
- [ ] **Step 10**: Git commit & push

---

## 6. 테스트 케이스 명세

### 6.1 단위 테스트 (`tests/test_agents.py`)

```python
@pytest.mark.asyncio
async def test_brainstorm_agent_run():
    """BrainstormAgent가 BrainstormResult 구조체를 올바르게 반환하는지 검증"""
    mock_result = BrainstormResult(
        lores=[
            LoreSuggestion(keyword="마나 크리스탈", category="item", description="..."),
        ],
        characters=[
            CharacterSuggestion(name="카이론", importance="protagonist", description="..."),
        ],
    )

    mock_model = AsyncMock()
    mock_structured = AsyncMock()
    mock_structured.ainvoke = AsyncMock(return_value=mock_result)
    mock_model.with_structured_output = MagicMock(return_value=mock_structured)

    # with_structured_output 호출 시 prompt | structured_model 체인 모킹
    with patch("app.services.agents.ChatPromptTemplate") as mock_prompt_cls:
        mock_prompt_instance = MagicMock()
        mock_prompt_cls.from_messages.return_value = mock_prompt_instance
        mock_prompt_instance.__or__ = MagicMock(return_value=mock_structured)

        agent = BrainstormAgent(mock_model)
        result = await agent.run(
            project_title="테스트 소설",
            project_synopsis="마법 학교에 입학한 소년의 모험",
        )

    assert isinstance(result, BrainstormResult)
    assert len(result.lores) >= 1
    assert len(result.characters) >= 1
    assert result.lores[0].category in ("lore", "location", "item")
    assert result.characters[0].importance in ("protagonist", "deuteragonist", "major", "minor")
```

### 6.2 수동 E2E 테스트 시나리오

| # | 시나리오 | 기대 결과 |
|---|----------|-----------|
| 1 | 시놉시스 있는 프로젝트에서 빈 피드백으로 기획 기동 | 세계관 3~5개 + 캐릭터 3~4명 제안 |
| 2 | 제안된 결과에 "캐릭터 1명 추가해줘" 피드백 후 재기획 | 기존 + 1명 추가된 결과 반환 |
| 3 | 체크박스 2개 해제 후 저장 | 해제된 항목은 DB에 저장되지 않음 |
| 4 | 저장 후 세계관/캐릭터 탭 확인 | 저장된 항목이 목록에 정상 출력 |
| 5 | 시놉시스 비어있는 프로젝트에서 기획 시도 | `st.warning` 표시, 버튼 비활성 |
