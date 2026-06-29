from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="사용자명 (3~50자)")
    password: str = Field(..., min_length=6, description="비밀번호 (6자 이상)")
    email: Optional[EmailStr] = Field(default=None, description="이메일 주소")

class UserResponse(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    created_at: datetime

    # Pydantic v2 ORM 매핑 설정
    model_config = {
        "from_attributes": True
    }

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
