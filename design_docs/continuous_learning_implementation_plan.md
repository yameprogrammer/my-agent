# AI 소설 집필 머신: 지속 학습 엔진 정밀 구현 계획서 (Continuous Learning Implementation Plan)

본 문서는 `continuous_learning_engine.md` 설계안을 바탕으로, 실제 프로덕션 코드베이스인 [app/models.py](file:///C:/Users/parkp/Workspace/personal/my-agent/app/models.py), [app/core/database.py](file:///C:/Users/parkp/Workspace/personal/my-agent/app/core/database.py), [app/services/workflow.py](file:///C:/Users/parkp/Workspace/personal/my-agent/app/services/workflow.py), [app/services/rag.py](file:///C:/Users/parkp/Workspace/personal/my-agent/app/services/rag.py)에 바로 반영할 수 있도록 설계된 정밀 구현 계획서입니다.

---

## 1. 구현 목표 (Objective)

사용자가 AI 생성 소설 초안에 대해 입력한 **피드백 이력**과 **수동 보정 결과(최종 원고)**를 비교 대조하여 AI가 스스로 **스타일 가이드를 진화**시키고, 씬별 아웃라인에 적합한 **과거의 교훈(Know-How)을 RAG로 동적 매칭**하여 다음 회차 집필 시 반영할 수 있도록 완벽하게 자동화된 학습 루프를 구축합니다.

---

## 2. Phase 1: DB 스키마 추가 및 Soft Migration

### 2.1 모델 정의 ([app/models.py](file:///C:/Users/parkp/Workspace/personal/my-agent/app/models.py) 확장)
`WritingKnowHow` 테이블을 SQLModel 기반으로 정의하고, `Project` 테이블과의 역참조 관계를 명시합니다.

```python
# app/models.py 하단에 추가

class WritingKnowHow(SQLModel, table=True):
    """지속 학습 엔진을 통해 추출된 세부 집필 노하우 및 피드백 극복 사례."""
    __tablename__ = "writing_know_how"

    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id", nullable=False, index=True)
    episode_id: Optional[int] = Field(
        sa_column=Column(Integer, ForeignKey("episode.id", ondelete="SET NULL"), nullable=True)
    )
    
    category: str = Field(default="general", nullable=False) # general | style | dialogue | action | logic | lore
    context_trigger: str = Field(nullable=False) # RAG 쿼리 및 매칭을 위한 상황 키워드 (e.g. "검술 전투 묘사")
    problem_identified: str = Field(nullable=False) # 기존에 발생했던 문제점
    lesson_learned: str = Field(nullable=False) # 해결책 및 향후 준수 지침
    
    # 1536차원 임베딩 컬럼 (pgvector)
    embedding: Optional[List[float]] = Field(
        default=None,
        sa_column=Column(Vector(1536), nullable=True)
    )
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    project: "Project" = Relationship(back_populates="writing_know_hows")

# Project 클래스 내에 관계 추가 (기존 Project 클래스 내부 정의 추가)
# writing_know_hows: List["WritingKnowHow"] = Relationship(
#     back_populates="project", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
# )
```

### 2.2 Soft Migration 스크립트 작성 ([app/core/database.py](file:///C:/Users/parkp/Workspace/personal/my-agent/app/core/database.py) 연동)
기존 DB 테이블이 있어도 안전하게 테이블을 생성하고 외래 키 제약 조건 및 인덱스를 생성하도록 `init_db()`에 추가합니다.

```python
# app/core/database.py 내 init_db() 하단에 추가할 코드

        # pgvector 및 SQLModel 마이그레이션 하단에 추가
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS writing_know_how (
                id SERIAL PRIMARY KEY,
                project_id INTEGER NOT NULL REFERENCES project(id) ON DELETE CASCADE,
                episode_id INTEGER REFERENCES episode(id) ON DELETE SET NULL,
                category VARCHAR(50) NOT NULL DEFAULT 'general',
                context_trigger VARCHAR(500) NOT NULL,
                problem_identified TEXT NOT NULL,
                lesson_learned TEXT NOT NULL,
                embedding vector(1536),
                created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT TIMEZONE('utc', NOW())
            );
        """))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_writing_know_how_project ON writing_know_how(project_id)"
        ))
```

---

## 3. Phase 2: AgentState 확장 및 이력 추적

교정 완료된 최종본과 최초 원고를 대조하기 위해, LangGraph 전체 수명 주기 동안 `최초 초안`과 `사용자 피드백 이력`을 추적해야 합니다.

### 3.1 State 스키마 변경 ([app/services/workflow.py](file:///C:/Users/parkp/Workspace/personal/my-agent/app/services/workflow.py))
`AgentState`에 캡처용 필드를 추가합니다.

```python
# app/services/workflow.py 내 AgentState 수정

class AgentState(TypedDict):
    project_id: int
    episode_id: int
    current_scene_index: int
    scenes: List[dict]
    lore_context: str
    draft: str                   # 현재 누적 초안 (교정 시 업데이트됨)
    initial_draft: Optional[str] # [추가] 피드백 적용 전 최초 완성 드래프트 백업
    feedback_history: List[str]  # [추가] 사용자 피드백 누적 리스트 (최대 5회 분량)
    current_scene_draft: str
    critique: str
    user_feedback: Optional[str]
    loop_count: int
    status: str
    evaluation_report: Optional[dict]
    write_mode: str
    seed_draft: str
```

### 3.2 Workflow 내 추적 로직 추가 ([app/services/workflow.py](file:///C:/Users/parkp/Workspace/personal/my-agent/app/services/workflow.py))

1. **최초 드래프트 백업**: 모든 씬의 초안 작성이 끝나고 처음으로 사용자의 피드백을 받기 위해 `waiting_user` 상태로 진입하는 단계에서 `initial_draft`를 백업합니다.
   * `_finalize_judge_result` 또는 `editor_node`가 실행되는 초입에 복사합니다.

```python
# app/services/workflow.py 내 editor_node() 수정

async def editor_node(state: AgentState, config: RunnableConfig) -> dict:
    if _check_cancelled(config):
        return {"status": "cancelled"}
        
    # [추가] 최초 1회 진입 시 현재의 draft 상태를 initial_draft 로 백업
    initial_draft = state.get("initial_draft")
    if not initial_draft and state.get("draft"):
        initial_draft = state["draft"]

    # [추가] 사용자 피드백이 들어왔다면 피드백 히스토리에 누적
    feedback_history = state.get("feedback_history") or []
    current_feedback = state.get("user_feedback")
    if current_feedback and current_feedback not in feedback_history:
        feedback_history.append(current_feedback)
```

그리고 `editor_node`가 리턴하는 딕셔너리에 `initial_draft`와 `feedback_history`를 함께 반환하여 상태를 유지시킵니다.

```python
    # editor_node() 리턴 부분 수정 (is_full_episode_edit 분기 시)
    if is_full_episode_edit:
        return {
            "draft": edited_draft,
            "initial_draft": initial_draft,
            "feedback_history": feedback_history,
            "current_scene_draft": "",
            "loop_count": state["loop_count"] + 1,
            "critique": "",
            "user_feedback": None,
            "status": "waiting_user",
        }
```

---

## 4. Phase 3: Retrospective Agent (사후 회고 에이전트) 구현

### 4.1 에이전트 클래스 생성 (`app/services/agents/retrospective.py`)
[app/services/agents/retrospective.py](file:///C:/Users/parkp/Workspace/personal/my-agent/app/services/agents/retrospective.py) 파일을 생성하여 LLM 구조화된 출력(Structured Output)을 활용한 분석 엔진을 정의합니다.

```python
from typing import List, Optional
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.language_models import BaseChatModel

class SituationalKnowHowSchema(BaseModel):
    category: str = Field(description="장면의 종류: action | dialogue | lore | description | pacing")
    context_trigger: str = Field(description="노하우가 트리거될 장면 아웃라인 유사도 매칭용 상황 설명 (예: 검술 기반 일대일 대결)")
    problem_identified: str = Field(description="최초 생성 시 드러난 AI의 부족함 및 설정 충돌 요인")
    lesson_learned: str = Field(description="동일 상황에서 AI가 지켜야 할 극도로 구체적인 글쓰기 지침")

class RetrospectiveReport(BaseModel):
    global_style_updates: List[str] = Field(description="공통적으로 강화하거나 필터링해야 할 어휘/문체 규칙 목록")
    situational_know_how: List[SituationalKnowHowSchema] = Field(description="장면 상황별 피드백 극복 지침 목록")

class RetrospectiveAgent:
    SYSTEM_PROMPT = """당신은 웹소설 흥행 공식과 집필 스타일을 분석하는 대한민국 최고 수준의 에디터입니다.
이번 에피소드의 최초 드래프트와 사용자의 피드백 사항, 그리고 사용자가 수정한 최종 승인본을 분석하여 
AI가 향후 소설 생성 시 반드시 반영해야 할 '실천적 집필 규칙'을 추출해 주십시오.

[작품 정보]
- 작품 시놉시스: {synopsis}
- 현재 전체 스타일 가이드: {current_style_guide}

[해당 회차 집필 이력]
- 회차 아웃라인: {outline}
- 최초 AI 드래프트: {initial_draft}
- 수집된 사용자 피드백 및 에이전트 교정 피드백: {feedbacks}
- 최종 승인된 완성본: {approved_text}

[규칙 추출 필수 지침]
1. 최초 드래프트와 최종 완성본을 비교하여 단어 선택, 대사 톤, 긴장감 묘사 등에서 바뀐 디테일을 포착하십시오.
2. 분석 결과를 두 가지 영역으로 나누어 구조화하십시오:
   - **global_style_updates**: 작품의 모든 장면에 걸쳐 적용될 문체 변화 (예: "주인공의 독백 시 '~했다' 대신 '~다' 종결어미 사용 비율을 늘림")
   - **situational_know_how**: 특정 장면 아웃라인이나 소재가 매칭될 때만 활용되는 묘사 규칙 (예: "싸늘한 눈빛의 대화 시 긴 수식어를 배제하고 한 줄 내외의 짧은 대사로 대치")
3. '더 생생하게 쓰기' 같은 모호한 문장은 피하고 반드시 행동적이고 실용적인 형태로 지침을 서술하십시오."""

    def __init__(self, model: BaseChatModel):
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.SYSTEM_PROMPT),
            ("user", "집필 이력을 바탕으로 개선 지침 보고서를 추출하십시오.")
        ])
        # Pydantic 스키마를 통한 구조화 출력 강제
        self.chain = prompt | model.with_structured_output(RetrospectiveReport)

    async def run(
        self,
        synopsis: str,
        current_style_guide: str,
        outline: str,
        initial_draft: str,
        feedbacks: str,
        approved_text: str
    ) -> RetrospectiveReport:
        return await self.chain.ainvoke({
            "synopsis": synopsis,
            "current_style_guide": current_style_guide or "N/A",
            "outline": outline,
            "initial_draft": initial_draft,
            "feedbacks": feedbacks,
            "approved_text": approved_text
        })
```

`app/services/agents/__init__.py` 에 `RetrospectiveAgent`를 노출시킵니다.

```python
# app/services/agents/__init__.py 에 추가
from app.services.agents.retrospective import RetrospectiveAgent  # noqa: F401
```

---

## 5. Phase 4: Workflow Handoff & Background Learning Task

회차 본문이 성공적으로 확정(`is_approved=True`)된 직후, 사용자의 대기 시간을 주지 않고 백그라운드 태스크로 분석 및 RAG 저장을 진행합니다.

### 5.1 백그라운드 분석 태스크 함수 작성 ([app/services/workflow.py](file:///C:/Users/parkp/Workspace/personal/my-agent/app/services/workflow.py))
`app/services/workflow.py` 하단이나 적합한 유틸리티 위치에 회고 연동 및 DB 반영 로직을 작성합니다.

```python
# app/services/workflow.py 에 추가할 백그라운드 학습 함수

import logging
from app.services.agents.retrospective import RetrospectiveAgent
from app.services.rag import generate_embedding

logger = logging.getLogger(__name__)

async def run_retrospective_and_learn_task(
    project_id: int,
    episode_id: int,
    outline: str,
    initial_draft: str,
    approved_text: str,
    feedback_history: List[str]
):
    """
    승인 후 호출되어 스타일 가이드를 자율 갱신하고 상황별 노하우를 pgvector DB에 적재합니다.
    """
    async with AsyncSession(async_engine) as session:
        try:
            project = await session.get(Project, project_id)
            if not project:
                return
                
            # 피드백 문자열 병합
            feedbacks_str = "\n".join([f"- {f}" for f in (feedback_history or [])])
            if not feedbacks_str:
                feedbacks_str = "N/A (사용자 직접 수동 수정 및 승인)"

            # LLM 에이전트 초기화
            llm = LLMFactory.get_model_for_agent(project, "editor", temperature=0.2)
            retrospective_agent = RetrospectiveAgent(llm)

            logger.info(f"[Continuous Learning] 분석 시작 - 프로젝트: {project_id}, 회차: {episode_id}")
            
            report = await retrospective_agent.run(
                synopsis=project.synopsis or "N/A",
                current_style_guide=project.style_guide or "",
                outline=outline or "N/A",
                initial_draft=initial_draft or approved_text, # 백업이 없는 경우 최종본 대조
                feedbacks=feedbacks_str,
                approved_text=approved_text
            )

            # 1. 글로벌 스타일 가이드 자율 갱신 및 병합
            if report.global_style_updates:
                existing_rules = set(line.strip() for line in (project.style_guide or "").split("\n") if line.strip())
                for rule in report.global_style_updates:
                    # 간단한 중복 제거 후 추가
                    if rule.strip() and rule.strip() not in existing_rules:
                        existing_rules.add(rule.strip())
                project.style_guide = "\n".join(sorted(list(existing_rules)))
                session.add(project)

            # 2. 상황별 노하우 RAG DB 임베딩 생성 및 저장
            for know_how in report.situational_know_how:
                # context_trigger 기반 임베딩 추출
                embedding_vector = await generate_embedding(know_how.context_trigger, project)
                
                db_know_how = WritingKnowHow(
                    project_id=project_id,
                    episode_id=episode_id,
                    category=know_how.category,
                    context_trigger=know_how.context_trigger,
                    problem_identified=know_how.problem_identified,
                    lesson_learned=know_how.lesson_learned,
                    embedding=embedding_vector
                )
                session.add(db_know_how)

            await session.commit()
            logger.info(f"[Continuous Learning] 성공적으로 학습 데이터를 반영했습니다. (스타일 가이드 갱신 및 상황 노하우 {len(report.situational_know_how)}건 적재)")

        except Exception as e:
            logger.error(f"[Continuous Learning] 학습 실패: {e}", exc_info=True)
```

### 5.2 save_node() 내 트리거 추가 ([app/services/workflow.py](file:///C:/Users/parkp/Workspace/personal/my-agent/app/services/workflow.py))
최종 승인본을 DB에 넣은 직후 백그라운드 태스크로 `run_retrospective_and_learn_task`를 던집니다.

```python
# app/services/workflow.py 내 save_node() 하단 수정

        # ... (기존 save_node 코드)
        db_content = Content(
            episode_id=state["episode_id"],
            parent_id=parent_id,
            content_text=state["draft"],
            author_type=author_type,
            version_tag=version_tag,
            is_approved=True
        )
        session.add(db_content)
        await session.commit()

        # [수정/추가] 백그라운드 태스크로 지속 학습 비동기 트리거 실행
        import asyncio
        # 아웃라인 정보를 문자열화
        outline_summary = "\n".join([f"- Scene {s.get('index')}: {s.get('title')} ({s.get('plot')})" for s in (state.get("scenes") or [])])
        
        asyncio.create_task(
            run_retrospective_and_learn_task(
                project_id=state["project_id"],
                episode_id=state["episode_id"],
                outline=outline_summary,
                initial_draft=state.get("initial_draft"),
                approved_text=state["draft"],
                feedback_history=state.get("feedback_history") or []
            )
        )
```

---

## 6. Phase 5: RAG 기반 동적 집필 지침 주입

다음 화 집필 시, 에피소드 아웃라인의 주요 씬에 맞춰 과거에 누적한 노하우를 시맨틱 검색하여 작가의 프롬프트에 동적으로 공급해야 합니다.

### 6.1 RAG 검색 함수 작성 ([app/services/rag.py](file:///C:/Users/parkp/Workspace/personal/my-agent/app/services/rag.py))
아웃라인을 쿼리로 삼아 `WritingKnowHow` 벡터 테이블에서 최적 매칭 레코드를 로드합니다.

```python
# app/services/rag.py 에 추가할 노하우 검색 함수

from app.models import WritingKnowHow

async def get_relevant_know_how_context(
    session: AsyncSession,
    project_id: int,
    scene_outline: str,
    limit: int = 3,
    rag_threshold: float = 0.5
) -> str:
    """
    현재 집필하려는 씬의 아웃라인과 시맨틱적으로 가장 매칭되는 과거 노하우 지침들을 로드합니다.
    """
    # 1. 아웃라인 임베딩 쿼리 생성
    project = await session.get(Project, project_id)
    if not project:
        return ""
        
    query_vector = await generate_embedding(scene_outline, project)
    if not query_vector:
        return ""

    # 2. 코사인 유사도 기준 pgvector 검색
    stmt = (
        select(WritingKnowHow)
        .where(WritingKnowHow.project_id == project_id)
        .where(WritingKnowHow.embedding != None)
        .where(WritingKnowHow.embedding.cosine_distance(query_vector) <= (1.0 - rag_threshold))
        .order_by(WritingKnowHow.embedding.cosine_distance(query_vector))
        .limit(limit)
    )
    results = (await session.execute(stmt)).scalars().all()
    if not results:
        return ""

    context_chunks = []
    context_chunks.append("※ 과거 집필 피드백을 통해 획득한 특수 지침:")
    for idx, r in enumerate(results):
        context_chunks.append(
            f"  [{r.context_trigger} 상황 대비 지침 {idx+1}]\n"
            f"  - 과거 지적된 원인: {r.problem_identified}\n"
            f"  - 이번 생성 시 적용할 극복 규칙: {r.lesson_learned}"
        )
    return "\n\n".join(context_chunks)
```

### 6.2 writer_node() 및 editor_node() 프롬프트 주입 연동 ([app/services/workflow.py](file:///C:/Users/parkp/Workspace/personal/my-agent/app/services/workflow.py))
`style_guide` 매개변수에 RAG로 결합한 노하우 텍스트를 인라인 방식으로 뒤에 덧붙여 주입합니다. 이를 통해 기존 에이전트 클래스들의 인자 형태를 변경하지 않고 안전하게 연동할 수 있습니다.

```python
# app/services/workflow.py 내 writer_node() 수정

        # ... (기존 writer_node 내부 데이터 조회 코드)
        style_guide = (getattr(project, "style_guide", None) or "").strip() or "(스타일 가이드 없음)"
        
        # [추가] RAG를 통한 맞춤형 실전 노하우 주입
        from app.services.rag import get_relevant_know_how_context
        # 현재 씬의 제목과 줄거리를 기반으로 검색 쿼리 작성
        current_scene = scenes[idx]
        scene_outline_query = f"{current_scene.get('title', '')} - {current_scene.get('plot', '')}"
        
        know_how_context = await get_relevant_know_how_context(
            session=session,
            project_id=state["project_id"],
            scene_outline=scene_outline_query,
            limit=2,
            rag_threshold=0.4 # 조금 더 유연한 검색 매칭 허용
        )
        
        if know_how_context:
            style_guide = f"{style_guide}\n\n{know_how_context}"
```

---

## 7. Phase 6: 검증 및 테스트 계획

### 7.1 단위 및 통합 테스트 시나리오 (`tests/test_continuous_learning.py`)
학습 엔진이 설계대로 피드백 데이터 수집 및 학습, RAG 쿼리 인젝션까지 순환하는지 검증하는 테스트 코드를 작성합니다.

```python
import pytest
from sqlmodel.ext.asyncio.session import AsyncSession
from app.models import Project, Episode, WritingKnowHow
from app.services.workflow import run_retrospective_and_learn_task
from app.services.rag import get_relevant_know_how_context

@pytest.mark.asyncio
async def test_continuous_learning_cycle(db_session: AsyncSession, sample_project: Project, sample_episode: Episode):
    """
    1. 회고 에이전트 분석 결과가 올바르게 DB와 스타일 가이드에 파싱되어 반영되는지 테스트.
    2. 생성된 임베딩 상황 트리거가 RAG를 통해 정상 쿼리 매칭되는지 검증.
    """
    # 임의의 학습 데이터 강제 주입
    project_id = sample_project.id
    episode_id = sample_episode.id
    
    # 1. 백그라운드 회고 태스크 작동 검증
    # 모의 초안 및 승인본과 피드백 리스트 작성
    outline = "- Scene 1: 대련장에서 기사와 혈투를 벌임"
    initial_draft = "주인공이 기사단장 아서와 칼을 부딪쳤다. 아서가 화를 내며 외쳤다. '이 빌어먹을 자식아!'"
    approved_text = "아서가 차갑게 웃으며 검을 겨누었다. 아서는 아무리 분노해도 절대 상스러운 욕설을 입에 담지 않는 고결한 성정의 기사였다. '대련을 계속하지요.'"
    feedback_history = ["기사단장은 욕을 하지 않는 고결한 캐릭터인데 대사가 성격과 안 맞아요. 존댓말로 수정해주세요."]

    # 백그라운드 태스크 실행 (테스트 환경에서는 동기 호출 방식 등으로 래핑)
    await run_retrospective_and_learn_task(
        project_id=project_id,
        episode_id=episode_id,
        outline=outline,
        initial_draft=initial_draft,
        approved_text=approved_text,
        feedback_history=feedback_history
    )

    # DB 조회 검증
    await db_session.refresh(sample_project)
    
    # 스타일 가이드에 기사단장 관련 언급 등이 업데이트 되었는지 확인
    assert sample_project.style_guide is not None
    
    # WritingKnowHow 에 인스턴스가 생성되었는지 검사
    from sqlmodel import select
    know_how_stmt = select(WritingKnowHow).where(WritingKnowHow.project_id == project_id)
    know_how_list = (await db_session.execute(know_how_stmt)).scalars().all()
    
    assert len(know_how_list) >= 1
    assert know_how_list[0].problem_identified is not None
    assert know_how_list[0].embedding is not None

    # 2. RAG 매칭 매커니즘 검증
    # 다음 화의 대련 상황 씬을 아웃라인으로 쿼리
    search_query = "아서 단장과의 진검 승부 및 대화 씬"
    retrieved_know_how = await get_relevant_know_how_context(
        session=db_session,
        project_id=project_id,
        scene_outline=search_query,
        limit=1,
        rag_threshold=0.4
    )
    
    assert "아서" in retrieved_know_how or "대련" in retrieved_know_how
```
