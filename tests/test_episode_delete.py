"""회차 삭제: Content 버전 트리 / PlotThread / AgentUsageLog FK 정리 검증."""
import os
import sys
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from httpx import AsyncClient, ASGITransport
from sqlmodel import select

from app.main import app
from app.core.database import get_async_session, init_db
from app.models import AgentUsageLog, Content, Episode, PlotThread, Project, User
from tests.conftest import activate_user


@pytest.mark.asyncio
async def test_delete_episode_with_related_fks():
    """본문 버전 트리·복선·사용 로그가 있어도 회차 삭제가 204로 성공해야 한다."""
    await init_db()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ts = int(time.time() * 1000)
        username = f"del_ep_owner_{ts}"
        password = "testpassword123"

        await ac.post("/auth/register", json={"username": username, "password": password})
        await activate_user(username)
        login = await ac.post("/auth/login", data={"username": username, "password": password})
        assert login.status_code == 200
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        proj = await ac.post(
            "/projects",
            json={"title": "회차 삭제 테스트", "synopsis": "FK 정리 검증"},
            headers=headers,
        )
        assert proj.status_code == 201
        project_id = proj.json()["id"]

        # 회차 + 본문 버전 트리 (parent_id 자기참조)
        ep = await ac.post(
            f"/projects/{project_id}/episodes",
            json={"episode_number": 1, "title": "삭제 대상 회차"},
            headers=headers,
        )
        assert ep.status_code == 201
        episode_id = ep.json()["id"]

        c1 = await ac.post(
            f"/projects/{project_id}/episodes/{episode_id}/contents",
            json={"parent_id": None, "version_tag": "v1.0", "text": "초안 본문"},
            headers=headers,
        )
        assert c1.status_code == 201
        c1_id = c1.json()["id"]

        c2 = await ac.post(
            f"/projects/{project_id}/episodes/{episode_id}/contents",
            json={"parent_id": c1_id, "version_tag": "v1.1", "text": "수정 본문"},
            headers=headers,
        )
        assert c2.status_code == 201

        # 복선이 해당 회차를 참조
        pt = await ac.post(
            f"/projects/{project_id}/plot-threads",
            json={
                "title": "복선 A",
                "description": "심은 복선",
                "status": "planted",
                "planted_episode_id": episode_id,
                "target_episode_id": episode_id,
            },
            headers=headers,
        )
        assert pt.status_code == 201, pt.text
        plot_thread_id = pt.json()["id"]

        # 사용 로그가 해당 회차를 참조
        async for session in get_async_session():
            session.add(
                AgentUsageLog(
                    project_id=project_id,
                    episode_id=episode_id,
                    agent_role="writer",
                    latency_ms=10,
                    success=True,
                )
            )
            await session.commit()
            break

        # 삭제 — 기존에는 FK 위반으로 500
        del_res = await ac.delete(
            f"/projects/{project_id}/episodes/{episode_id}",
            headers=headers,
        )
        assert del_res.status_code == 204, del_res.text

        # 회차·본문 제거 확인
        get_ep = await ac.get(
            f"/projects/{project_id}/episodes/{episode_id}",
            headers=headers,
        )
        assert get_ep.status_code == 404

        async for session in get_async_session():
            contents = (
                await session.execute(select(Content).where(Content.episode_id == episode_id))
            ).scalars().all()
            assert contents == []

            episode = await session.get(Episode, episode_id)
            assert episode is None

            # 복선은 유지되고 회차 FK만 NULL
            plot = await session.get(PlotThread, plot_thread_id)
            assert plot is not None
            assert plot.planted_episode_id is None
            assert plot.target_episode_id is None

            # 사용 로그는 유지되고 episode_id만 NULL
            logs = (
                await session.execute(
                    select(AgentUsageLog).where(AgentUsageLog.project_id == project_id)
                )
            ).scalars().all()
            assert len(logs) >= 1
            assert all(log.episode_id is None for log in logs)

            # cleanup
            db_project = await session.get(Project, project_id)
            if db_project:
                await session.delete(db_project)
            users = (
                await session.execute(select(User).where(User.username == username))
            ).scalars().all()
            for u in users:
                await session.delete(u)
            await session.commit()
            break


@pytest.mark.asyncio
async def test_delete_empty_episode():
    """연관 데이터 없는 빈 회차 삭제도 204."""
    await init_db()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ts = int(time.time() * 1000)
        username = f"del_ep_empty_{ts}"
        password = "testpassword123"

        await ac.post("/auth/register", json={"username": username, "password": password})
        await activate_user(username)
        login = await ac.post("/auth/login", data={"username": username, "password": password})
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        proj = await ac.post(
            "/projects",
            json={"title": "빈 회차 삭제", "synopsis": "x"},
            headers=headers,
        )
        project_id = proj.json()["id"]

        ep = await ac.post(
            f"/projects/{project_id}/episodes",
            json={"episode_number": 1, "title": "빈 회차"},
            headers=headers,
        )
        episode_id = ep.json()["id"]

        del_res = await ac.delete(
            f"/projects/{project_id}/episodes/{episode_id}",
            headers=headers,
        )
        assert del_res.status_code == 204, del_res.text

        async for session in get_async_session():
            db_project = await session.get(Project, project_id)
            if db_project:
                await session.delete(db_project)
            users = (
                await session.execute(select(User).where(User.username == username))
            ).scalars().all()
            for u in users:
                await session.delete(u)
            await session.commit()
            break
