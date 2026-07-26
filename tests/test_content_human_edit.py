"""
H1 Human Edit: author_type 검증 및 hybrid fork / 승인 E2E
"""
import sys
import os
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from pydantic import ValidationError
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.schemas.content import ContentCreate
from tests.conftest import activate_user


def test_content_create_author_type_validation():
    ok = ContentCreate(
        parent_id=None,
        version_tag="v1.0-draft",
        text="작가 초안입니다.",
        author_type="user",
    )
    assert ok.author_type == "user"

    hybrid = ContentCreate(
        parent_id=1,
        version_tag="v2.0-human",
        text="수정본",
        author_type="HYBRID",  # normalize
    )
    assert hybrid.author_type == "hybrid"

    with pytest.raises(ValidationError):
        ContentCreate(
            version_tag="v1",
            text="x",
            author_type="robot",
        )

    with pytest.raises(ValidationError):
        ContentCreate(
            version_tag="v1",
            text="   ",
            author_type="user",
        )


@pytest.mark.asyncio
async def test_human_edit_fork_and_approve_e2e():
    from app.core.database import init_db

    await init_db()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ts = int(time.time())
        username = f"he_user_{ts}"
        password = "testpassword123"

        await ac.post("/auth/register", json={"username": username, "password": password})
        await activate_user(username)
        login = await ac.post(
            "/auth/login", data={"username": username, "password": password}
        )
        assert login.status_code == 200
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        proj = await ac.post(
            "/projects",
            json={"title": f"HE 테스트 {ts}", "synopsis": "human edit"},
            headers=headers,
        )
        assert proj.status_code == 201
        project_id = proj.json()["id"]

        ep = await ac.post(
            f"/projects/{project_id}/episodes",
            json={
                "episode_number": 1,
                "title": "1화",
                "outline": "초안 기반 테스트",
            },
            headers=headers,
        )
        assert ep.status_code == 201, ep.text
        episode_id = ep.json()["id"]

        # AI 스타일 원본 버전
        c1 = await ac.post(
            f"/projects/{project_id}/episodes/{episode_id}/contents",
            json={
                "parent_id": None,
                "version_tag": "v1.0",
                "text": "루엘은 탑 위에 섰다.",
                "author_type": "ai",
            },
            headers=headers,
        )
        assert c1.status_code == 201, c1.text
        c1_id = c1.json()["id"]
        assert c1.json()["author_type"] == "ai"

        # Human hybrid fork
        c2 = await ac.post(
            f"/projects/{project_id}/episodes/{episode_id}/contents",
            json={
                "parent_id": c1_id,
                "version_tag": "v2.0-human",
                "text": "루엘은 폭풍우 속 탑 위에 홀로 섰다.",
                "author_type": "hybrid",
            },
            headers=headers,
        )
        assert c2.status_code == 201, c2.text
        c2_data = c2.json()
        assert c2_data["parent_id"] == c1_id
        assert c2_data["author_type"] == "hybrid"
        assert "폭풍우" in c2_data["text"]
        c2_id = c2_data["id"]

        # 승인
        ap = await ac.put(
            f"/projects/{project_id}/episodes/{episode_id}/contents/{c2_id}/approve",
            headers=headers,
        )
        assert ap.status_code == 200
        assert ap.json()["is_approved"] is True

        # 직접 초안 (root user)
        draft = await ac.post(
            f"/projects/{project_id}/episodes/{episode_id}/contents",
            json={
                "parent_id": None,
                "version_tag": "v3.0-draft",
                "text": "작가 순수 초안 문단.",
                "author_type": "user",
            },
            headers=headers,
        )
        assert draft.status_code == 201
        assert draft.json()["author_type"] == "user"

        # invalid author_type
        bad = await ac.post(
            f"/projects/{project_id}/episodes/{episode_id}/contents",
            json={
                "version_tag": "bad",
                "text": "x",
                "author_type": "robot",
            },
            headers=headers,
        )
        assert bad.status_code == 422
