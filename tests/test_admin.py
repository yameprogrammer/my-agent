import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import time
from httpx import AsyncClient, ASGITransport
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.main import app
from app.core.database import get_async_session
from app.models import User
from tests.conftest import activate_user

@pytest.mark.asyncio
async def test_admin_dashboard_and_controls_e2e():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        timestamp = int(time.time())
        admin_uname = f"admin_{timestamp}"
        user_uname = f"user_{timestamp}"
        password = "secure_password_123"

        # 1. 일반 유저 및 관리자 유저 등록
        reg_admin = await ac.post("/auth/register", json={"username": admin_uname, "password": password, "email": f"admin_{timestamp}@test.com"})
        reg_user = await ac.post("/auth/register", json={"username": user_uname, "password": password, "email": f"user_{timestamp}@test.com"})
        assert reg_admin.status_code == 201
        assert reg_user.status_code == 201

        # 2. 일반 유저는 텔레그램 승인 처리 (is_active=True, but is_admin=False)
        await activate_user(user_uname)
        
        # 3. 관리자 유저는 DB에서 직접 is_active=True 및 is_admin=True 처리
        async for session in get_async_session():
            db_admin_res = await session.execute(select(User).where(User.username == admin_uname))
            db_admin = db_admin_res.scalar_one()
            db_admin.is_active = True
            db_admin.is_admin = True
            session.add(db_admin)
            
            db_user_res = await session.execute(select(User).where(User.username == user_uname))
            db_user = db_user_res.scalar_one()
            user_id = db_user.id
            
            await session.commit()
            admin_id = db_admin.id
            break

        # 4. 로그인 토큰 발급
        # 4.1 일반 유저 토큰
        user_login = await ac.post("/auth/login", data={"username": user_uname, "password": password})
        assert user_login.status_code == 200
        user_token = user_login.json()["access_token"]
        user_headers = {"Authorization": f"Bearer {user_token}"}

        # 4.2 관리자 유저 토큰
        admin_login = await ac.post("/auth/login", data={"username": admin_uname, "password": password})
        assert admin_login.status_code == 200
        admin_token = admin_login.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # 5. 인가 가드 검증: 일반 유저가 어드민 API 접근 시도 (403 Forbidden)
        res_stats_user = await ac.get("/admin/stats", headers=user_headers)
        assert res_stats_user.status_code == 403
        assert "Admin role required" in res_stats_user.json()["detail"]

        # 6. 관리자 유저의 정상 어드민 기능 수행 검증
        # 6.1 Stats 통계 조회
        res_stats_admin = await ac.get("/admin/stats", headers=admin_headers)
        assert res_stats_admin.status_code == 200
        stats_data = res_stats_admin.json()
        assert stats_data["total_users"] >= 2
        assert stats_data["pending_users"] >= 0

        # 6.2 Users 목록 페이징 및 필터 검색 조회
        res_users = await ac.get(f"/admin/users?search={user_uname}", headers=admin_headers)
        assert res_users.status_code == 200
        users_data = res_users.json()
        assert users_data["total"] == 1
        assert users_data["items"][0]["username"] == user_uname

        # 7. 회원 관리 제어 액션 검증
        # 7.1 유저 거절(Reject) 처리
        res_reject = await ac.patch(f"/admin/users/{user_id}/status", json={"action": "reject"}, headers=admin_headers)
        assert res_reject.status_code == 200
        assert res_reject.json()["is_active"] is False
        assert res_reject.json()["rejected_at"] is not None

        # 7.2 유저 승인(Approve) 처리 (거절 상태에서 복구)
        res_approve = await ac.patch(f"/admin/users/{user_id}/status", json={"action": "approve"}, headers=admin_headers)
        assert res_approve.status_code == 200
        assert res_approve.json()["is_active"] is True
        assert res_approve.json()["rejected_at"] is None

        # 7.3 유저 일시정지(Suspend) 처리
        res_suspend = await ac.patch(f"/admin/users/{user_id}/status", json={"action": "suspend"}, headers=admin_headers)
        assert res_suspend.status_code == 200
        assert res_suspend.json()["is_active"] is False

        # 7.4 유저 권한 변경 (is_admin = True)
        res_role = await ac.patch(f"/admin/users/{user_id}/role", json={"is_admin": True}, headers=admin_headers)
        assert res_role.status_code == 200
        assert res_role.json()["is_admin"] is True

        # 8. 방어벽 예외 가드 검증: 어드민 자가 제어 시도 시 400 Bad Request
        # 8.1 자가 일시정지(Suspend) 차단
        res_self_suspend = await ac.patch(f"/admin/users/{admin_id}/status", json={"action": "suspend"}, headers=admin_headers)
        assert res_self_suspend.status_code == 400
        assert "Self-suspension" in res_self_suspend.json()["detail"]

        # 8.2 자가 권한 강등(Demote) 차단
        res_self_demote = await ac.patch(f"/admin/users/{admin_id}/role", json={"is_admin": False}, headers=admin_headers)
        assert res_self_demote.status_code == 400
        assert "Self-demotion" in res_self_demote.json()["detail"]

        # 9. 테스트 데이터 클린업 (Clean up)
        async for session in get_async_session():
            db_admin_res = await session.execute(select(User).where(User.username == admin_uname))
            db_admin = db_admin_res.scalar_one_or_none()
            if db_admin:
                await session.delete(db_admin)
                
            db_user_res = await session.execute(select(User).where(User.username == user_uname))
            db_user = db_user_res.scalar_one_or_none()
            if db_user:
                await session.delete(db_user)
                
            await session.commit()
            break


