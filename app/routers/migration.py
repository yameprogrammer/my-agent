from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlmodel.ext.asyncio.session import AsyncSession
import json

from app.core.database import get_async_session
from app.core.dependencies import get_current_user
from app.core.crypto import EncryptionNotConfiguredError
from app.models import User, Project
from app.schemas.migration import ProjectExportSchema
from app.services.migration import export_project_data, import_project_data

router = APIRouter(prefix="/migration", tags=["Migration"])

@router.get("/export/{project_id}", response_model=ProjectExportSchema)
async def export_project(
    project_id: int,
    include_secrets: bool = Query(
        False,
        description=(
            "true 이면 복호화된 API 키를 JSON 에 포함합니다. "
            "기본 false — 키는 제외되어 백업 파일 유출 시 키 노출을 막습니다."
        ),
    ),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    지정한 프로젝트의 데이터를 JSON 으로 내보냅니다 (본인 소유만).
    기본적으로 LLM API 키는 포함하지 않습니다.
    """
    project = await session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to export this project")
        
    return await export_project_data(
        project_id, session, include_secrets=include_secrets
    )

@router.post("/import", status_code=status.HTTP_201_CREATED)
async def import_project(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    JSON 형식의 프로젝트 백업 파일을 업로드하여 현재 사용자 계정으로 가져오기(복원)합니다.
    """
    try:
        content = await file.read()
        json_data = json.loads(content)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file format")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read file: {str(e)}")

    try:
        schema = ProjectExportSchema(**json_data)
    except Exception as ve:
        raise HTTPException(status_code=422, detail=f"Schema validation error: {str(ve)}")

    try:
        # 단일 트랜잭션 관리
        new_project = await import_project_data(current_user.id, schema, session)
        await session.commit()
        await session.refresh(new_project)
        
        return {
            "status": "success",
            "message": "Project imported successfully",
            "new_project_id": new_project.id,
            "title": new_project.title
        }
    except EncryptionNotConfiguredError as e:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"Database import failed: {str(e)}")
