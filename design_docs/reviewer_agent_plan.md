# 📋 AI 평가 에이전트(ReviewerAgent) 도입 및 에이전트별 LLM 분리 설정 세부 계획서 (실무용)

본 계획서는 소설 자동 집필 시스템의 핵심 품질 강화를 위해 **회차 전체 종합 평가 에이전트(ReviewerAgent)**를 구현하고, 에피소드 기획·집필·검수·윤문·평가 각 단계에 개별 LLM을 튜닝할 수 있는 **에이전트별 LLM 분리 설정 기능**을 시스템에 녹여내기 위한 실무 엔지니어링 명세서입니다.

---

## 1. 데이터베이스 모델 및 스키마 변경 계획

### 1.1 `app/models.py` (Project 테이블 확장)
`Project` 클래스에 에이전트별 오버라이드 설정을 위한 컬럼을 추가합니다. 모든 API 키는 `Fernet` 대칭키로 저장 시점에 암호화 처리됩니다.

```python
# app/models.py
from typing import Optional
from sqlmodel import SQLModel, Field

class Project(SQLModel, table=True):
    # ... 기존 필드 (id, user_id, title, synopsis, llm_provider, llm_model, api_key_override, created_at) ...

    # 1) Plotter Agent (기획) 오버라이드 설정
    plotter_provider: Optional[str] = Field(default=None, nullable=True)
    plotter_model: Optional[str] = Field(default=None, nullable=True)
    plotter_api_key: Optional[str] = Field(default=None, nullable=True)

    # 2) Writer Agent (집필) 오버라이드 설정
    writer_provider: Optional[str] = Field(default=None, nullable=True)
    writer_model: Optional[str] = Field(default=None, nullable=True)
    writer_api_key: Optional[str] = Field(default=None, nullable=True)

    # 3) Judge Agent (모순 감지) 오버라이드 설정
    judge_provider: Optional[str] = Field(default=None, nullable=True)
    judge_model: Optional[str] = Field(default=None, nullable=True)
    judge_api_key: Optional[str] = Field(default=None, nullable=True)

    # 4) Editor Agent (교정/윤문) 오버라이드 설정
    editor_provider: Optional[str] = Field(default=None, nullable=True)
    editor_model: Optional[str] = Field(default=None, nullable=True)
    editor_api_key: Optional[str] = Field(default=None, nullable=True)

    # 5) Reviewer Agent (종합 평가) 오버라이드 설정
    reviewer_provider: Optional[str] = Field(default=None, nullable=True)
    reviewer_model: Optional[str] = Field(default=None, nullable=True)
    reviewer_api_key: Optional[str] = Field(default=None, nullable=True)
```

### 1.2 `scripts/migrate_agent_llm_fields.py` (DB 마이그레이션 스크립트)
로컬 SQLite 및 PostgreSQL 개발 DB의 데이터 손실을 방지하기 위한 컬럼 추가 마이그레이션 스크립트입니다.

```python
# scripts/migrate_agent_llm_fields.py
import asyncio
import os
import sys
from sqlalchemy import text

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.core.database import async_engine

async def run_migration():
    agents = ["plotter", "writer", "judge", "editor", "reviewer"]
    async with async_engine.begin() as conn:
        print("Starting Project table migration...")
        for agent in agents:
            try:
                # PostgreSQL/SQLite 공용 호환 쿼리 처리
                await conn.execute(text(f"ALTER TABLE project ADD COLUMN {agent}_provider VARCHAR(50);"))
                await conn.execute(text(f"ALTER TABLE project ADD COLUMN {agent}_model VARCHAR(100);"))
                await conn.execute(text(f"ALTER TABLE project ADD COLUMN {agent}_api_key TEXT;"))
                print(f"Successfully added fields for: {agent}")
            except Exception as e:
                # 이미 컬럼이 존재하는 경우(중복 방지) 예외 스킵
                print(f"Field for {agent} might already exist. Details: {e}")
        print("Migration complete!")

if __name__ == "__main__":
    asyncio.run(run_migration())
```

---

## 2. API 요청/응답 스펙 정의

### 2.1 `app/schemas/project.py`
요청 데이터 수신 및 응답 데이터 마스킹 가드를 정밀화합니다.

