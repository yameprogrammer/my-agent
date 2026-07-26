"""IDEA-19 템플릿 프로젝트 + IDEA-18 공유는 share 라우터."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_async_session
from app.core.dependencies import get_current_user
from app.models import User, Project, Character, WorldSetting, Episode
from app.schemas.project import ProjectResponse
from app.services.templates import list_template_ids, get_template

router = APIRouter(tags=["Templates"])


class FromTemplateRequest(BaseModel):
    template_id: str = Field(..., description="fantasy | romance | modern_action")
    title: Optional[str] = None


@router.get("/project-templates")
async def get_project_templates(current_user: User = Depends(get_current_user)):
    return {"templates": list_template_ids()}


@router.post("/projects/from-template", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project_from_template(
    body: FromTemplateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    try:
        tpl = get_template(body.template_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Unknown template: {body.template_id}")

    project = Project(
        user_id=current_user.id,
        title=(body.title or tpl["title"]).strip(),
        synopsis=tpl.get("synopsis"),
        llm_provider="openai",
        llm_model="gpt-4o-mini",
    )
    session.add(project)
    await session.flush()

    for c in tpl.get("characters") or []:
        session.add(Character(
            project_id=project.id,
            name=c["name"],
            description=c["description"],
            importance=c.get("importance", "minor"),
        ))
    for lore in tpl.get("lores") or []:
        session.add(WorldSetting(
            project_id=project.id,
            keyword=lore["keyword"],
            category=lore.get("category", "concept"),
            description=lore["description"],
        ))
    for ep in tpl.get("episodes") or []:
        session.add(Episode(
            project_id=project.id,
            episode_number=ep["episode_number"],
            title=ep["title"],
            outline=ep.get("outline"),
        ))
    await session.commit()
    await session.refresh(project)
    return ProjectResponse.from_orm_model(project)
