import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import time
from httpx import AsyncClient, ASGITransport
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import selectinload

from app.main import app
from app.core.database import get_async_session, async_engine
from app.models import User, Project, Episode, Content
from tests.conftest import activate_user

@pytest.mark.asyncio
async def test_download_all_formats():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        timestamp = int(time.time())
        username = f"dl_user_{timestamp}"
        password = "secure_password_123"
        email = f"dl_{timestamp}@example.com"

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

        # 3. 테스트 데이터베이스 프로젝트 세팅
        async with AsyncSession(async_engine) as session:
            db_user_res = await session.execute(select(User).where(User.username == username))
            db_user = db_user_res.scalar_one()
            user_id = db_user.id

            proj = Project(
                user_id=user_id,
                title=f"다운로드 테스트 소설 {timestamp}",
                synopsis="테스트용 시놉시스",
                llm_provider="openai",
                llm_model="gpt-4o-mini"
            )
            session.add(proj)
            await session.flush()
            project_id = proj.id

            # Episode 1 (최종 승인본 존재)
            ep1 = Episode(
                project_id=project_id,
                episode_number=1,
                title="제 1화. 승인의 장"
            )
            session.add(ep1)
            await session.flush()
            ep1_id = ep1.id

            c1 = Content(
                episode_id=ep1_id,
                parent_id=None,
                content_text="이것은 최종 승인된 1화 본문입니다.",
                author_type="ai",
                version_tag="v1.0",
                is_approved=True
            )
            session.add(c1)

            # Episode 2 (최종 승인본 미존재 - Fallback 대상)
            ep2 = Episode(
                project_id=project_id,
                episode_number=2,
                title="제 2화. 대기 장"
            )
            session.add(ep2)
            await session.flush()
            ep2_id = ep2.id

            c2 = Content(
                episode_id=ep2_id,
                parent_id=None,
                content_text="이것은 아직 미승인이지만 가장 최신의 2화 본문입니다.",
                author_type="ai",
                version_tag="v1.0",
                is_approved=False
            )
            session.add(c2)
            await session.commit()

        # 4. 각 포맷별 다운로드 요청 테스트
        # 4.1 TXT 포맷 (의존성 없으므로 무조건 200 OK 반환되어야 함)
        res_txt = await ac.get(f"/projects/{project_id}/download?format=txt", headers=headers)
        assert res_txt.status_code == 200
        assert res_txt.headers["content-type"].startswith("text/plain")
        body_txt = res_txt.content.decode("utf-8")
        assert "제목: 다운로드 테스트 소설" in body_txt
        assert "이것은 최종 승인된 1화 본문입니다." in body_txt
        assert "이것은 아직 미승인이지만 가장 최신의 2화 본문입니다." in body_txt # Fallback 검증

        # 4.2 EPUB 포맷 검증
        res_epub = await ac.get(f"/projects/{project_id}/download?format=epub", headers=headers)
        assert res_epub.status_code in [200, 500]
        if res_epub.status_code == 200:
            assert res_epub.headers["content-type"].startswith("application/epub+zip")
            assert len(res_epub.content) > 0
        else:
            assert "Required package not installed" in res_epub.json()["detail"]

        # 4.3 PDF 포맷 검증
        res_pdf = await ac.get(f"/projects/{project_id}/download?format=pdf", headers=headers)
        assert res_pdf.status_code in [200, 500]
        if res_pdf.status_code == 200:
            assert res_pdf.headers["content-type"].startswith("application/pdf")
            assert len(res_pdf.content) > 0
        else:
            assert "Required package not installed" in res_pdf.json()["detail"]

        # 4.4 DOCX 포맷 검증
        res_docx = await ac.get(f"/projects/{project_id}/download?format=docx", headers=headers)
        assert res_docx.status_code in [200, 500]
        if res_docx.status_code == 200:
            assert res_docx.headers["content-type"].startswith("application/vnd.openxmlformats-officedocument.wordprocessingml.document")
            assert len(res_docx.content) > 0
        else:
            assert "Required package not installed" in res_docx.json()["detail"]

        # 5. 존재하지 않는 포맷 요청 (400 Bad Request)
        res_invalid = await ac.get(f"/projects/{project_id}/download?format=hwp", headers=headers)
        assert res_invalid.status_code == 400

        # 6. 테스트 데이터 정리
        async with AsyncSession(async_engine) as session:
            stmt = select(Project).where(Project.id == project_id)
            proj_res = await session.execute(stmt)
            db_proj = proj_res.scalar_one_or_none()
            if db_proj:
                await session.delete(db_proj)
                
            db_user_res = await session.execute(select(User).where(User.username == username))
            db_user = db_user_res.scalar_one_or_none()
            if db_user:
                await session.delete(db_user)
                
            await session.commit()
