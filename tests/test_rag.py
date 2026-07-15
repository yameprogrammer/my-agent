import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import time
from unittest.mock import AsyncMock, patch, MagicMock
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import async_engine
from app.models import User, Project, WorldSetting, Character
from app.services.rag import generate_embedding, retrieve_relevant_lores

@pytest.mark.asyncio
async def test_generate_embedding():
    """
    generate_embedding 유틸리티가 지정된 프로바이더에 적절한 임베딩 모델을 인스턴스화하고
    임베딩 쿼리를 생성하는지 모킹 테스트를 진행합니다.
    """
    project = Project(
        llm_provider="openai",
        llm_model="gpt-4o-mini",
        api_key_override="test-key"
    )

    mock_embeddings = MagicMock()
    mock_embeddings.aembed_query = AsyncMock(return_value=[0.123] * 1536)

    with patch("app.services.rag.OpenAIEmbeddings", return_value=mock_embeddings):
        vector = await generate_embedding("테스트 텍스트", project)
        assert vector is not None
        assert len(vector) == 1536
        assert vector[0] == 0.123
        mock_embeddings.aembed_query.assert_called_once_with("테스트 텍스트")


@pytest.mark.asyncio
async def test_hybrid_rag_retrieval_e2e():
    """
    데이터베이스에 저장된 실제 데이터와 pgvector 모의 코사인 유사도 쿼리를 활용해
    키워드 매칭(인물/세계관) + 의미론적 pgvector 유사도 매칭이 결합된 하이브리드 RAG 작동을 검증합니다.
    """
    timestamp = int(time.time())
    username = f"rag_user_{timestamp}"
    password = "testpassword123"

    async with AsyncSession(async_engine) as db_session:
        user = User(username=username, hashed_password=password)
        db_session.add(user)
        await db_session.flush()
        user_id = user.id

        project = Project(
            user_id=user_id,
            title="마법 고등학교 소설",
            synopsis="소년이 마법을 배운다",
            llm_provider="openai",
            llm_model="gpt-4o-mini"
        )
        db_session.add(project)
        await db_session.flush()
        project_id = project.id

        # 1. 인물 설정집 등록
        char_protagonist = Character(
            project_id=project_id,
            name="알렌",
            description="화염 마법을 연습하는 고교생 주인공",
            importance="protagonist"
        )
        char_other = Character(
            project_id=project_id,
            name="카엘",
            description="얼음 마법의 대가이자 알렌의 경쟁자",
            importance="major"
        )
        db_session.add(char_protagonist)
        db_session.add(char_other)

        # 2. 세계관 설정집 등록 (일부만 임베딩 저장)
        setting_exact = WorldSetting(
            project_id=project_id,
            keyword="화염 마법",
            category="lore",
            description="알렌이 사용하는 강력한 파괴 마법",
            embedding=None
        )
        setting_semantic = WorldSetting(
            project_id=project_id,
            keyword="프로스트 기사단",
            category="concept",
            description="얼음 속성 기사들이 소속된 신비한 군대 조직",
            embedding=[0.1] * 1536  # 가상의 임베딩 벡터 저장
        )
        db_session.add(setting_exact)
        db_session.add(setting_semantic)
        await db_session.flush()
        
        char_p_id = char_protagonist.id
        char_o_id = char_other.id
        ws_e_id = setting_exact.id
        ws_s_id = setting_semantic.id
        
        await db_session.commit()

    # RAG 실행을 위한 입력 파라미터 정의
    scene_title = "카엘과의 갈등"
    scene_plot = "알렌은 화염 마법을 뿜어내며 맹훈련을 시작했다. 얼음 마법을 쓰는 카엘이 이를 비웃는다."

    # RAG 쿼리 벡터 모킹
    mock_vector = [0.1] * 1536
    
    with patch("app.services.rag.generate_embedding", return_value=mock_vector):
        async with AsyncSession(async_engine) as session:
            lore_context = await retrieve_relevant_lores(
                session=session,
                project_id=project_id,
                scene_title=scene_title,
                scene_plot=scene_plot,
                limit=3
            )
            
            # 검증 1: 씬 시놉시스에 정확한 이름("알렌", "카엘")과 키워드("화염 마법")가 존재하므로 키워드 RAG로 가져왔는지 확인
            assert "알렌" in lore_context
            assert "카엘" in lore_context
            assert "화염 마법" in lore_context
            
            # 검증 2: pgvector 임베딩 유사성(mock_vector)을 통해 "프로스트 기사단"도 매칭되어 출력되었는지 확인
            assert "프로스트 기사단" in lore_context
            
            print(f"\n[RAG Retrieval Context Output]:\n{lore_context}")

    # 3. 데이터 클린업
    async with AsyncSession(async_engine) as session:
        db_ws1 = await session.get(WorldSetting, ws_e_id)
        db_ws2 = await session.get(WorldSetting, ws_s_id)
        db_ch1 = await session.get(Character, char_p_id)
        db_ch2 = await session.get(Character, char_o_id)
        db_proj = await session.get(Project, project_id)
        db_user = await session.get(User, user_id)
        
        if db_ws1: await session.delete(db_ws1)
        if db_ws2: await session.delete(db_ws2)
        if db_ch1: await session.delete(db_ch1)
        if db_ch2: await session.delete(db_ch2)
        if db_proj: await session.delete(db_proj)
        if db_user: await session.delete(db_user)
        await session.commit()
        print("[Cleanup] RAG test data cleaned up.")


