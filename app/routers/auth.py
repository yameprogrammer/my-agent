from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from app.core.database import get_async_session
from app.core.security import hash_password, verify_password, create_access_token
from app.models import User
from app.schemas.auth import UserRegister, UserResponse, Token

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_in: UserRegister,
    session: AsyncSession = Depends(get_async_session)
):
    """
    신규 사용자 회원가입 API
    """
    # 1. username 중복 체크
    statement = select(User).where(User.username == user_in.username)
    result = await session.execute(statement)
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
        
    # 2. email 중복 체크 (이메일이 제공된 경우에만)
    if user_in.email:
        statement_email = select(User).where(User.email == user_in.email)
        result_email = await session.execute(statement_email)
        existing_email = result_email.scalar_one_or_none()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
            
    # 3. 신규 유저 데이터베이스 적재
    db_user = User(
        username=user_in.username,
        hashed_password=hash_password(user_in.password),
        email=user_in.email
    )
    session.add(db_user)
    await session.commit()
    await session.refresh(db_user)
    return db_user

@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_async_session)
):
    """
    OAuth2 Password Flow 호환 로그인 및 JWT 발급 API
    """
    # 1. 사용자 조회
    statement = select(User).where(User.username == form_data.username)
    result = await session.execute(statement)
    user = result.scalar_one_or_none()
    
    # 2. 패스워드 대조 검증
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    # 3. JWT 발급
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}
