"""
H6: line diff + span replace + partial-rewrite schema/API helpers
"""
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from app.services.text_diff import build_line_diff, apply_span_replacement


def test_build_line_diff_insert_delete():
    left = "alpha\nbeta\ngamma"
    right = "alpha\nBETA\ngamma\ndelta"
    rows = build_line_diff(left, right)
    ops = {r["op"] for r in rows}
    assert "equal" in ops
    assert any(r["op"] in ("replace", "delete", "insert") for r in rows)
    # first line equal
    assert rows[0]["op"] == "equal"
    assert rows[0]["left"] == "alpha"


def test_build_line_diff_identical():
    rows = build_line_diff("a\nb", "a\nb")
    assert all(r["op"] == "equal" for r in rows)


def test_apply_span_replacement():
    full = "안녕하세요. 오늘 날씨가 좋습니다. 끝."
    sel = "오늘 날씨가 좋습니다."
    out = apply_span_replacement(full, sel, "폭풍이 몰아칩니다.")
    assert "폭풍이 몰아칩니다." in out
    assert "안녕하세요" in out
    assert sel not in out


def test_apply_span_missing_raises():
    with pytest.raises(ValueError):
        apply_span_replacement("abc", "zzz", "x")


@pytest.mark.asyncio
async def test_partial_rewrite_testing_mode_e2e():
    """TESTING=True 시 SpanRewriteAgent 모의 경로 + API 통합."""
    import time
    from httpx import AsyncClient, ASGITransport
    from app.main import app
    from app.core.database import init_db
    from tests.conftest import activate_user

    os.environ["TESTING"] = "True"
    await init_db()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ts = int(time.time())
        user = f"h6_{ts}"
        await ac.post("/auth/register", json={"username": user, "password": "testpassword123"})
        await activate_user(user)
        tok = (
            await ac.post("/auth/login", data={"username": user, "password": "testpassword123"})
        ).json()["access_token"]
        h = {"Authorization": f"Bearer {tok}"}

        proj = (
            await ac.post("/projects", json={"title": f"H6 {ts}", "synopsis": "t"}, headers=h)
        ).json()
        ep = (
            await ac.post(
                f"/projects/{proj['id']}/episodes",
                json={"episode_number": 1, "title": "1", "outline": "o"},
                headers=h,
            )
        ).json()

        full = "앞문장. 중간 문장입니다. 뒷문장."
        sel = "중간 문장입니다."
        c1 = (
            await ac.post(
                f"/projects/{proj['id']}/episodes/{ep['id']}/contents",
                json={
                    "version_tag": "v1",
                    "text": full,
                    "author_type": "ai",
                },
                headers=h,
            )
        ).json()

        pr = await ac.post(
            f"/projects/{proj['id']}/episodes/{ep['id']}/contents/partial-rewrite",
            json={
                "full_text": full,
                "selected_text": sel,
                "instruction": "더 긴장감 있게",
                "parent_content_id": c1["id"],
                "save_as_version": True,
                "version_tag": "v-partial",
            },
            headers=h,
        )
        assert pr.status_code == 200, pr.text
        body = pr.json()
        assert "[수정됨]" in body["rewritten_span"]
        assert sel not in body["full_text"] or "[수정됨]" in body["full_text"]
        assert body["content"] is not None
        assert body["content"]["author_type"] == "hybrid"
        assert body["content"]["parent_id"] == c1["id"]

        # Diff parent vs new
        d = await ac.get(
            f"/projects/{proj['id']}/episodes/{ep['id']}/contents/{c1['id']}/diff/{body['content']['id']}",
            headers=h,
        )
        assert d.status_code == 200
        assert "rows" in d.json()
        assert len(d.json()["rows"]) >= 1