```python
# app/schemas/project.py

class ProjectCreate(ProjectBase):
    api_key_override: Optional[str] = None
    plotter_provider: Optional[str] = None
    plotter_model: Optional[str] = None
    plotter_api_key: Optional[str] = None
    writer_provider: Optional[str] = None
    writer_model: Optional[str] = None
    writer_api_key: Optional[str] = None
    judge_provider: Optional[str] = None
    judge_model: Optional[str] = None
    judge_api_key: Optional[str] = None
    editor_provider: Optional[str] = None
    editor_model: Optional[str] = None
    editor_api_key: Optional[str] = None
    reviewer_provider: Optional[str] = None
    reviewer_model: Optional[str] = None
    reviewer_api_key: Optional[str] = None

class ProjectUpdate(BaseModel):
    # ... 기존 대표 필드 ...
    # 에이전트별 프로바이더, 모델명, API 키 필드 추가 (모두 Optional[str])

class ProjectResponse(BaseModel):
    id: int
    title: str
    synopsis: Optional[str] = None
    llm_provider: str
    llm_model: str
    has_api_key: bool = False
    
    # 에이전트별 설정 여부 노출 (has_api_key 패턴)
    plotter_provider: Optional[str] = None
    plotter_model: Optional[str] = None
    has_plotter_api_key: bool = False
    
    writer_provider: Optional[str] = None
    writer_model: Optional[str] = None
    has_writer_api_key: bool = False
    
    judge_provider: Optional[str] = None
    judge_model: Optional[str] = None
    has_judge_api_key: bool = False
    
    editor_provider: Optional[str] = None
    editor_model: Optional[str] = None
    has_editor_api_key: bool = False
    
    reviewer_provider: Optional[str] = None
    reviewer_model: Optional[str] = None
    has_reviewer_api_key: bool = False
    
    created_at: datetime

    @classmethod
    def from_orm_model(cls, project):
        return cls(
            id=project.id,
            title=project.title,
            synopsis=project.synopsis,
            llm_provider=project.llm_provider,
            llm_model=project.llm_model,
            has_api_key=bool(project.api_key_override),
            
            plotter_provider=project.plotter_provider,
            plotter_model=project.plotter_model,
            has_plotter_api_key=bool(project.plotter_api_key),
            
            writer_provider=project.writer_provider,
            writer_model=project.writer_model,
            has_writer_api_key=bool(project.writer_api_key),
            
            judge_provider=project.judge_provider,
            judge_model=project.judge_model,
            has_judge_api_key=bool(project.judge_api_key),
            
            editor_provider=project.editor_provider,
            editor_model=project.editor_model,
            has_editor_api_key=bool(project.editor_api_key),
            
            reviewer_provider=project.reviewer_provider,
            reviewer_model=project.reviewer_model,
            has_reviewer_api_key=bool(project.reviewer_api_key),
            
            created_at=project.created_at
        )
```

### 2.2 `app/routers/project.py` (API 키 일괄 암호화 자동화)
새로 추가되는 개별 API 키 또한 기존 `Fernet` 대칭 암호화 유틸리티를 사용해 암호문 형태로 DB에 입력합니다.

```python
# app/routers/project.py

# 저장 시 일괄 암호화 적용 대상 필드 목록
API_KEY_FIELDS = {
    "api_key_override",
    "plotter_api_key",
    "writer_api_key",
    "judge_api_key",
    "editor_api_key",
    "reviewer_api_key"
}

# 1) create_project 라우터:
    db_project = Project(
        user_id=current_user.id,
        title=project_in.title,
        synopsis=project_in.synopsis,
        llm_provider=project_in.llm_provider,
        llm_model=project_in.llm_model,
        api_key_override=encrypt_api_key(project_in.api_key_override),
        # 에이전트별 키 필드 암호화 매핑
        plotter_provider=project_in.plotter_provider,
        plotter_model=project_in.plotter_model,
        plotter_api_key=encrypt_api_key(project_in.plotter_api_key),
        writer_provider=project_in.writer_provider,
        writer_model=project_in.writer_model,
        writer_api_key=encrypt_api_key(project_in.writer_api_key),
        judge_provider=project_in.judge_provider,
        judge_model=project_in.judge_model,
        judge_api_key=encrypt_api_key(project_in.judge_api_key),
        editor_provider=project_in.editor_provider,
        editor_model=project_in.editor_model,
        editor_api_key=encrypt_api_key(project_in.editor_api_key),
        reviewer_provider=project_in.reviewer_provider,
        reviewer_model=project_in.reviewer_model,
        reviewer_api_key=encrypt_api_key(project_in.reviewer_api_key),
    )

# 2) update_project 라우터:
    update_data = project_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if key in API_KEY_FIELDS and value is not None:
            value = encrypt_api_key(value)
        setattr(project, key, value)
```

