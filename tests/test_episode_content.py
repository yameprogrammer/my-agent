import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import time
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import get_async_session, close_db
from app.models import User, Project, Episode, Content
from sqlmodel import select

@pytest.mark.asyncio
async def test_episode_and_content_version_tree_with_auth_guard():
    # DB 스키마 갱신 강제화 (is_approved 필드 연동 목적)
    from app.core.database import init_db
    await init_db()


    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        timestamp = int(time.time())
        
        # 1. 테스트 유저 생성 및 로그인
        owner_username = f"owner_e_{timestamp}"
        stranger_username = f"stranger_e_{timestamp}"
        password = "testpassword123"
        
        await ac.post("/auth/register", json={"username": owner_username, "password": password})
        await ac.post("/auth/register", json={"username": stranger_username, "password": password})
        
        # Owner 로그인 및 JWT 토큰 획득
        login_owner = await ac.post("/auth/login", data={"username": owner_username, "password": password})
        token_owner = login_owner.json()["access_token"]
        headers_owner = {"Authorization": f"Bearer {token_owner}"}
        
        # Stranger 로그인 및 JWT 토큰 획득
        login_stranger = await ac.post("/auth/login", data={"username": stranger_username, "password": password})
        token_stranger = login_stranger.json()["access_token"]
        headers_stranger = {"Authorization": f"Bearer {token_stranger}"}
        
        # 2. Owner 프로젝트 생성
        project_res = await ac.post(
            "/projects", 
            json={"title": "회차 테스트 소설", "synopsis": "버전 관리 시스템 테스트용 프로젝트"}, 
            headers=headers_owner
        )
        project_id = project_res.json()["id"]
        
        # 3. [회차 추가 테스트] POST /projects/{project_id}/episodes
        ep_res = await ac.post(
            f"/projects/{project_id}/episodes", 
            json={"episode_number": 1, "title": "제 1화: 운명의 만남"}, 
            headers=headers_owner
        )
        assert ep_res.status_code == 201
        episode_data = ep_res.json()
        episode_id = episode_data["id"]
        assert episode_data["title"] == "제 1화: 운명의 만남"
        print(f"\n[Create Episode Success] ID: {episode_id} in Project {project_id}")
        
        # 4. [본문 첫 번째 버전 생성 테스트] v1.0
        c1_res = await ac.post(
            f"/projects/{project_id}/episodes/{episode_id}/contents",
            json={"parent_id": None, "version_tag": "v1.0", "text": "루엘은 마법 제국에서 태어났다."},
            headers=headers_owner
        )
        assert c1_res.status_code == 201
        c1_data = c1_res.json()
        c1_id = c1_data["id"]
        assert c1_data["version_tag"] == "v1.0"
        assert c1_data["is_approved"] is False
        print(f"[Create Content v1.0 Success] ID: {c1_id}")
        
        # 5. [본문 두 번째 버전(브랜칭) 생성 테스트] v1.1-feedback (parent_id = v1.0)
        c2_res = await ac.post(
            f"/projects/{project_id}/episodes/{episode_id}/contents",
            json={"parent_id": c1_id, "version_tag": "v1.1-feedback", "text": "번개 천재 루엘은 신성 마법 제국에서 태어났다."},
            headers=headers_owner
        )
        assert c2_res.status_code == 201
        c2_data = c2_res.json()
        c2_id = c2_data["id"]
        assert c2_data["parent_id"] == c1_id
        assert c2_data["version_tag"] == "v1.1-feedback"
        print(f"[Create Content v1.1 Success] ID: {c2_id} (Parent ID: {c1_id})")
        
        # 6. [인가 차단 가드 테스트 1] Stranger가 Owner의 프로젝트 에피소드에 본문 생성을 시도할 때 -> 403 Forbidden
        c_fail_res = await ac.post(
            f"/projects/{project_id}/episodes/{episode_id}/contents",
            json={"parent_id": None, "version_tag": "v1.0-hacked", "text": "해킹 본문"},
            headers=headers_stranger
        )
        assert c_fail_res.status_code == 403
        
        # 7. [인가 차단 가드 테스트 2] Stranger가 Owner 본문 버전의 최종 승인 처리를 시도할 때 -> 403 Forbidden
        approve_fail_res = await ac.put(
            f"/projects/{project_id}/episodes/{episode_id}/contents/{c2_id}/approve",
            headers=headers_stranger
        )
        assert approve_fail_res.status_code == 403
        print("[Auth Guard Success] Stranger was blocked from creating/approving Content (403 Forbidden)")
        
        # 8. Owner가 v1.1-feedback 본문 버전을 최종 승인(Approve) 처리
        approve_res = await ac.put(
            f"/projects/{project_id}/episodes/{episode_id}/contents/{c2_id}/approve",
            headers=headers_owner
        )
        assert approve_res.status_code == 200
        assert approve_res.json()["is_approved"] is True
        print(f"[Approve Success] Content ID: {c2_id} approved as final version.")
        
        # 9. 승인 변경 후 목록 조회 및 중복 승인 자동 해제 검증
        list_res = await ac.get(f"/projects/{project_id}/episodes/{episode_id}/contents", headers=headers_owner)
        assert list_res.status_code == 200
        contents_list = list_res.json()
        assert len(contents_list) == 2
        
        # 구버전 v1.0 확인 -> is_approved 가 False 여야 함
        v1_0 = next(c for c in contents_list if c["version_tag"] == "v1.0")
        assert v1_0["is_approved"] is False
        
        # 승인된 v1.1-feedback 확인 -> is_approved 가 True 여야 함
        v1_1 = next(c for c in contents_list if c["version_tag"] == "v1.1-feedback")
        assert v1_1["is_approved"] is True
        print("[Double-Approve Prevention Check] Previously approved contents reset to False successfully.")
        
        # 10. 데이터베이스 클린업
        async for session in get_async_session():
            stmt_project = select(Project).where(Project.id == project_id)
            db_project = (await session.execute(stmt_project)).scalar_one_or_none()
            if db_project:
                await session.delete(db_project)
                
            stmt_users = select(User).where(User.username.in_([owner_username, stranger_username]))
            db_users = (await session.execute(stmt_users)).scalars().all()
            for u in db_users:
                await session.delete(u)
            await session.commit()
        print("[Cleanup] Test project and users cleaned up.")
        

