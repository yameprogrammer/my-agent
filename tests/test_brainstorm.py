import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import time
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import get_async_session
from app.models import User, Project, WorldSetting, Character
from sqlmodel import select
from tests.conftest import activate_user
from app.services.agents import BrainstormResult, LoreSuggestion, CharacterSuggestion

@pytest.mark.asyncio
async def test_brainstorm_api_e2e():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        timestamp = int(time.time())
        
        # 1. 사용자 계정 생성 및 로그인
        owner_username = f"owner_b_{timestamp}"
        stranger_username = f"stranger_b_{timestamp}"
        password = "testpassword123"
        
        await ac.post("/auth/register", json={"username": owner_username, "password": password})
        await ac.post("/auth/register", json={"username": stranger_username, "password": password})
        await activate_user(owner_username)
        await activate_user(stranger_username)
        
        login_owner = await ac.post("/auth/login", data={"username": owner_username, "password": password})
        token_owner = login_owner.json()["access_token"]
        headers_owner = {"Authorization": f"Bearer {token_owner}"}
        
        login_stranger = await ac.post("/auth/login", data={"username": stranger_username, "password": password})
        token_stranger = login_stranger.json()["access_token"]
        headers_stranger = {"Authorization": f"Bearer {token_stranger}"}
        
        # 2. Owner 프로젝트 생성 (시놉시스 있음)
        project_res = await ac.post(
            "/projects", 
            json={
                "title": "브레인스토밍 소설",
                "synopsis": "인류 최후의 마법 학원을 배경으로 한 판타지 소설",
                "api_key_override": "dummy-key"
            }, 
            headers=headers_owner
        )
        project_id = project_res.json()["id"]

        # 3. 프로젝트 생성 (시놉시스 없음 - 에러용)
        project_no_syn_res = await ac.post(
            "/projects", 
            json={
                "title": "시놉시스 없는 소설",
                "synopsis": "",
                "api_key_override": "dummy-key"
            }, 
            headers=headers_owner
        )
        project_no_syn_id = project_no_syn_res.json()["id"]
        
        # 4. 시놉시스가 없는 경우 가드 확인 (400 Bad Request)
        res_no_syn = await ac.post(
            f"/projects/{project_no_syn_id}/brainstorm",
            json={"user_instruction": "설정 추천해줘"},
            headers=headers_owner
        )
        assert res_no_syn.status_code == 400
        assert "시놉시스가 비어 있습니다" in res_no_syn.json()["detail"]

        # 5. 권한 가드 확인 (타인이 접근하는 경우 403 Forbidden)
        res_stranger = await ac.post(
            f"/projects/{project_id}/brainstorm",
            json={"user_instruction": "설정 추천해줘"},
            headers=headers_stranger
        )
        assert res_stranger.status_code == 403

        # 6. 정상 브레인스토밍 API 호출 테스트 (모킹 적용)
        mock_result = BrainstormResult(
            lores=[
                LoreSuggestion(keyword="신화 속 아카데미", category="location", description="오래전 가려진 전설의 아카데미"),
            ],
            characters=[
                CharacterSuggestion(name="아셀", importance="protagonist", description="마나를 느끼지 못하는 소년"),
            ],
        )

        with patch("app.routers.brainstorm.BrainstormAgent") as mock_agent_cls:
            mock_agent_instance = AsyncMock()
            mock_agent_instance.run.return_value = mock_result
            mock_agent_cls.return_value = mock_agent_instance

            res_brainstorm = await ac.post(
                f"/projects/{project_id}/brainstorm",
                json={"user_instruction": "마법 아카데미 설정을 지어줘"},
                headers=headers_owner
            )
            assert res_brainstorm.status_code == 200
            data = res_brainstorm.json()
            assert "lores" in data
            assert len(data["lores"]) == 1
            assert data["lores"][0]["keyword"] == "신화 속 아카데미"
            assert data["characters"][0]["name"] == "아셀"
            # 기존 DB 항목이 없으므로 create로 태깅
            assert data["lores"][0]["change_type"] == "create"
            assert data["characters"][0]["change_type"] == "create"
            assert data["create_count"] == 2
            assert data["update_count"] == 0

        # 7. 기획 반영 (apply) 테스트
        apply_payload = {
            "lores": [
                {"keyword": "신화 속 아카데미", "category": "location", "description": "오래전 가려진 전설의 아카데미"}
            ],
            "characters": [
                {"name": "아셀", "importance": "protagonist", "description": "마나를 느끼지 못하는 소년"}
            ]
        }

        # 타인 반영 차단 테스트 (403 Forbidden)
        res_apply_stranger = await ac.post(
            f"/projects/{project_id}/brainstorm/apply",
            json=apply_payload,
            headers=headers_stranger
        )
        assert res_apply_stranger.status_code == 403

        # 정상 반영 테스트
        res_apply = await ac.post(
            f"/projects/{project_id}/brainstorm/apply",
            json=apply_payload,
            headers=headers_owner
        )
        assert res_apply.status_code == 200
        apply_res = res_apply.json()
        assert apply_res["status"] == "success"
        assert apply_res["added_lores"] == 1
        assert apply_res["added_characters"] == 1

        # 7.5. 기획 업데이트 (이미 존재하는 항목 덮어쓰기) 테스트
        update_payload = {
            "lores": [
                {"keyword": "신화 속 아카데미", "category": "location", "description": "가려진 전설의 아카데미 - 수정됨"}
            ],
            "characters": [
                {"name": "아셀", "importance": "deuteragonist", "description": "마나를 다룰 수 있게 된 소년"}
            ]
        }
        res_update = await ac.post(
            f"/projects/{project_id}/brainstorm/apply",
            json=update_payload,
            headers=headers_owner
        )
        assert res_update.status_code == 200
        update_res = res_update.json()
        assert update_res["status"] == "success"
        assert update_res["added_lores"] == 0
        assert update_res["updated_lores"] == 1
        assert update_res["added_characters"] == 0
        assert update_res["updated_characters"] == 1

        # 7.6. 피드백 기반 기존 항목 수정안(update 태깅) 테스트
        mock_update_result = BrainstormResult(
            lores=[
                LoreSuggestion(
                    keyword="신화 속 아카데미",
                    category="location",
                    description="가려진 전설의 아카데미 — 더 엄격한 마법 대가가 존재하는 공간",
                    change_type="update",
                    change_summary="마법 체계를 엄격한 대가 규칙으로 수정",
                ),
            ],
            characters=[
                CharacterSuggestion(
                    name="아셀",
                    importance="protagonist",
                    description="소심하고 내향적이지만 잠재된 마나를 깨우려는 소년",
                    change_type="update",
                    change_summary="성격을 소심·내향적으로 재정의",
                ),
            ],
        )
        with patch("app.routers.brainstorm.BrainstormAgent") as mock_agent_cls:
            mock_agent_instance = AsyncMock()
            mock_agent_instance.run.return_value = mock_update_result
            mock_agent_cls.return_value = mock_agent_instance

            res_feedback = await ac.post(
                f"/projects/{project_id}/brainstorm",
                json={"user_instruction": "아셀을 소심하게 바꾸고 아카데미 마법 규칙을 더 엄격하게"},
                headers=headers_owner
            )
            assert res_feedback.status_code == 200
            feedback_data = res_feedback.json()
            assert feedback_data["update_count"] == 2
            assert feedback_data["create_count"] == 0
            assert feedback_data["lores"][0]["change_type"] == "update"
            assert feedback_data["characters"][0]["change_type"] == "update"

        # 8. DB에 실제로 업데이트되었으며 중복 생성되지 않았는지 확인
        async for session in get_async_session():
            lores = (await session.execute(select(WorldSetting).where(WorldSetting.project_id == project_id))).scalars().all()
            chars = (await session.execute(select(Character).where(Character.project_id == project_id))).scalars().all()
            assert len(lores) == 1
            assert lores[0].keyword == "신화 속 아카데미"
            assert lores[0].description == "가려진 전설의 아카데미 - 수정됨"
            assert len(chars) == 1
            assert chars[0].name == "아셀"
            assert chars[0].importance == "deuteragonist"
            assert chars[0].description == "마나를 다룰 수 있게 된 소년"

        # 9. 기획 & 인물 검수 API 테스트 (DB에 설정/캐릭터가 있는 상태)
        res_audit = await ac.post(
            f"/projects/{project_id}/brainstorm/audit",
            json={},
            headers=headers_owner
        )
        assert res_audit.status_code == 200
        audit_data = res_audit.json()
        assert "is_passed" in audit_data
        assert "score" in audit_data
        assert "summary" in audit_data
        assert "character_issues" in audit_data
        assert "lore_issues" in audit_data
        assert "contradictions" in audit_data
        assert "suggestions" in audit_data
        assert audit_data["is_passed"] is True
        assert audit_data["score"] == 92

        # 타인 검수 차단
        res_audit_stranger = await ac.post(
            f"/projects/{project_id}/brainstorm/audit",
            json={},
            headers=headers_stranger
        )
        assert res_audit_stranger.status_code == 403

        # 시놉시스 없는 프로젝트 검수 차단
        res_audit_no_syn = await ac.post(
            f"/projects/{project_no_syn_id}/brainstorm/audit",
            json={},
            headers=headers_owner
        )
        assert res_audit_no_syn.status_code == 400
        assert "시놉시스" in res_audit_no_syn.json()["detail"]

        # 설정/캐릭터 모두 없는 프로젝트 검수 차단
        empty_proj = await ac.post(
            "/projects",
            json={
                "title": "빈 기획 소설",
                "synopsis": "시놉시스만 있는 작품",
                "api_key_override": "dummy-key"
            },
            headers=headers_owner
        )
        empty_id = empty_proj.json()["id"]
        res_audit_empty = await ac.post(
            f"/projects/{empty_id}/brainstorm/audit",
            json={},
            headers=headers_owner
        )
        assert res_audit_empty.status_code == 400
        assert "세계관 설정 또는 캐릭터" in res_audit_empty.json()["detail"]

        # 10. 데이터베이스 클린업
        async for session in get_async_session():
            # 프로젝트 삭제 (종속 항목 캐스케이드 삭제됨)
            for pid in [project_id, project_no_syn_id, empty_id]:
                stmt_project = select(Project).where(Project.id == pid)
                db_project = (await session.execute(stmt_project)).scalar_one_or_none()
                if db_project:
                    await session.delete(db_project)
                
            statement_users = select(User).where(User.username.in_([owner_username, stranger_username]))
            db_users = (await session.execute(statement_users)).scalars().all()
            for u in db_users:
                await session.delete(u)
            await session.commit()