---

## 3. 에이전트 팩토리 및 에이전트 비즈니스 로직 연동

### 3.1 `app/services/llm_factory.py` (지능형 라우팅 구현)
개별 에이전트 셋업 시 `agent_type`을 검사하여 모델 구동 사양을 결정합니다.

```python
# app/services/llm_factory.py
from app.core.crypto import decrypt_api_key

class LLMFactory:
    @staticmethod
    def get_model(project: Project, agent_type: Optional[str] = None) -> BaseChatModel:
        # Default Fallback 값 지정
        provider = project.llm_provider
        model_name = project.llm_model
        encrypted_key = project.api_key_override

        # 오버라이드 필드가 활성화된 경우 라우팅 정보 대체
        if agent_type:
            spec_provider = getattr(project, f"{agent_type}_provider", None)
            spec_model = getattr(project, f"{agent_type}_model", None)
            spec_api_key = getattr(project, f"{agent_type}_api_key", None)

            if spec_provider and spec_model:
                provider = spec_provider
                model_name = spec_model
                encrypted_key = spec_api_key

        # API 복호화 수행
        decrypted_key = decrypt_api_key(encrypted_key) if encrypted_key else None
        
        # 각 프로바이더 클래스 매핑 리턴 (기존 로직 활용)
        if provider == "openai":
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(model=model_name, api_key=decrypted_key)
        # ... 타 프로바이더 생략 ...
```

### 3.2 `ReviewerAgent` 정의 (`app/services/agents.py`)
에피소드의 전체적인 완성도와 구성도를 평가하는 신규 에이전트 클래스입니다.

```python
# app/services/agents.py

class ReviewReport(BaseModel):
    score: int = Field(description="종합 평점 (1-100점)")
    readability: int = Field(description="가독성 분석 점수 (1-10)")
    tension: int = Field(description="긴장감 및 완급 전개 속도 점수 (1-10)")
    strengths: List[str] = Field(description="본 작품에서 가장 몰입도 높고 잘 작성된 강점 요소 리스트")
    weaknesses: List[str] = Field(description="설정 일치 여부 및 어조 불일치 등 개선이 필요한 약점 요소 리스트")
    suggestions: List[str] = Field(description="작가가 피드백 입력 시 바로 참고할 수 있는 수정 및 조율 가이드라인")
    summary: str = Field(description="전체 드래프트에 대한 종합 리뷰 의견")

class ReviewerAgent:
    SYSTEM_PROMPT = """당신은 완성된 웹소설 1개 회차의 드래프트를 분석하여 문학적 완성도, 독자 몰입도, 문체 완성도를 정량적으로 평가하고 
구체적 보완 지시서를 생성하는 전문 소설 기획 편집자(Reviewer)입니다.

제시된 [전체 소설 시놉시스]와 [세계관/캐릭터 정보]를 바탕으로, 완성된 [에피소드 드래프트 전체 본문]을 꼼꼼하게 검수하십시오.

[전체 소설 시놉시스]
{project_synopsis}

[세계관 및 캐릭터 설정]
{lore_context}

[에피소드 드래프트 전체 본문]
{draft}

검수 분석 기준:
1. 문장 가독성 및 가독 흐름이 자연스러운가?
2. 회차 전체의 긴장도(Tension) 완급조절이 성공적으로 달성되었는가?
3. 캐릭터 고유의 말투와 세계관 속성들이 흐름 내에서 개연성 있게 묘사되었는가?
4. 독자 입장에서 흥미 유발 및 클리프행어 연출이 양호한가?

중요: 인사말이나 메타 설명 없이 오직 규정된 JSON 포맷(ReviewReport 구조)에 맞춰 출력하십시오."""

    def __init__(self, model: BaseChatModel):
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.SYSTEM_PROMPT),
            ("user", "드래프트 분석을 정밀 실행한 뒤 결과를 ReviewReport 스키마에 맞추어 반환해 주세요.")
        ])
        structured_model = model.with_structured_output(ReviewReport)
        self.chain = prompt | structured_model

    async def run(self, project_synopsis: str, lore_context: str, draft: str) -> ReviewReport:
        return await self.chain.ainvoke({
            "project_synopsis": project_synopsis,
            "lore_context": lore_context,
            "draft": draft
        })
```

