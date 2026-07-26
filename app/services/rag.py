import logging
from typing import List, Optional
from langchain_openai import OpenAIEmbeddings
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import Project, WorldSetting, Character, ReferenceMaterial, Episode
from app.core.config import settings
from app.core.crypto import decrypt_api_key

logger = logging.getLogger(__name__)

# WorldSetting.embedding 컬럼과 차원을 일치시키기 위한 고정 임베딩 모델 (WP-B 옵션 B1)
# 채팅 LLM 프로바이더(Google/Anthropic/Ollama)와 무관하게 1536-d 벡터를 사용한다.
EMBEDDING_MODEL_NAME = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536


def get_embeddings_model(project: Project):
    """
    Lore 임베딩 전용 모델 팩토리.

    Vector(1536) 스키마와 항상 호환되도록 OpenAI text-embedding-3-small 을 사용한다.
    API 키: OPENAI_API_KEY 우선, openai 프로젝트의 api_key_override 폴백.
    """
    key = settings.OPENAI_API_KEY
    if not key and project.llm_provider.lower() == "openai":
        key = decrypt_api_key(project.api_key_override)
    if not key:
        logger.debug(
            "No OpenAI API key for embeddings (project_id=%s provider=%s); "
            "semantic RAG will be skipped.",
            getattr(project, "id", None),
            project.llm_provider,
        )
        return None
    return OpenAIEmbeddings(
        model=EMBEDDING_MODEL_NAME,
        openai_api_key=key,
    )


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
    limit: int = 5,
    episode_id: Optional[int] = None
) -> str:
    """
    하이브리드 매칭을 적용하여 관련 인물 설정 및 세계관 설정집(Lorebook) 데이터를 조회합니다.
    1. 인물 설정: 등장인물 목록 중 명칭이 씬 본문/기획안에 포함된 경우 무조건 로딩 (상위 중요도 우선)
    2. 세계관 설정: 키워드 매칭(Exact Match) + pgvector 코사인 유사도(Semantic Match) 하이브리드 검색
    """
    project = await session.get(Project, project_id)
    if not project:
        return "프로젝트 정보를 찾을 수 없습니다."

    # RAG 파라미터 제어 변수 기본값
    rag_threshold = 0.5
    rag_limit = limit
    force_ref_ids = []

    # 에피소드 맞춤형 제어 로드 (RAG 임계치, 개수 제한, 강제 연결)
    if episode_id:
        episode = await session.get(Episode, episode_id)
        if episode:
            rag_threshold = episode.rag_threshold
            rag_limit = episode.rag_limit
            if episode.force_reference_ids:
                try:
                    force_ref_ids = [int(i.strip()) for i in episode.force_reference_ids.split(",") if i.strip().isdigit()]
                except Exception as e:
                    logger.warning(f"Failed to parse force_reference_ids: {e}")

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
            # 코사인 거리가 (1 - rag_threshold) 이하인 것만 필터링
            semantic_stmt = (
                select(WorldSetting)
                .where(WorldSetting.project_id == project_id)
                .where(WorldSetting.embedding != None)
                .where(WorldSetting.embedding.cosine_distance(query_vector) <= (1.0 - rag_threshold))
                .order_by(WorldSetting.embedding.cosine_distance(query_vector))
                .limit(rag_limit)
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
            
    matched_lores = list(merged_lores.values())[:rag_limit]

    # === 3. 참고 자료 (Reference Material) 조회 ===
    # 3-A. 강제 참고 자료 로드 (Force-Include)
    matched_refs = []
    seen_ref_ids = set()
    if force_ref_ids:
        try:
            force_stmt = select(ReferenceMaterial).where(ReferenceMaterial.id.in_(force_ref_ids))
            force_res = (await session.execute(force_stmt)).scalars().all()
            for fr in force_res:
                matched_refs.append(fr)
                seen_ref_ids.add(fr.id)
        except Exception as e:
            logger.error(f"Failed to query force_reference_ids: {e}")

    # 3-B. 제목 키워드 매칭
    ref_stmt = select(ReferenceMaterial).where(ReferenceMaterial.project_id == project_id)
    all_refs = (await session.execute(ref_stmt)).scalars().all()
    
    for r in all_refs:
        if r.id in seen_ref_ids:
            continue
        if r.title in scene_title or r.title in scene_plot:
            matched_refs.append(r)
            seen_ref_ids.add(r.id)

    # 3-C. IMP-11: 임베딩 시맨틱 검색 (WorldSetting 과 동일 차원)
    if query_vector is not None:
        try:
            semantic_ref_stmt = (
                select(ReferenceMaterial)
                .where(ReferenceMaterial.project_id == project_id)
                .where(ReferenceMaterial.embedding != None)  # noqa: E711
                .where(
                    ReferenceMaterial.embedding.cosine_distance(query_vector)
                    <= (1.0 - rag_threshold)
                )
                .order_by(ReferenceMaterial.embedding.cosine_distance(query_vector))
                .limit(rag_limit)
            )
            semantic_ref_res = await session.execute(semantic_ref_stmt)
            for sr in semantic_ref_res.scalars().all():
                if sr.id not in seen_ref_ids:
                    matched_refs.append(sr)
                    seen_ref_ids.add(sr.id)
        except Exception as e:
            logger.error(f"pgvector reference semantic search failed: {e}")
            
    # 매칭 결과가 부족할 시 최신 리서치 자료 상위 3개를 Fallback으로 추가
    if len(matched_refs) < 3:
        sorted_refs = sorted(all_refs, key=lambda x: x.created_at, reverse=True)
        for sr in sorted_refs:
            if sr.id in seen_ref_ids:
                continue
            matched_refs.append(sr)
            seen_ref_ids.add(sr.id)
            if len(matched_refs) >= 3:
                break

    # 설정된 최대 개수 적용
    matched_refs = matched_refs[:rag_limit]

    # === 4. 맥락 텍스트 포맷 조합 ===
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
        
    lore_context += "\n=== [고증 및 리서치 참고 자료] ===\n"
    if matched_refs:
        lore_context += "\n".join([
            f"- {r.title} ({r.category}): {r.content[:600]}..." if len(r.content) > 600 else f"- {r.title} ({r.category}): {r.content}"
            for r in matched_refs
        ]) + "\n"
    else:
        lore_context += "(매칭된 고증 참고 자료 없음)\n"
        
    return lore_context


# Plotter 전용 컨텍스트 상한 (IMP-08)
PLOTTER_MAX_CHARS = 8000
PLOTTER_MAJOR_IMPORTANCE = {"protagonist", "deuteragonist", "major"}
PLOTTER_LORE_LIMIT = 12
PLOTTER_CHAR_LIMIT = 15


async def build_plotter_lore_context(
    session: AsyncSession,
    project_id: int,
    *,
    episode_title: str = "",
    episode_outline: str = "",
    max_chars: int = PLOTTER_MAX_CHARS,
    lore_limit: int = PLOTTER_LORE_LIMIT,
    char_limit: int = PLOTTER_CHAR_LIMIT,
) -> str:
    """
    IMP-08: Plotter 에 전 캐릭터·전 세계관 전문 dump 대신
    - 중요 인물 전원 + 개요에 이름이 등장하는 minor
    - 키워드/시맨틱 하이브리드로 선별된 세계관 (Writer RAG 와 동일 엔진)
    을 상한 내에서 조립한다.
    """
    project = await session.get(Project, project_id)
    if not project:
        return "프로젝트 정보를 찾을 수 없습니다."

    query_title = (episode_title or "").strip()
    query_plot = (episode_outline or "").strip() or query_title
    haystack = f"{query_title}\n{query_plot}"

    # --- Characters ---
    char_stmt = select(Character).where(Character.project_id == project_id)
    chars = list((await session.execute(char_stmt)).scalars().all())
    importance_rank = {"protagonist": 1, "deuteragonist": 2, "major": 3, "minor": 4}

    selected_chars = []
    for c in chars:
        imp = (c.importance or "minor").lower()
        if imp in PLOTTER_MAJOR_IMPORTANCE or (c.name and c.name in haystack):
            selected_chars.append(c)
    # 개요 매칭이 거의 없으면 중요도 상위만
    if len(selected_chars) < 3 and chars:
        sorted_all = sorted(chars, key=lambda x: importance_rank.get((x.importance or "").lower(), 99))
        for c in sorted_all:
            if c not in selected_chars:
                selected_chars.append(c)
            if len(selected_chars) >= min(5, char_limit):
                break

    selected_chars.sort(key=lambda x: importance_rank.get((x.importance or "").lower(), 99))
    selected_chars = selected_chars[:char_limit]

    # --- World settings: hybrid via retrieve core logic ---
    # 재사용: scene 제목/줄거리로 하이브리드 검색 후 포맷만 Plotter 용으로 축약
    hybrid = await retrieve_relevant_lores(
        session=session,
        project_id=project_id,
        scene_title=query_title or "회차 기획",
        scene_plot=query_plot or "회차 개요",
        limit=lore_limit,
        episode_id=None,
    )

    # retrieve_relevant_lores 는 참고자료 포함 포맷 — Plotter 에 그대로 쓰되 상한 적용
    char_block = "=== [등장인물 설정 — 필터됨] ===\n"
    if selected_chars:
        char_block += "\n".join(
            f"- {c.name} ({c.importance}): {c.description}" for c in selected_chars
        ) + "\n"
    else:
        char_block += "(등장인물 없음)\n"

    combined = char_block + "\n" + hybrid
    if len(combined) > max_chars:
        combined = combined[: max_chars - 20] + "\n…(토큰 상한 절단)"
    return combined
