"""
인증 라우터

- POST /auth/register  : 회원가입 요청 (is_active=False로 저장 후 관리자에게 승인 이메일 발송)
- POST /auth/login     : 로그인 및 JWT 발급 (is_active=False면 403 반환)
- GET  /auth/approve/{user_id} : 관리자 승인 링크 클릭 시 계정 활성화
- GET  /auth/me        : 현재 로그인 유저 정보 조회
"""

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import HTMLResponse
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

from app.core.database import get_async_session
from app.core.security import hash_password, verify_password, create_access_token
from app.core.dependencies import get_current_user
from app.models import User
from app.schemas.auth import UserRegister, UserResponse, Token
from app.services.email_service import (
    send_registration_request_to_admin,
    send_approval_notification_to_user,
)

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
    description="계정이 즉시 활성화되지 않고, 관리자 이메일 승인 후에만 로그인이 가능합니다.",
)
async def register(
    user_in: UserRegister,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_async_session),
):
    """
    신규 사용자 회원가입 API.
    - is_active=False 상태로 DB에 저장
    - 관리자 이메일로 승인 요청 발송 (BackgroundTask로 비차단 처리)
    """
    # 1. username 중복 체크
    statement = select(User).where(User.username == user_in.username)
    result = await session.execute(statement)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )

    # 2. email 중복 체크 (이메일이 제공된 경우에만)
    if user_in.email:
        statement_email = select(User).where(User.email == user_in.email)
        result_email = await session.execute(statement_email)
        if result_email.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

    # 3. 신규 유저 저장 (is_active=False)
    db_user = User(
        username=user_in.username,
        hashed_password=hash_password(user_in.password),
        email=user_in.email,
        is_active=False,
        is_admin=False,
    )
    session.add(db_user)
    await session.commit()
    await session.refresh(db_user)

    # 4. 관리자에게 승인 요청 이메일 발송 (백그라운드 태스크 — 응답을 지연시키지 않음)
    background_tasks.add_task(
        send_registration_request_to_admin,
        username=db_user.username,
        user_email=db_user.email,
        user_id=db_user.id,
    )

    logger.info("신규 가입 요청: username=%s, id=%d", db_user.username, db_user.id)
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
    관리자 미승인(is_active=False) 계정은 로그인이 차단됩니다.
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

    # 3. 계정 활성화 여부 확인
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is pending admin approval. Please wait for the administrator to activate your account.",
        )

    # 4. JWT 발급
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}


# ---------------------------------------------------------------------------
# 관리자 승인 (이메일 링크 클릭 시 호출)
# ---------------------------------------------------------------------------

@router.get(
    "/approve/{user_id}",
    response_class=HTMLResponse,
    summary="관리자 회원 승인",
    description="관리자 이메일의 승인 링크를 클릭하면 해당 계정을 활성화합니다.",
)
async def approve_user(
    user_id: int,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_async_session),
):
    """
    관리자 이메일에 포함된 승인 링크(/auth/approve/{user_id})를 통해 호출됩니다.
    해당 계정을 is_active=True로 전환하고, 사용자에게 활성화 완료 이메일을 발송합니다.
    """
    # 1. 대상 유저 조회
    statement = select(User).where(User.id == user_id)
    result = await session.execute(statement)
    user = result.scalar_one_or_none()

    if not user:
        return HTMLResponse(
            content=_html_result_page("오류", "존재하지 않는 사용자입니다.", success=False),
            status_code=404,
        )

    # 2. 이미 활성화된 계정 처리
    if user.is_active:
        return HTMLResponse(
            content=_html_result_page(
                "이미 승인됨",
                f"'{user.username}' 계정은 이미 활성화되어 있습니다.",
                success=True,
            )
        )

    # 3. 계정 활성화
    user.is_active = True
    session.add(user)
    await session.commit()

    logger.info("계정 승인 완료: username=%s, id=%d", user.username, user.id)

    # 4. 사용자에게 승인 완료 이메일 발송 (이메일이 있는 경우에만)
    if user.email:
        background_tasks.add_task(
            send_approval_notification_to_user,
            username=user.username,
            user_email=user.email,
        )

    return HTMLResponse(
        content=_html_result_page(
            "승인 완료",
            f"'{user.username}' 계정이 성공적으로 활성화되었습니다. 이제 해당 사용자가 로그인할 수 있습니다.",
            success=True,
        )
    )


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


# ---------------------------------------------------------------------------
# 헬퍼: 승인 결과 HTML 페이지 생성
# ---------------------------------------------------------------------------

def _html_result_page(title: str, message: str, success: bool = True) -> str:
    color = "#667eea" if success else "#ef4444"
    icon = "✅" if success else "❌"
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} — AI 소설 작가 시스템</title>
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
      font-family: 'Apple SD Gothic Neo', 'Noto Sans KR', sans-serif;
      background: #f4f6f8;
      display: flex; align-items: center; justify-content: center;
      min-height: 100vh;
    }}
    .card {{
      background: #ffffff;
      border-radius: 16px;
      box-shadow: 0 8px 32px rgba(0,0,0,0.10);
      padding: 56px 48px;
      max-width: 480px;
      width: 90%;
      text-align: center;
    }}
    .icon {{ font-size: 56px; margin-bottom: 24px; }}
    h1 {{ font-size: 24px; color: #111827; font-weight: 700; margin-bottom: 16px; }}
    p {{ font-size: 15px; color: #6b7280; line-height: 1.7; }}
    .badge {{
      display: inline-block;
      background: {color};
      color: #fff;
      font-size: 12px;
      font-weight: 600;
      padding: 4px 12px;
      border-radius: 99px;
      margin-bottom: 20px;
      letter-spacing: 0.5px;
    }}
  </style>
</head>
<body>
  <div class="card">
    <div class="icon">{icon}</div>
    <div class="badge">AI 소설 작가 시스템</div>
    <h1>{title}</h1>
    <p>{message}</p>
  </div>
</body>
</html>"""