---

## 4. LangGraph 워크플로우 그래프 구조 설계 (`app/services/workflow.py`)

### 4.1 상태(AgentState) 확장 및 에이전트 초기화
```python
# app/services/workflow.py

class AgentState(TypedDict):
    # ... 기존 상태 정의 ...
    evaluation_report: Optional[dict] # 에피소드 종합 평가 보고서 저장
```

워크플로우 컴파일 함수(`get_compiled_workflow`) 내부에서 개별 에이전트를 적합한 LLM 인스턴스로 바인딩합니다.

```python
async def get_compiled_workflow(conn_pool=None):
    # ... project 객체 로딩 후 ...
    plotter_agent = PlotterAgent(LLMFactory.get_model(project, "plotter"))
    writer_agent = WriterAgent(LLMFactory.get_model(project, "writer"))
    judge_agent = JudgeAgent(LLMFactory.get_model(project, "judge"))
    editor_agent = EditorAgent(LLMFactory.get_model(project, "editor"))
    reviewer_agent = ReviewerAgent(LLMFactory.get_model(project, "reviewer"))
```

### 4.2 `reviewer_node` 구현 및 배치
모든 씬의 빌드 및 내부 교열 루프가 최종적으로 완료되었을 때 종합 평가를 수행합니다.

```python
async def reviewer_node(state: AgentState, config: RunnableConfig) -> dict:
    """
    모든 씬 집필이 완료된 후, draft 전체 본문을 기반으로 ReviewerAgent를 구동하여 평가 점수 및 보고서를 생성합니다.
    """
    # ... project 및 lore 정보 추출 ...
    
    # 팩토리에서 reviewer 전용 모델 로드
    reviewer = ReviewerAgent(LLMFactory.get_model(project, "reviewer"))
    
    try:
        report = await reviewer.run(
            project_synopsis=project.synopsis or "",
            lore_context=state.get("lore_context", ""),
            draft=state.get("draft", "")
        )
        # Pydantic 모델을 dict 형태로 치환하여 상태 저장
        report_dict = report.model_dump()
    except Exception as e:
        logger.error(f"ReviewerAgent run failed: {e}")
        # 오류 시 Soft-fail 처리하여 집필 중단 없이 다음 스탭 이동 보장
        report_dict = {
            "score": 0, "readability": 0, "tension": 0,
            "strengths": ["리뷰 에이전트 오류 발생"], "weaknesses": [], "suggestions": [],
            "summary": "평가 시스템 장애로 보고서를 생성하지 못했습니다."
        }
        
    return {"evaluation_report": report_dict, "status": "waiting_user"}
```

---

## 5. UI 시각화 컴포넌트 세부 명세

### 5.1 `ui/project_view.py` (설정 폼)
기본 설정 창에 아코디언 컴포넌트를 확장하여 에이전트별 설정을 덮어쓸 수 있도록 지원합니다.

```python
# ui/project_view.py 예시

with st.expander("🤖 에이전트별 세부 모델 설정 (고급)"):
    st.caption("필드를 입력하지 않거나 비워둘 시 프로젝트 대표 LLM 사양을 사용합니다.")
    agents = ["plotter", "writer", "judge", "editor", "reviewer"]
    
    for agent in agents:
        st.markdown(f"**{agent.upper()} Agent**")
        col1, col2, col3 = st.columns(3)
        with col1:
            provider = st.selectbox("제공자", ["", "openai", "google", "anthropic", "ollama"], key=f"{agent}_prov")
        with col2:
            model = st.text_input("모델명", key=f"{agent}_model_name")
        with col3:
            key = st.text_input("API Key Override", type="password", key=f"{agent}_api_key_str")
```

### 5.2 `ui/monitor_view.py` (평가 보고서 화면)
최종 사용자 대기 시 우측 절반 공간에 시각적인 에디터 평가 리포트 대시보드를 출력합니다.

