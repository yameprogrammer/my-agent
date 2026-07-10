import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import time
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import get_async_session, close_db
from app.models import User, Project, WorldSetting, Character
from sqlmodel import select
from tests.conftest import activate_user

@pytest.mark.asyncio
async def test_lore_and_character_crud_with_auth_guard():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        timestamp = int(time.time())
        
        # 1. 테스트용 2명의 사용자 계정(owner, stranger) 생성 및 로그인
        owner_username = f"owner_l_{timestamp}"
        stranger_username = f"stranger_l_{timestamp}"
        password = "testpassword123"
        
        await ac.post("/auth/register", json={"username": owner_username, "password": password})
        await ac.post("/auth/register", json={"username": stranger_username, "password": password})
        await activate_user(owner_username)
        await activate_user(stranger_username)
        
        # Owner 로그인 및 JWT 획득
        login_owner = await ac.post("/auth/login", data={"username": owner_username, "password": password})
        token_owner = login_owner.json()["access_token"]
        headers_owner = {"Authorization": f"Bearer {token_owner}"}
        
        # Stranger 로그인 및 JWT 획득
        login_stranger = await ac.post("/auth/login", data={"username": stranger_username, "password": password})
        token_stranger = login_stranger.json()["access_token"]
        headers_stranger = {"Authorization": f"Bearer {token_stranger}"}
        
        # 2. Owner 프로젝트 생성
        project_res = await ac.post(
            "/projects", 
            json={"title": "세계관 테스트 프로젝트", "synopsis": "설정집과 캐릭터 추가 테스트 프로젝트"}, 
            headers=headers_owner
        )
        project_id = project_res.json()["id"]
        
        # 3. [세계관 설정 추가 테스트] POST /projects/{project_id}/world-settings
        lore_payload = {
            "keyword": "신성 마법 제국",
            "category": "lore",
            "description": "빛과 신성 마법을 숭상하는 제국"
        }
        res_lore_create = await ac.post(f"/projects/{project_id}/world-settings", json=lore_payload, headers=headers_owner)
        assert res_lore_create.status_code == 201
        lore_data = res_lore_create.json()
        lore_id = lore_data["id"]
        assert lore_data["keyword"] == "신성 마법 제국"
        print(f"\n[Create WorldSetting Success] ID: {lore_id} in Project {project_id}")
        
        # 4. [캐릭터 시트 추가 테스트] POST /projects/{project_id}/characters
        char_payload = {
            "name": "레온",
            "description": "신성 마법 제국의 제 1기사단장",
            "importance": "major"
        }
        res_char_create = await ac.post(f"/projects/{project_id}/characters", json=char_payload, headers=headers_owner)
        assert res_char_create.status_code == 201
        char_data = res_char_create.json()
        char_id = char_data["id"]
        assert char_data["name"] == "레온"
        print(f"[Create Character Success] ID: {char_id} in Project {project_id}")
        
        # 5. [인가 차단 가드 테스트 1] 타인(stranger)이 세계관 설정 생성을 시도할 때 -> 403 Forbidden
        res_lore_other_create = await ac.post(f"/projects/{project_id}/world-settings", json=lore_payload, headers=headers_stranger)
        assert res_lore_other_create.status_code == 403
        
        # 6. [인가 차단 가드 테스트 2] 타인(stranger)이 캐릭터 생성을 시도할 때 -> 403 Forbidden
        res_char_other_create = await ac.post(f"/projects/{project_id}/characters", json=char_payload, headers=headers_stranger)
        assert res_char_other_create.status_code == 403
        print("[Auth Guard Success] Stranger was blocked from creating lore/character in Owner's project (403 Forbidden)")
        
        # 7. Owner가 세계관 및 캐릭터 목록 조회
        res_lore_list = await ac.get(f"/projects/{project_id}/world-settings", headers=headers_owner)
        assert res_lore_list.status_code == 200
        assert len(res_lore_list.json()) >= 1
        
        res_char_list = await ac.get(f"/projects/{project_id}/characters", headers=headers_owner)
        assert res_char_list.status_code == 200
        assert len(res_char_list.json()) >= 1
        
        # 8. Owner가 세계관 수정
        res_lore_update = await ac.put(
            f"/projects/{project_id}/world-settings/{lore_id}", 
            json={"description": "어둠에 맞서 빛과 신성 마법을 숭상하는 제국"}, 
            headers=headers_owner
        )
        assert res_lore_update.status_code == 200
        assert res_lore_update.json()["description"] == "어둠에 맞서 빛과 신성 마법을 숭상하는 제국"
        
        # 9. Owner가 세계관 및 캐릭터 삭제
        res_lore_delete = await ac.delete(f"/projects/{project_id}/world-settings/{lore_id}", headers=headers_owner)
        assert res_lore_delete.status_code == 204
        
        res_char_delete = await ac.delete(f"/projects/{project_id}/characters/{char_id}", headers=headers_owner)
        assert res_char_delete.status_code == 204
        print("[Delete Success] Lore and character deleted by owner.")
        
        # 10. 삭제 후 조회 시도 -> 404 Not Found 확인
        res_lore_get_deleted = await ac.get(f"/projects/{project_id}/world-settings/{lore_id}", headers=headers_owner)
        assert res_lore_get_deleted.status_code == 404
        
        # 11. 데이터베이스 클린업
        async for session in get_async_session():
            statement_project = select(Project).where(Project.id == project_id)
            db_project = (await session.execute(statement_project)).scalar_one_or_none()
            if db_project:
                await session.delete(db_project)
                
            statement_users = select(User).where(User.username.in_([owner_username, stranger_username]))
            db_users = (await session.execute(statement_users)).scalars().all()
            for u in db_users:
                await session.delete(u)
        print("[Cleanup] Test project and users cleaned up.")
        

