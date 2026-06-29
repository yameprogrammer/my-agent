import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from sqlmodel import select
from app.core.database import init_db, get_async_session, close_db
from app.models import User, Project, WorldSetting, Character, Episode, Content

async def test_db_setup_and_flow():
    # 1. DB 초기화 (테이블 생성 및 확장 활성화)
    print("\n--- [Step 1] Initializing Database and enabling pgvector ---")
    await init_db()
    
    # 2. 세션 획득 및 데이터 적재
    print("\n--- [Step 2] Inserting mock data to verify schema relationships ---")
    async for session in get_async_session():
        # User 생성 (이전 실패 데이터와 충돌을 방지하기 위해 유니크한 닉네임 생성)
        import time
        unique_username = f"testuser_{int(time.time())}"
        user = User(username=unique_username, hashed_password="hashed_password_example")
        session.add(user)
        await session.commit()
        await session.refresh(user)
        print(f"Created User: {user.username} (ID: {user.id})")
        
        # Project 생성
        project = Project(
            user_id=user.id, 
            title="검과 번개의 학교", 
            synopsis="아르카나 마법학교의 번개 천재 루엘의 모험"
        )
        session.add(project)
        await session.commit()
        await session.refresh(project)
        print(f"Created Project: {project.title} (ID: {project.id})")
        
        # 1536차원 더미 임베딩 생성 (OpenAI text-embedding-3-small 대응)
        dummy_embedding = [0.1] * 1536
        
        # WorldSetting (Lorebook) 생성
        lore1 = WorldSetting(
            project_id=project.id, 
            keyword="아르카나 마법학교", 
            category="location", 
            description="붉은 벽돌이 인상적인 역사 깊은 학교",
            embedding=dummy_embedding
        )
        session.add(lore1)
        await session.commit()
        await session.refresh(lore1)
        print(f"Created WorldSetting: {lore1.keyword} (ID: {lore1.id})")
        
        # Character 생성
        char1 = Character(
            project_id=project.id,
            name="루엘",
            description="번개 마법의 천재이지만 병약한 소년",
            importance="protagonist"
        )
        session.add(char1)
        await session.commit()
        await session.refresh(char1)
        print(f"Created Character: {char1.name} (ID: {char1.id})")
        
        # Episode 생성
        episode = Episode(
            project_id=project.id,
            episode_number=1,
            title="제 1화: 번개의 낙인",
            outline="루엘이 마법학교에 입학하여 라이벌을 만나는 내용"
        )
        session.add(episode)
        await session.commit()
        await session.refresh(episode)
        print(f"Created Episode: {episode.title} (ID: {episode.id})")
        
        # Content (Version Tree) 생성 - 루트 초안
        content_v1 = Content(
            episode_id=episode.id,
            content_text="루엘은 붉은 벽돌의 아르카나 마법학교 앞에 섰다. 가슴이 뛰었다.",
            author_type="ai",
            version_tag="v1.0"
        )
        session.add(content_v1)
        await session.commit()
        await session.refresh(content_v1)
        print(f"Created Content Root: {content_v1.version_tag} (ID: {content_v1.id})")
        
        # Content - 유저 피드백 반영 본문 (자식 초안)
        content_v1_1 = Content(
            episode_id=episode.id,
            parent_id=content_v1.id,
            content_text="루엘은 붉은 벽돌의 아르카나 마법학교 앞에 섰다. 병약한 몸이었지만 오늘은 가슴이 뛰었다.",
            author_type="hybrid",
            version_tag="v1.1-feedback-applied"
        )
        session.add(content_v1_1)
        await session.commit()
        await session.refresh(content_v1_1)
        print(f"Created Content Branch: {content_v1_1.version_tag} (ID: {content_v1_1.id}, Parent ID: {content_v1_1.parent_id})")

        # 3. pgvector 유사도 검색 기능 테스트
        print("\n--- [Step 3] Testing pgvector similarity search ---")
        # 검색용 타겟 벡터 (1536차원) - 0.11 근처로 세팅하여 더미 벡터와 매칭 유도
        target_vector = [0.11] * 1536
        statement = (
            select(WorldSetting)
            .where(WorldSetting.project_id == project.id)
            # 코사인 거리 (cosine_distance) 연산
            .order_by(WorldSetting.embedding.cosine_distance(target_vector))
            .limit(1)
        )
        results = await session.execute(statement)
        matched_lore = results.scalar_one_or_none()
        
        assert matched_lore is not None
        assert matched_lore.keyword == "아르카나 마법학교"
        print(f"Vector Search Success! Matched keyword: {matched_lore.keyword}")
        
        # 4. 데이터 삭제 및 리셋 (Clean up)
        print("\n--- [Step 4] Cleaning up test data ---")
        # 자식 노드를 먼저 명시적으로 지우고 커밋하여 부모와의 FK 연결 해제
        await session.delete(content_v1_1)
        await session.commit()
        
        # 이후 부모 노드 및 다른 관련 데이터 삭제
        await session.delete(content_v1)
        await session.delete(episode)
        await session.delete(char1)
        await session.delete(lore1)
        await session.delete(project)
        await session.delete(user)
        await session.commit()
        print("Test data clean up complete.")
        
    await close_db()
    print("\n--- [Success] Database connection and pgvector workflow successfully verified! ---")

if __name__ == "__main__":
    asyncio.run(test_db_setup_and_flow())
