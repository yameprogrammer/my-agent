import asyncio
import sys
from sqlmodel import select

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from app.core.database import get_async_session
from app.models import User
from app.core.security import hash_password

async def main():
    username = "p001"
    raw_password = "password123"
    email = "p001@example.com"
    
    async for session in get_async_session():
        # 1. 외래키 제약조건 우회를 위해 Project 먼저 전부 삭제
        print("Cleaning up old test projects...")
        from app.models import Project
        stmt_proj = select(Project)
        res_proj = await session.execute(stmt_proj)
        all_projects = res_proj.scalars().all()
        for p in all_projects:
            await session.delete(p)
        await session.commit()

        # 2. 기존 유저와 중복 이메일 유저 전부 날리기
        print("Cleaning up old test users...")
        stmt_all = select(User)
        res_all = await session.execute(stmt_all)
        all_users = res_all.scalars().all()
        for u in all_users:
            await session.delete(u)
        await session.commit()
        print("Cleanup done.")
        
        # 3. 신규 사용자 생성 및 자동 승인 완료 처리
        hashed = hash_password(raw_password)
        user = User(
            username=username,
            hashed_password=hashed,
            email=email,
            is_active=True,  # 수동 활성화
            is_admin=True
        )
        
        session.add(user)
        await session.commit()
        await session.refresh(user)
        
        print(f"\n✅ 계정 생성 및 수동 승인 완료!")
        print(f"👉 사용자명 (ID): {user.username}")
        print(f"👉 비밀번호: {raw_password}")
        print(f"👉 이메일: {user.email}")
        print(f"👉 계정 상태: Active (승인됨, 즉시 로그인 가능)")
        return

if __name__ == "__main__":
    import os
    os.environ["TESTING"] = "False" # Use development DB
    asyncio.run(main())
