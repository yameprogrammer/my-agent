import logging
from typing import List, Optional
from langchain_openai import OpenAIEmbeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_ollama import OllamaEmbeddings
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import Project, WorldSetting, Character
from app.core.config import settings

logger = logging.getLogger(__name__)

def get_embeddings_model(project: Project):
    """
    프로젝트 LLM 설정에 최적화된 LangChain Embeddings 모델 객체를 생성합니다.
    """
    provider = project.llm_provider.lower()
    api_key = project.api_key_override
    
    if provider == "openai":
        key = api_key or settings.OPENAI_API_KEY
        if key:
            return OpenAIEmbeddings(
                model="text-embedding-3-small",
                openai_api_key=key
            )
    elif provider == "google":
        key = api_key or settings.GOOGLE_API_KEY
        if key:
            return GoogleGenerativeAIEmbeddings(
                model="models/text-embedding-004",
                google_api_key=key
            )
    elif provider == "ollama":
        return OllamaEmbeddings(
            model=project.llm_model
        )
    return None


async def generate_embedding(text: str, project: Project) -> Optional[List[float]]:
    """
    지정된 텍스트의 임베딩 벡터를 비동기 생성합니다.
    """
    try:
        model = get_embeddings_model(project)
        if model is None:
            return None
        return await model.aembed_query(text)
    except Exception as e:
        logger.warning(f"Failed to generate embedding for RAG: {e}")
        return None


async def retrieve_relevant_lores(
    session: AsyncSession,
    project_id: int,
    scene_title: str,
    scene_plot: str,
    limit: int = 5
) -> str:
    """
    하이브리드 매칭을 적용하여 관련 인물 설정 및 세계관 설정집(Lorebook) 데이터를 조회합니다.
    1. 인물 설정: 등장인물 목록 중 명칭이 씬 본문/기획안에 포함된 경우 무조건 로딩 (상위 중요도 우선)
    2. 세계관 설정: 키워드 매칭(Exact Match) + pgvector 코사인 유사도(Semantic Match) 하이브리드 검색
    """
    project = await session.get(Project, project_id)
    if not project:
        return "프로젝트 정보를 찾을 수 없습니다."

    # === 1. 인물 설정 (키워드 매칭) ===
    char_stmt = select(Character).where(Character.project_id == project_id)
    chars = (await session.execute(char_stmt)).scalars().all()
    
    matched_chars = []
    for c in chars:
        if c.name in scene_title or c.name in scene_plot:
            matched_chars.append(c)
            
    importance_rank = {"protagonist": 1, "deuteragonist": 2, "major": 3, "minor": 4}
    matched_chars.sort(key=lambda x: importance_rank.get(x.importance, 99))

    # === 2. 세계관 설정 (키워드 + pgvector 유사도 하이브리드) ===
    lore_stmt = select(WorldSetting).where(WorldSetting.project_id == project_id)
    all_lores = (await session.execute(lore_stmt)).scalars().all()
    
    # 2-A. 키워드 매칭
    exact_lores = [
        ws for ws in all_lores 
        if ws.keyword in scene_title or ws.keyword in scene_plot
    ]
    
    # 2-B. pgvector 의미 매칭 (Cosine Similarity)
    semantic_lores = []
    query_text = f"{scene_title}\n{scene_plot}"
    query_vector = await generate_embedding(query_text, project)
    
    if query_vector is not None:
        try:
            # pgvector의 cosine_distance 연산자를 활용한 유사도 쿼리
            semantic_stmt = (
                select(WorldSetting)
                .where(WorldSetting.project_id == project_id)
                .where(WorldSetting.embedding != None)
                .order_by(WorldSetting.embedding.cosine_distance(query_vector))
                .limit(limit)
            )
            semantic_res = await session.execute(semantic_stmt)
            semantic_lores = semantic_res.scalars().all()
        except Exception as e:
            logger.error(f"pgvector semantic search failed: {e}")
            
    # 두 매칭 결과를 병합 및 중복 제거
    merged_lores = {ws.id: ws for ws in exact_lores}
    for ws in semantic_lores:
        if ws.id not in merged_lores:
            merged_lores[ws.id] = ws
            
    matched_lores = list(merged_lores.values())

    # === 3. 맥락 텍스트 포맷 조합 ===
    lore_context = "=== [등장인물 설정] ===\n"
    if matched_chars:
        lore_context += "\n".join([
            f"- {c.name} ({c.importance}): {c.description}"
            for c in matched_chars
        ]) + "\n"
    else:
        lore_context += "(매칭된 등장인물 없음)\n"
        
    lore_context += "\n=== [세계관 및 설정집] ===\n"
    if matched_lores:
        lore_context += "\n".join([
            f"- {ws.keyword} ({ws.category}): {ws.description}"
            for ws in matched_lores
        ]) + "\n"
    else:
        lore_context += "(매칭된 세계관 설정 없음)\n"
        
    return lore_context
