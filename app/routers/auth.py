"""
인증 라우터

- POST /auth/register  : 회원가입 요청 (is_active=False로 저장 후 관리자 텔레그램 알림 발송)
- POST /auth/login     : 로그인 및 JWT 발급 (is_active=False 또는 rejected_at 설정 시 403 반환)
- GET  /auth/me        : 현재 로그인 유저 정보 조회
"""

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

from app.core.database import get_async_session
from app.core.security import hash_password, verify_password, create_access_token, BCRYPT_MAX_PASSWORD_BYTES
from app.core.dependencies import get_current_user
from app.models import User
from app.schemas.auth import UserRegister, UserResponse, Token
from app.services.telegram_service import TelegramBotService
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])


# ---------------------------------------------------------------------------
# 회원가입
# ---------------------------------------------------------------------------

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="신규 회원가입 요청",
    description="계정이 즉시 활성화되지 않고, 관리자 텔레그램 승인 후에만 로그인이 가능합니다.",
)
async def register(
    user_in: UserRegister,
    session: AsyncSession = Depends(get_async_session),
):
    """
    신규 사용자 회원가입 API.
    - is_active=False 상태로 DB에 저장
    - 관리자 텔레그램으로 승인 요청 발송
    - 거절된 이력이 있는 유저의 재가입 처리 포함
    """
    # 1. username 중복 체크
    statement = select(User).where(User.username == user_in.username)
    result = await session.execute(statement)
    existing_user = result.scalar_one_or_none()

    # 2. email 중복 체크 (이메일이 제공된 경우에만)
    # 거절된 유저가 재가입하더라도, 입력한 새 이메일이 다른 활성/대기 유저에 의해 점유되었는지 확인해야 함
    if user_in.email:
        statement_email = select(User).where(User.email == user_in.email)
        result_email = await session.execute(statement_email)
        email_owner = result_email.scalar_one_or_none()
        
        if email_owner:
            # 본인이 재가입하는 경우는 허용, 타인이 이미 사용하는 경우는 차단
            if not existing_user or existing_user.id != email_owner.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered",
                )

    try:
        hashed = hash_password(user_in.password)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e) or f"Password too long (max {BCRYPT_MAX_PASSWORD_BYTES} bytes)",
        )

    if existing_user:
        # 거절된 유저가 재가입하는 경우: 기존 레코드를 덮어쓰고 재승인 요청
        if existing_user.rejected_at:
            logger.info("거절된 유저(%s)의 재가입 요청 처리", existing_user.username)
            db_user = existing_user
            db_user.hashed_password = hashed
            db_user.email = user_in.email
            db_user.rejected_at = None  # 거절 상태 초기화
            db_user.is_active = False   # 다시 승인 대기 상태로
        else:
            # 이미 활성 상태거나 승인 대기 중인 일반 중복 가입
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered",
            )
    else:
        # 3. 신규 유저 저장 (is_active=False)
        db_user = User(
            username=user_in.username,
            hashed_password=hashed,
            email=user_in.email,
            is_active=False,
            is_admin=False,
        )

    session.add(db_user)
    await session.commit()
    await session.refresh(db_user)

    # 4. 관리자에게 텔레그램 승인 요청 발송 (Best-effort)
    if settings.TELEGRAM_BOT_TOKEN:
        try:
            telegram = TelegramBotService(
                settings.TELEGRAM_BOT_TOKEN,
                settings.ADMIN_TELEGRAM_CHAT_ID,
            )
            await telegram.send_registration_alert(db_user)
        except Exception as e:
            logger.warning("텔레그램 가입 알림 전송 실패 (가입은 정상 처리됨): %s", e)

    logger.info("신규 가입 요청 처리 완료: username=%s, id=%d", db_user.username, db_user.id)
    return db_user


# ---------------------------------------------------------------------------
# 로그인
# ---------------------------------------------------------------------------

@router.post(
    "/login",
    response_model=Token,
    summary="로그인 및 JWT 발급",
)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_async_session),
):
    """
    OAuth2 Password Flow 호환 로그인 및 JWT 발급 API.
    관리자 미승인(is_active=False) 또는 거절된 계정은 로그인이 차단됩니다.
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

    # 3. 계정 상태 확인 (거절 여부 우선 체크)
    if user.rejected_at:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="계정이 거절되었습니다. 재가입해 주세요.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is pending admin approval. Please wait for the administrator to activate your account via Telegram.",
        )

    # 4. JWT 발급
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}


# ---------------------------------------------------------------------------
# 현재 로그인 유저 조회
# ---------------------------------------------------------------------------

@router.get(
    "/me",
    response_model=UserResponse,
    summary="현재 로그인 유저 정보 조회",
)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user