@pytest.mark.asyncio
async def test_episode_custom_rag_retrieval():
    """
    Episode-level RAG 세부 설정(rag_threshold, rag_limit, force_reference_ids)을 주었을 때
    지정된 매개변수대로 필터링 및 강제 병합이 일어나는지 검증합니다.
    """
    from app.models import Episode, ReferenceMaterial
    timestamp = int(time.time())
    username = f"rag_ep_{timestamp}"
    password = "testpassword123"

    async with AsyncSession(async_engine) as db_session:
        user = User(username=username, hashed_password=password)
        db_session.add(user)
        await db_session.flush()
        user_id = user.id

        project = Project(
            user_id=user_id,
            title="마법 테스트 소설",
            synopsis="RAG 커스텀 테스트",
            llm_provider="openai",
            llm_model="gpt-4o-mini"
        )
        db_session.add(project)
        await db_session.flush()

        # 강제 지정용 ReferenceMaterial 추가
        ref_force = ReferenceMaterial(
            project_id=project.id,
            title="강제 고증 자료",
            content="반드시 포함되어야 하는 극단적 상세 정보 내용입니다.",
            category="medical",
            source_type="manual"
        )
        # 일반 ReferenceMaterial 추가
        ref_normal = ReferenceMaterial(
            project_id=project.id,
            title="일반 무시할 고증 자료",
            content="이것은 강제 지정되지 않았고 관련 키워드가 씬에 없습니다.",
            category="etc",
            source_type="manual"
        )
        db_session.add(ref_force)
        db_session.add(ref_normal)
        await db_session.flush()

        # Episode 추가 (force_reference_ids 및 limit=1, threshold=0.9 극단값 설정)
        episode = Episode(
            project_id=project.id,
            episode_number=1,
            title="1화",
            outline="테스트",
            rag_threshold=0.9,  # 매우 높은 유사도 조건
            rag_limit=1,        # 1개만 가져오도록 제한
            force_reference_ids=str(ref_force.id)
        )
        db_session.add(episode)
        await db_session.flush()
        
        proj_id = project.id
        ep_id = episode.id
        
        await db_session.commit()

    async with AsyncSession(async_engine) as session:
        # 1. retrieve_relevant_lores 가동 (episode_id 전달)
        lore_context = await retrieve_relevant_lores(
            session=session,
            project_id=proj_id,
            scene_title="평범한 수련 씬",
            scene_plot="아무것도 매칭 안 됨",
            episode_id=ep_id
        )

        # 2. 검증: force_reference_ids로 지정한 자료는 반드시 포함되어야 함
        assert "강제 고증 자료" in lore_context
        # 3. 검증: rag_limit이 1로 설정되었으므로 일반 참고자료(Fallback) 등은 배제되어야 함
        assert "일반 무시할 고증 자료" not in lore_context

    # Cleanup
    async with AsyncSession(async_engine) as session:
        from sqlmodel import delete
        await session.execute(delete(Episode).where(Episode.project_id == proj_id))
        await session.execute(delete(ReferenceMaterial).where(ReferenceMaterial.project_id == proj_id))
        await session.execute(delete(Project).where(Project.id == proj_id))
        await session.execute(delete(User).where(User.id == user_id))
        await session.commit()

