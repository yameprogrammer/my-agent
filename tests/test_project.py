import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import time
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import get_async_session, close_db
from app.models import User, Project
from sqlmodel import select
from tests.conftest import activate_user

@pytest.mark.asyncio
async def test_project_crud_and_auth_guard():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        timestamp = int(time.time())
        
        # 1. 테스트용 2명의 유저(소유자 owner_a, 타인 stranger_b) 생성 및 로그인
        username_a = f"owner_a_{timestamp}"
        username_b = f"stranger_b_{timestamp}"
        password = "testpassword123"
        
        # 회원가입 → 관리자 승인 시뮬레이션
        await ac.post("/auth/register", json={"username": username_a, "password": password})
        await ac.post("/auth/register", json={"username": username_b, "password": password})
        await activate_user(username_a)
        await activate_user(username_b)
        
        # 로그인 및 JWT 획득 - User A (Owner)
        login_a = await ac.post("/auth/login", data={"username": username_a, "password": password})
        token_a = login_a.json()["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}
        
        # 로그인 및 JWT 획득 - User B (Stranger)
        login_b = await ac.post("/auth/login", data={"username": username_b, "password": password})
        token_b = login_b.json()["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}
        
        # 2. UserA가 소설 프로젝트 생성 (POST /projects)
        project_payload = {
            "title": "루엘의 번개 학교",
            "synopsis": "루엘이 번개 능력을 단련하는 모험기",
            "llm_provider": "openai",
            "llm_model": "gpt-4o-mini",
            "api_key_override": "user-key-dummy"
        }
        res_create = await ac.post("/projects", json=project_payload, headers=headers_a)
        assert res_create.status_code == 201
        project_data = res_create.json()
        project_id = project_data["id"]
        assert project_data["title"] == "루엘의 번개 학교"
        assert project_data["has_api_key"] is True  # 보안 필드 원본 비노출성 검증
        print(f"\n[Create Project Success] ID: {project_id} created by {username_a}")
        
        # 3. UserA가 본인 소유 프로젝트 리스트 조회 (GET /projects)
        res_list = await ac.get("/projects", headers=headers_a)
        assert res_list.status_code == 200
        list_data = res_list.json()
        assert len(list_data) >= 1
        assert list_data[0]["id"] == project_id
        
        # 4. UserA가 본인 소유 프로젝트 상세 조회 (GET /projects/{id})
        res_get_own = await ac.get(f"/projects/{project_id}", headers=headers_a)
        assert res_get_own.status_code == 200
        assert res_get_own.json()["title"] == "루엘의 번개 학교"
        
        # 5. [인가 가드 검증] UserB가 UserA의 프로젝트 상세 조회 시도 -> 403 Forbidden 차단 검증
        res_get_other = await ac.get(f"/projects/{project_id}", headers=headers_b)
        assert res_get_other.status_code == 403
        print("[Auth Guard Success] Stranger B was blocked from accessing Owner A's project (403 Forbidden)")
        
        # 6. UserA가 본인 소유 프로젝트 정보 수정 (PUT /projects/{id})
        update_payload = {
            "title": "루엘의 번개 마법학교 (개정판)",
            "synopsis": "루엘이 병마를 딛고 결투에서 승리하는 시놉시스"
        }
        res_update = await ac.put(f"/projects/{project_id}", json=update_payload, headers=headers_a)
        assert res_update.status_code == 200
        updated_data = res_update.json()
        assert updated_data["title"] == "루엘의 번개 마법학교 (개정판)"
        assert updated_data["synopsis"] == "루엘이 병마를 딛고 결투에서 승리하는 시놉시스"
        print("[Update Project Success] Project title and synopsis updated.")
        
        # 7. UserA가 본인 소유 프로젝트 삭제 (DELETE /projects/{id})
        res_delete = await ac.delete(f"/projects/{project_id}", headers=headers_a)
        assert res_delete.status_code == 204
        print("[Delete Project Success] Project deleted.")
        
        # 8. 삭제 후 재조회 시도 -> 404 Not Found 확인
        res_get_deleted = await ac.get(f"/projects/{project_id}", headers=headers_a)
        assert res_get_deleted.status_code == 404
        print("[Post-Delete Check] Accessing deleted project returns 404 Not Found.")
        
        # 9. 데이터베이스 클린업 (테스트 계정 삭제)
        async for session in get_async_session():
            statement = select(User).where(User.username.in_([username_a, username_b]))
            result = await session.execute(statement)
            db_users = result.scalars().all()
            for u in db_users:
                await session.delete(u)
            await session.commit()
        print("[Cleanup] Test users removed successfully.")
        

