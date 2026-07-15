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
from app.models import User, Project, ReferenceMaterial
from app.services.rag import retrieve_relevant_lores
from tests.conftest import activate_user

@pytest.mark.asyncio
async def test_reference_materials_and_research_agent_e2e():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        timestamp = int(time.time())
        username = f"writer_{timestamp}"
        password = "secure_password_123"

        # 1. 사용자 가입 및 활성화
        reg_res = await ac.post("/auth/register", json={
            "username": username,
            "password": password,
            "email": f"writer_{timestamp}@test.com"
        })
        assert reg_res.status_code == 201
        await activate_user(username)

        # 2. 로그인 토큰 획득
        login_res = await ac.post("/auth/login", data={
            "username": username,
            "password": password
        })
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 3. 신규 프로젝트 생성
        proj_res = await ac.post("/api/projects", headers=headers, json={
            "title": f"SF Space Opera {timestamp}",
            "synopsis": "인간과 AI의 우주 전쟁에 관한 대서사시.",
            "llm_provider": "openai",
            "llm_model": "gpt-4o-mini"
        })
        assert proj_res.status_code == 201
        project_id = proj_res.json()["id"]

        # 4. 참고 자료 수동 등록 (POST)
        ref1_res = await ac.post(
            f"/api/projects/{project_id}/references",
            headers=headers,
            json={
                "title": "웜홀 이동 시 조석력 영향",
                "content": "웜홀의 목(throat) 영역을 통과할 때 발생하는 강력한 중력 경사도는 선체를 전단시킬 수 있음.",
                "category": "science",
                "source_type": "academic",
                "source_url": "https://arxiv.org/abs/physics/wormhole"
            }
        )
        assert ref1_res.status_code == 201
        ref1_id = ref1_res.json()["id"]

        # 5. 참고 자료 목록 조회 및 카테고리 필터 검색 (GET)
        list_res = await ac.get(
            f"/api/projects/{project_id}/references?category=science&search=웜홀",
            headers=headers
        )
        assert list_res.status_code == 200
        list_data = list_res.json()
        assert list_data["total"] == 1
        assert list_data["items"][0]["id"] == ref1_id

        # 6. 리서치 에이전트 비동기 기동 API 검증 (POST)
        research_res = await ac.post(
            f"/api/projects/{project_id}/references/research",
            headers=headers,
            json={
                "topic": "19세기 증기기관 기술 고증",
                "category": "history",
                "target_sources": ["web", "academic", "sns"]
            }
        )
        assert research_res.status_code == 202
        assert research_res.json()["status"] == "processing"

        # 7. RAG 검색 및 컨텍스트 주입 함수 검증
        # 리서치 에이전트의 비동기 백그라운드 태스크가 mock search로 완료될 수 있도록 스레드를 동기 실행해 줌
        from app.services.researcher import run_researcher_agent
        await run_researcher_agent(
            project_id=project_id,
            topic="19세기 증기기관 기술 고증",
            category="history",
            target_sources=["web", "academic", "sns"]
        )

        async for session in get_async_session():
            # DB에 에이전트 보고서가 잘 적재되었는지 확인
            stmt = select(ReferenceMaterial).where(
                ReferenceMaterial.project_id == project_id,
                ReferenceMaterial.title.like("%19세기%")
            )
            report_res = await session.execute(stmt)
            report = report_res.scalars().first()
            assert report is not None
            assert report.category == "history"
            
            # RAG retrieve_relevant_lores 연계 작동 테스트
            context = await retrieve_relevant_lores(
                session=session,
                project_id=project_id,
                scene_title="기차가 어둠을 헤치고 은하수를 건너면",
                scene_plot="주인공이 19세기 식의 증기기관 우주선을 탑승한다.",
                limit=3
            )
            assert "고증 및 리서치 참고 자료" in context
            assert "19세기 증기기관" in context or "웜홀" in context

        # 8. 참고 자료 삭제 검증 (DELETE)
        del_res = await ac.delete(
            f"/api/projects/{project_id}/references/{ref1_id}",
            headers=headers
        )
        assert del_res.status_code == 204

        # 삭제 여부 DB 재검사
        async for session in get_async_session():
            ref1_check = await session.get(ReferenceMaterial, ref1_id)
            assert ref1_check is None
