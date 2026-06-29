from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from app.core.database import get_async_session
from app.core.security import decode_access_token
from app.models import User, Project

# OAuth2 토큰 Bearer 스키마 연동 (로그인 엔드포인트 URL 지정)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_async_session)
) -> User:
    """
    HTTP Request의 Bearer Token을 검증하여 현재 접속한 User 인스턴스를 반환하는 공통 의존성 함수
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # 1. JWT 토큰 디코딩
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
        
    # 2. 토큰 주체(username) 추출
    username: str = payload.get("sub")
    if username is None:
        raise credentials_exception
        
    # 3. 데이터베이스에서 해당 유저 조회
    statement = select(User).where(User.username == username)
    result = await session.execute(statement)
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
        
    return user


async def check_project_owner(
    project_id: int,
    current_user: User,
    session: AsyncSession
) -> Project:
    """
    특정 프로젝트의 소유권(인가)을 검증하여 통과 시 프로젝트 인스턴스를 반환하는 공통 헬퍼 함수
    """
    statement = select(Project).where(Project.id == project_id)
    result = await session.execute(statement)
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
        
    if project.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: You do not own this project"
        )
        
    return project
