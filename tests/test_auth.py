import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import time
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import get_async_session, close_db
from app.models import User
from sqlmodel import select
from tests.conftest import activate_user

@pytest.mark.asyncio
async def test_auth_full_workflow():
    # FastAPI ASGI Application 연동을 위한 ASGI Transport 정의
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        
        # 1. 고유한 테스트 사용자 계정 정보 준비 (타임스탬프 활용)
        timestamp = int(time.time())
        username = f"auth_user_{timestamp}"
        password = "secure_password_123"
        email = f"auth_{timestamp}@example.com"
        
        # 2. 회원가입 API (/auth/register) 테스트
        register_payload = {
            "username": username,
            "password": password,
            "email": email
        }
        response = await ac.post("/auth/register", json=register_payload)
        assert response.status_code == 201
        user_data = response.json()
        assert user_data["username"] == username
        assert user_data["email"] == email
        assert "hashed_password" not in user_data  # 보안: hashed_password 컬럼이 API 응답에 노출되지 않는지 검증
        print(f"\n[Register Success] Created user: {username}")
        
        # 3. 중복 가입 방지 검증 (동일 ID로 재가입 시도)
        dup_response = await ac.post("/auth/register", json=register_payload)
        assert dup_response.status_code == 400
        print("[Register Failure Check] Duplicate username blocked correctly.")
        
        # 4. 미승인 계정 로그인 차단 (is_active=False → 403)
        pending_login = await ac.post(
            "/auth/login",
            data={"username": username, "password": password},
        )
        assert pending_login.status_code == 403
        print("[Login Pending Check] Inactive account login blocked correctly.")

        # 5. 관리자 승인 시뮬레이션 후 로그인
        await activate_user(username)

        wrong_login_payload = {
            "username": username,
            "password": "wrongpassword"
        }
        failed_login_res = await ac.post("/auth/login", data=wrong_login_payload)
        assert failed_login_res.status_code == 401
        print("[Login Failure Check] Wrong password login blocked correctly.")
        
        login_payload = {
            "username": username,
            "password": password
        }
        login_response = await ac.post("/auth/login", data=login_payload)
        assert login_response.status_code == 200
        token_data = login_response.json()
        assert token_data["token_type"] == "bearer"
        token = token_data["access_token"]
        print("[Login Success] Token issued successfully.")
        
        # 6. 보호된 API 접근 (/users/me) 테스트 - 인증 헤더 누락 시 401 권한 차단 검증
        unauth_response = await ac.get("/users/me")
        assert unauth_response.status_code == 401
        print("[Auth Guard Check] Token omission blocked correctly.")
        
        # 7. 보호된 API 접근 (/users/me) 테스트 - 올바른 토큰 첨부 시 접근 성공 검증
        headers = {"Authorization": f"Bearer {token}"}
        auth_response = await ac.get("/users/me", headers=headers)
        assert auth_response.status_code == 200
        me_data = auth_response.json()
        assert me_data["username"] == username
        assert me_data["email"] == email
        print(f"[Auth Guard Success] Returned current user: {me_data['username']}")
        
        # 8. 테스트 데이터베이스 정리 (Clean up)
        async for session in get_async_session():
            statement = select(User).where(User.username == username)
            result = await session.execute(statement)
            db_user = result.scalar_one_or_none()
            if db_user:
                await session.delete(db_user)
                await session.commit()
        print("[Cleanup] Test user removed from database successfully.")
        

