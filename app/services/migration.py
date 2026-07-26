from typing import Optional
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import HTTPException

from app.models import Project, WorldSetting, Character, Episode, Content
from app.schemas.migration import (
    ProjectExportSchema, WorldSettingExportSchema, CharacterExportSchema,
    EpisodeExportSchema, ContentExportSchema
)
from app.core.crypto import decrypt_api_key, encrypt_api_key

# 내보내기/백업 시 기본적으로 제외하는 시크릿 필드
_SECRET_FIELD_NAMES = (
    "api_key_override",
    "plotter_api_key",
    "writer_api_key",
    "judge_api_key",
    "editor_api_key",
    "reviewer_api_key",
)


def strip_secret_fields(data: dict) -> dict:
    """dict 형태의 export 페이로드에서 API 키 필드를 제거(None)한다."""
    cleaned = dict(data)
    for name in _SECRET_FIELD_NAMES:
        cleaned[name] = None
    return cleaned


async def export_project_data(
    project_id: int,
    db: AsyncSession,
    *,
    include_secrets: bool = False,
) -> ProjectExportSchema:
    """
    지정한 프로젝트 ID의 원고·캐릭터·세계관 설정을 직렬화한다.

    include_secrets=False (기본): API 키 필드는 항상 None — 공개 유출·백업 파일 사고 방지.
    include_secrets=True: 복호화된 평문 키 포함 (의도적 이전 시에만, 파일 취급 주의).
    """
    stmt = (
        select(Project)
        .where(Project.id == project_id)
        .options(
            selectinload(Project.world_settings),
            selectinload(Project.characters),
            selectinload(Project.episodes).selectinload(Episode.contents)
        )
    )
    result = await db.execute(stmt)
    project = result.scalars().first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    world_settings_schema = [
        WorldSettingExportSchema(
            keyword=ws.keyword,
            category=ws.category,
            description=ws.description,
            embedding=ws.embedding
        )
        for ws in project.world_settings
    ]

    characters_schema = [
        CharacterExportSchema(
            name=c.name,
            description=c.description,
            importance=c.importance
        )
        for c in project.characters
    ]

    episodes_schema = []
    for ep in project.episodes:
        contents_schema = [
            ContentExportSchema(
                old_id=c.id,
                old_parent_id=c.parent_id,
                content_text=c.content_text,
                author_type=c.author_type,
                version_tag=c.version_tag,
                is_approved=c.is_approved,
                created_at=c.created_at
            )
            for c in ep.contents
        ]
        episodes_schema.append(
            EpisodeExportSchema(
                old_id=ep.id,
                episode_number=ep.episode_number,
                title=ep.title,
                outline=ep.outline,
                summary=getattr(ep, "summary", None),
                created_at=ep.created_at,
                contents=contents_schema
            )
        )

    def _key(field: Optional[str]) -> Optional[str]:
        if not include_secrets:
            return None
        return decrypt_api_key(field)

    return ProjectExportSchema(
        title=project.title,
        synopsis=project.synopsis,
        llm_provider=project.llm_provider,
        llm_model=project.llm_model,
        api_key_override=_key(project.api_key_override),
        plotter_provider=project.plotter_provider,
        plotter_model=project.plotter_model,
        plotter_api_key=_key(project.plotter_api_key),
        writer_provider=project.writer_provider,
        writer_model=project.writer_model,
        writer_api_key=_key(project.writer_api_key),
        judge_provider=project.judge_provider,
        judge_model=project.judge_model,
        judge_api_key=_key(project.judge_api_key),
        editor_provider=project.editor_provider,
        editor_model=project.editor_model,
        editor_api_key=_key(project.editor_api_key),
        reviewer_provider=project.reviewer_provider,
        reviewer_model=project.reviewer_model,
        reviewer_api_key=_key(project.reviewer_api_key),
        world_settings=world_settings_schema,
        characters=characters_schema,
        episodes=episodes_schema,
    )


async def import_project_data(user_id: int, schema: ProjectExportSchema, db: AsyncSession) -> Project:
    """
    가져온 프로젝트 스키마 데이터를 복구합니다.
    수신 서버의 대칭키로 API Key 를 재암호화하여 저장하며,
    parent_id 버전 트리를 복원합니다.
    """
    new_project = Project(
        user_id=user_id,
        title=schema.title,
        synopsis=schema.synopsis,
        llm_provider=schema.llm_provider,
        llm_model=schema.llm_model,
        api_key_override=encrypt_api_key(schema.api_key_override),
        plotter_provider=schema.plotter_provider,
        plotter_model=schema.plotter_model,
        plotter_api_key=encrypt_api_key(schema.plotter_api_key),
        writer_provider=schema.writer_provider,
        writer_model=schema.writer_model,
        writer_api_key=encrypt_api_key(schema.writer_api_key),
        judge_provider=schema.judge_provider,
        judge_model=schema.judge_model,
        judge_api_key=encrypt_api_key(schema.judge_api_key),
        editor_provider=schema.editor_provider,
        editor_model=schema.editor_model,
        editor_api_key=encrypt_api_key(schema.editor_api_key),
        reviewer_provider=schema.reviewer_provider,
        reviewer_model=schema.reviewer_model,
        reviewer_api_key=encrypt_api_key(schema.reviewer_api_key),
    )
    db.add(new_project)
    await db.flush()

    for ws_data in schema.world_settings:
        db.add(WorldSetting(
            project_id=new_project.id,
            keyword=ws_data.keyword,
            category=ws_data.category,
            description=ws_data.description,
            embedding=ws_data.embedding
        ))

    for c_data in schema.characters:
        db.add(Character(
            project_id=new_project.id,
            name=c_data.name,
            description=c_data.description,
            importance=c_data.importance
        ))

    await db.flush()

    for ep_data in schema.episodes:
        new_ep = Episode(
            project_id=new_project.id,
            episode_number=ep_data.episode_number,
            title=ep_data.title,
            outline=ep_data.outline,
            summary=getattr(ep_data, "summary", None),
            created_at=ep_data.created_at
        )
        db.add(new_ep)
        await db.flush()

        content_id_map = {}
        sorted_contents = sorted(
            ep_data.contents,
            key=lambda c: (0 if c.old_parent_id is None else 1, c.created_at)
        )
        for c_data in sorted_contents:
            new_parent_id = None
            if c_data.old_parent_id:
                new_parent_id = content_id_map.get(c_data.old_parent_id)

            new_content = Content(
                episode_id=new_ep.id,
                parent_id=new_parent_id,
                content_text=c_data.content_text,
                author_type=c_data.author_type,
                version_tag=c_data.version_tag,
                is_approved=c_data.is_approved,
                created_at=c_data.created_at
            )
            db.add(new_content)
            await db.flush()
            content_id_map[c_data.old_id] = new_content.id

    await db.flush()
    return new_project
