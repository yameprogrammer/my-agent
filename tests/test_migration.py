import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import time
import json
from httpx import AsyncClient, ASGITransport
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import selectinload

from app.main import app
from app.core.database import get_async_session, async_engine
from app.models import User, Project, WorldSetting, Character, Episode, Content
from tests.conftest import activate_user

@pytest.mark.asyncio
async def test_project_migration_flow_e2e():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        timestamp = int(time.time())
        username = f"mig_user_{timestamp}"
        password = "secure_password_123"
        email = f"mig_{timestamp}@example.com"

        # 1. 테스트 유저 등록 및 활성화
        register_payload = {"username": username, "password": password, "email": email}
        reg_res = await ac.post("/auth/register", json=register_payload)
        assert reg_res.status_code == 201
        await activate_user(username)

        # 2. 로그인 토큰 획득
        login_res = await ac.post("/auth/login", data={"username": username, "password": password})
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 3. 데이터베이스 세션을 통해 테스트용 소설 프로젝트 구축
        async with AsyncSession(async_engine) as session:
            db_user_res = await session.execute(select(User).where(User.username == username))
            db_user = db_user_res.scalar_one()
            user_id = db_user.id

            # Project
            proj = Project(
                user_id=user_id,
                title=f"마이그레이션 판타지 소설 {timestamp}",
                synopsis="테스트용 시놉시스",
                llm_provider="google",
                llm_model="gemini-1.5-flash",
                api_key_override="test-secret-key-override"
            )
            session.add(proj)
            await session.flush()
            project_id = proj.id

            # WorldSetting
            ws = WorldSetting(
                project_id=project_id,
                keyword="아르카나 마법",
                category="lore",
                description="아르카나 에너지를 다루는 마법 지침"
            )
            session.add(ws)

            # Character
            char = Character(
                project_id=project_id,
                name="마르쿠스",
                description="주인공의 마법 스승",
                importance="major"
            )
            session.add(char)

            # Episode
            ep = Episode(
                project_id=project_id,
                episode_number=1,
                title="제 1화: 운명의 만남"
            )
            session.add(ep)
            await session.flush()
            episode_id = ep.id

            # Content 1 (Parent)
            c1 = Content(
                episode_id=episode_id,
                parent_id=None,
                content_text="마르쿠스는 깊은 한숨을 쉬며 책을 덮었다.",
                author_type="ai",
                version_tag="v1.0",
                is_approved=False
            )
            session.add(c1)
            await session.flush()
            c1_id = c1.id

            # Content 2 (Child)
            c2 = Content(
                episode_id=episode_id,
                parent_id=c1_id,
                content_text="마르쿠스는 깊은 한숨을 쉬며 마법 고서를 덮어 보관했다.",
                author_type="hybrid",
                version_tag="v1.1",
                is_approved=True
            )
            session.add(c2)
            await session.commit()

        # 4. Export API 호출 테스트
        export_res = await ac.get(f"/migration/export/{project_id}", headers=headers)
        assert export_res.status_code == 200
        export_data = export_res.json()
        assert export_data["title"] == f"마이그레이션 판타지 소설 {timestamp}"
        assert export_data["api_key_override"] == "test-secret-key-override" # 복호화 검증
        assert len(export_data["world_settings"]) == 1
        assert len(export_data["characters"]) == 1
        assert len(export_data["episodes"]) == 1
        assert len(export_data["episodes"][0]["contents"]) == 2

        # 5. Import API 호출 테스트 (동일 유저의 다른 프로젝트로 임포트)
        # JSON 문자열을 바이트 스트림 파일로 모킹하여 업로드 전송
        json_bytes = json.dumps(export_data).encode("utf-8")
        files = {"file": ("export.json", json_bytes, "application/json")}
        
        import_res = await ac.post("/migration/import", files=files, headers=headers)
        print("\n=== DEBUG IMPORT RES ===", import_res.json())
        assert import_res.status_code == 201
        import_res_data = import_res.json()
        assert import_res_data["status"] == "success"
        new_project_id = import_res_data["new_project_id"]

        # 6. 가져오기 및 트리 구조 복원 무결성 정밀 검증
        async with AsyncSession(async_engine) as session:
            # 신규 프로젝트 및 관계 탐색
            stmt = (
                select(Project)
                .where(Project.id == new_project_id)
                .options(
                    selectinload(Project.world_settings),
                    selectinload(Project.characters),
                    selectinload(Project.episodes).selectinload(Episode.contents)
                )
            )
            res = await session.execute(stmt)
            new_proj = res.scalars().first()
            
            assert new_proj is not None
            assert new_proj.title == f"마이그레이션 판타지 소설 {timestamp}"
            assert len(new_proj.world_settings) == 1
            assert new_proj.world_settings[0].keyword == "아르카나 마법"
            assert len(new_proj.characters) == 1
            assert new_proj.characters[0].name == "마르쿠스"
            assert len(new_proj.episodes) == 1
            
            new_ep = new_proj.episodes[0]
            assert new_ep.title == "제 1화: 운명의 만남"
            assert len(new_ep.contents) == 2
            
            # Content 버전 트리 매핑 구조 무결성 검증
            # parent_id가 없는 놈(c1 대조군)과 있는 놈(c2 대조군) 구분
            sorted_new_contents = sorted(new_ep.contents, key=lambda c: c.created_at)
            new_c1 = sorted_new_contents[0]
            new_c2 = sorted_new_contents[1]
            
            assert new_c1.parent_id is None
            assert new_c2.parent_id == new_c1.id # 트리 관계 이관 성공 검증!
            assert new_c2.is_approved is True
            assert new_c2.author_type == "hybrid"

            # 7. 테스트 데이터 청소 (Clean up)
            # 신규 이관 데이터 삭제
            await session.delete(new_proj) # Cascade 삭제로 하위 데이터 모두 삭제
            
            # 구 테스트 데이터 삭제
            old_proj_stmt = (
                select(Project)
                .where(Project.id == project_id)
                .options(
                    selectinload(Project.world_settings),
                    selectinload(Project.characters),
                    selectinload(Project.episodes).selectinload(Episode.contents)
                )
            )
            old_proj_res = await session.execute(old_proj_stmt)
            old_proj = old_proj_res.scalars().first()
            if old_proj:
                await session.delete(old_proj)
                
            db_user_res = await session.execute(select(User).where(User.username == username))
            db_user = db_user_res.scalar_one_or_none()
            if db_user:
                await session.delete(db_user)
                
            await session.commit()
