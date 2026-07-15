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

async def export_project_data(project_id: int, db: AsyncSession) -> ProjectExportSchema:
    """
    지정한 프로젝트 ID의 모든 원고, 캐릭터, 세계관 설정을 조회하여 스키마 데이터로 직렬화합니다.
    외래 키 암호화 정보는 Plaintext로 복호화하여 저장합니다.
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
                created_at=ep.created_at,
                contents=contents_schema
            )
        )

    return ProjectExportSchema(
        title=project.title,
        synopsis=project.synopsis,
        llm_provider=project.llm_provider,
        llm_model=project.llm_model,
        
        # 복호화 후 전달
        api_key_override=decrypt_api_key(project.api_key_override),
        
        plotter_provider=project.plotter_provider,
        plotter_model=project.plotter_model,
        plotter_api_key=decrypt_api_key(project.plotter_api_key),
        
        writer_provider=project.writer_provider,
        writer_model=project.writer_model,
        writer_api_key=decrypt_api_key(project.writer_api_key),
        
        judge_provider=project.judge_provider,
        judge_model=project.judge_model,
        judge_api_key=decrypt_api_key(project.judge_api_key),
        
        editor_provider=project.editor_provider,
        editor_model=project.editor_model,
        editor_api_key=decrypt_api_key(project.editor_api_key),
        
        reviewer_provider=project.reviewer_provider,
        reviewer_model=project.reviewer_model,
        reviewer_api_key=decrypt_api_key(project.reviewer_api_key),
        
        world_settings=world_settings_schema,
        characters=characters_schema,
        episodes=episodes_schema
    )

async def import_project_data(user_id: int, schema: ProjectExportSchema, db: AsyncSession) -> Project:
    """
    가져온 프로젝트 스키마 데이터를 복구합니다.
    새로운 수신 서버의 대칭키를 이용하여 API Key들을 재암호화하여 저장하며,
    순차 정렬 방식을 활용해 self-referencing parent_id 버전 트리를 완전 복원합니다.
    """
    # 1. Project 생성 및 수신 서버 대칭키 재암호화
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
    await db.flush()  # new_project.id 획득

    # 2. WorldSetting 생성
    for ws_data in schema.world_settings:
        new_ws = WorldSetting(
            project_id=new_project.id,
            keyword=ws_data.keyword,
            category=ws_data.category,
            description=ws_data.description,
            embedding=ws_data.embedding
        )
        db.add(new_ws)

    # 3. Character 생성
    for c_data in schema.characters:
        new_c = Character(
            project_id=new_project.id,
            name=c_data.name,
            description=c_data.description,
            importance=c_data.importance
        )
        db.add(new_c)

    await db.flush()

    # 4. Episode & Content 생성
    for ep_data in schema.episodes:
        new_ep = Episode(
            project_id=new_project.id,
            episode_number=ep_data.episode_number,
            title=ep_data.title,
            outline=ep_data.outline,
            created_at=ep_data.created_at
        )
        db.add(new_ep)
        await db.flush()  # new_ep.id 획득

        # Content의 버전 트리 복원
        content_id_map = {}
        # 부모가 없는 노드(루트)를 최우선 순위로 하고 생성일로 정렬해 버전 트리 복원 신뢰도를 확보
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
            await db.flush()  # new_content.id 획득
            content_id_map[c_data.old_id] = new_content.id

    await db.flush()
    return new_project
