from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class ContentBase(BaseModel):
    parent_id: Optional[int] = Field(default=None, description="부모 버전 Content ID (첫 버전일 경우 None)")
    version_tag: str = Field(..., min_length=1, max_length=50, description="버전 태그 (예: v1.0, v1.1-feedback)")
    text: str = Field(..., description="소설 본문 내용")
    author_type: str = Field(default="user", description="작성 주체 (user | ai)")

class ContentCreate(ContentBase):
    pass

class ContentResponse(BaseModel):
    id: int
    episode_id: int
    parent_id: Optional[int] = None
    version_tag: str
    text: str  # API 노출명은 직관적인 text로 노출
    author_type: str
    is_approved: bool
    created_at: datetime

    @classmethod
    def from_orm_model(cls, content):
        """
        DB 모델(Content)의 content_text를 Pydantic의 text 필드로 맵핑하여 반환
        """
        return cls(
            id=content.id,
            episode_id=content.episode_id,
            parent_id=content.parent_id,
            version_tag=content.version_tag,
            text=content.content_text,
            author_type=content.author_type,
            is_approved=content.is_approved,
            created_at=content.created_at
        )

    model_config = {
        "from_attributes": True
    }