```python
# ui/monitor_view.py

    elif status == "waiting_user":
        st.success("🤖 에이전트가 초안 작성을 완료했습니다. 검토 후 피드백을 주거나 승인하세요.")
        
        # 화면을 좌/우 2열로 분할 (좌측: 본문 및 피드백, 우측: 검수 보고서)
        left_col, right_col = st.columns([6, 4])
        
        with left_col:
            with st.container(border=True):
                st.markdown("### 현재 초안 본문")
                st.markdown(st.session_state.draft_text)
            
            st.markdown("---")
            st.subheader("인간 피드백 (Human-in-the-loop)")
            feedback = st.text_area("수정 지시사항 (피드백)")
            # ... 승인/수정 버튼 컴포넌트 ...
            
        with right_col:
            st.markdown("### 📊 🤖 AI 종합 검수 보고서")
            report = st.session_state.get("evaluation_report", {})
            if report:
                # 점수판 시각화
                m1, m2, m3 = st.columns(3)
                m1.metric("종합 점수", f"{report.get('score', 0)} / 100")
                m2.metric("가독성", f"{report.get('readability', 0)} / 10")
                m3.metric("완급 조절", f"{report.get('tension', 0)} / 10")
                
                # 상세 분석 내역 탭 배포
                t1, t2, t3 = st.tabs(["🌟 강점 분석", "⚠️ 보완 분석", "💡 개선 제안"])
                with t1:
                    for s in report.get("strengths", []):
                        st.markdown(f"- {s}")
                with t2:
                    for w in report.get("weaknesses", []):
                        st.markdown(f"- {w}")
                with t3:
                    for sug in report.get("suggestions", []):
                        st.markdown(f"- {sug}")
                
                # 종합 심평
                st.info(f"**총평**:\n\n{report.get('summary', '')}")
            else:
                st.info("평가 데이터가 없습니다.")
```

---

## 7. QA/설계 보완 피드백 반영 사항 (Checklist)

### 7.1 모델 버전 관리 및 UI 프리셋 (la-v1 vs la-v2 대응)
- **문제**: 사용자가 자유 텍스트 모델명(예: `gpt-4o`)을 직접 기입하는 구조로 인해, AI 제공사의 모델 감퇴/이름 변경/API 업데이트 시 대규모 수동 조치나 오타 발생 우려가 있습니다.
- **보완책**: UI(`ui/project_view.py`) 단에서 텍스트 입력을 직접 허용하되, 에이전트 목적별로 **추천 모델 프리셋**(예: `OpenAI - gpt-4o-mini (속도/가성비 기획/집필 최적)`, `OpenAI - gpt-4o (고지능 추론/검수 최적)`, `Anthropic - claude-3-5-sonnet-latest`)을 Selectbox 형태로 상단에 우선적으로 배치하고 선택할 수 있도록 설계하여 사용자 실수를 방지합니다.

### 7.2 ReviewerAgent의 환각(Hallucination) 방지 지침
- **문제**: 종합 평가 에이전트가 본문에 없는 내용을 근거로 아쉬운 점을 지적하거나 강점을 지칭하는 환각 현상 발생 가능성이 있습니다.
- **보완책**: `ReviewerAgent`의 `SYSTEM_PROMPT`에 **"반드시 소설 본문에 실제로 등장하는 키워드, 대사, 구체적인 문장(장면)을 인용(Citation)하여 구체적인 근거를 weaknesses 및 suggestions 항목마다 1개 이상 제시할 것. 없는 내용을 창작해 지적하지 말 것."**이라는 제약조건을 강력히 수록하고, Pydantic 스키마 설명에도 근거 제시를 의무화합니다.

### 7.3 asyncio.Lock 대기 시간 대비 실시간 통지 브로드캐스트
- **문제**: `ReviewerAgent`가 소설 전체를 분석하고 구조화 출력을 생성할 때 LLM 처리에 상당한 시간(20~30초 이상)이 소요됩니다. 이 과정에서 `asyncio.Lock`이 점유되며 다른 클라이언트 요청이 병목에 가로막힐 수 있습니다.
- **보완책**: 
  - `reviewer_node`에 도달하여 평가를 개시하기 직전, `on_status` 콜백을 호출하여 **`{"event": "status_changed", "status": "reviewing", "message": "🤖 집필 완료! AI 에디터가 본문 종합 검수 보고서를 작성하는 중입니다. 잠시만 기다려 주세요 (예상 소요 시간 20초)..."}`** 메시지를 실시간 브로드캐스트 전송하도록 구조를 보완합니다.
  - 이를 통해 사용자는 화면이 멈춘 것처럼 느끼는 현상을 예방하고 안정된 피드백을 받을 수 있습니다.
