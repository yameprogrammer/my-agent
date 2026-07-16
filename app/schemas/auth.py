from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from datetime import datetime
import re
from app.core.config import settings

class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="사용자명 (3~50자)")
    password: str = Field(..., min_length=6, description="비밀번호 (6자 이상, 프로덕션 환경의 경우 8자 이상 및 영문/숫자/특수문자 조합)")
    email: Optional[EmailStr] = Field(default=None, description="이메일 주소")

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if settings.ENVIRONMENT == "production":
            if len(v) < 8:
                raise ValueError("프로덕션 환경의 비밀번호는 8자 이상이어야 합니다.")
            if not re.search(r"[A-Za-z]", v):
                raise ValueError("프로덕션 환경의 비밀번호는 영문자를 최소 1개 이상 포함해야 합니다.")
            if not re.search(r"\d", v):
                raise ValueError("프로덕션 환경의 비밀번호는 숫자를 최소 1개 이상 포함해야 합니다.")
            if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
                raise ValueError("프로덕션 환경의 비밀번호는 특수문자를 최소 1개 이상 포함해야 합니다.")
        else:
            if len(v) < 6:
                raise ValueError("비밀번호는 6자 이상이어야 합니다.")
        return v


class UserResponse(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    is_active: bool
    is_admin: bool
    created_at: datetime

    # Pydantic v2 ORM 매핑 설정
    model_config = {
        "from_attributes": True
    }

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
