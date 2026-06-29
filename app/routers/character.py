from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from typing import List
from app.core.database import get_async_session
from app.core.dependencies import get_current_user, check_project_owner
from app.models import Character, User
from app.schemas.character import CharacterCreate, CharacterUpdate, CharacterResponse

router = APIRouter(prefix="/projects/{project_id}/characters", tags=["Characters"])

@router.post("", response_model=CharacterResponse, status_code=status.HTTP_201_CREATED)
async def create_character(
    project_id: int,
    character_in: CharacterCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    특정 소설 프로젝트 내에 신규 캐릭터 시트 생성 API (소유권 검증 포함)
    """
    await check_project_owner(project_id, current_user, session)
    
    db_character = Character(
        project_id=project_id,
        name=character_in.name,
        description=character_in.description,
        importance=character_in.importance
    )
    session.add(db_character)
    await session.commit()
    await session.refresh(db_character)
    return db_character

@router.get("", response_model=List[CharacterResponse])
async def list_characters(
    project_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    특정 소설 프로젝트의 캐릭터 시트 목록 전체 조회 API (소유권 검증 포함)
    """
    await check_project_owner(project_id, current_user, session)
    
    statement = select(Character).where(Character.project_id == project_id)
    result = await session.execute(statement)
    characters = result.scalars().all()
    return characters

@router.get("/{character_id}", response_model=CharacterResponse)
async def get_character(
    project_id: int,
    character_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    단일 캐릭터 시트 상세 조회 API (소유권 검증 포함)
    """
    await check_project_owner(project_id, current_user, session)
    
    statement = select(Character).where(Character.id == character_id, Character.project_id == project_id)
    result = await session.execute(statement)
    character = result.scalar_one_or_none()
    
    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found"
        )
    return character

@router.put("/{character_id}", response_model=CharacterResponse)
async def update_character(
    project_id: int,
    character_id: int,
    character_in: CharacterUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    캐릭터 시트 수정 API (소유권 검증 포함)
    """
    await check_project_owner(project_id, current_user, session)
    
    statement = select(Character).where(Character.id == character_id, Character.project_id == project_id)
    result = await session.execute(statement)
    character = result.scalar_one_or_none()
    
    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found"
        )
        
    update_data = character_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(character, key, value)
        
    session.add(character)
    await session.commit()
    await session.refresh(character)
    return character

@router.delete("/{character_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_character(
    project_id: int,
    character_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    캐릭터 시트 삭제 API (소유권 검증 포함)
    """
    await check_project_owner(project_id, current_user, session)
    
    statement = select(Character).where(Character.id == character_id, Character.project_id == project_id)
    result = await session.execute(statement)
    character = result.scalar_one_or_none()
    
    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found"
        )
        
    await session.delete(character)
    await session.commit()
    return None