@pytest.mark.asyncio
async def test_admin_system_backup_and_restore():
    """
    어드민 백업 및 복구(backup/restore) API 작동과 JSON 파일 이관 흐름을 종합 검증합니다.
    """
    import json
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        timestamp = int(time.time())
        admin_uname = f"bk_admin_{timestamp}"
        password = "secure_password_123"

        # 1. 관리자 유저 등록 및 DB 권한 승격
        reg_admin = await ac.post("/auth/register", json={"username": admin_uname, "password": password, "email": f"bk_{timestamp}@test.com"})
        assert reg_admin.status_code == 201
        
        async for session in get_async_session():
            db_admin_res = await session.execute(select(User).where(User.username == admin_uname))
            db_admin = db_admin_res.scalar_one()
            db_admin.is_active = True
            db_admin.is_admin = True
            session.add(db_admin)
            await session.commit()
            admin_id = db_admin.id
            break

        # 2. 어드민 로그인
        admin_login = await ac.post("/auth/login", data={"username": admin_uname, "password": password})
        assert admin_login.status_code == 200
        admin_token = admin_login.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # 3. 시스템 글로벌 백업 (Export) 기동
        res_backup = await ac.get("/admin/backup", headers=admin_headers)
        print(f"DEBUG BACKUP RESPONSE: {res_backup.text}")
        assert res_backup.status_code == 200
        backup_json = res_backup.json()
        assert "projects" in backup_json
        assert "references" in backup_json

        # 4. 시스템 글로벌 복원 (Restore) 기동 (Export 받은 JSON 데이터 그대로 업로드)
        json_bytes = json.dumps(backup_json).encode("utf-8")
        files = {"file": ("backup.json", json_bytes, "application/json")}
        
        res_restore = await ac.post("/admin/restore", files=files, headers=admin_headers)
        assert res_restore.status_code == 200
        assert res_restore.json()["status"] == "success"

        # 9. 클린업
        # 복원을 수행하면 db_admin 계정이 삭제되었을 수 있으므로 다시 가입 여부를 확인해 삭제
        async for session in get_async_session():
            db_admin_res = await session.execute(select(User).where(User.username == admin_uname))
            db_admin = db_admin_res.scalar_one_or_none()
            if db_admin:
                await session.delete(db_admin)
                await session.commit()
            break

