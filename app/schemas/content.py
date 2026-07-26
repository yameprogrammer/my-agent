from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal, List
from datetime import datetime

AuthorType = Literal["user", "ai", "hybrid"]


class ContentBase(BaseModel):
    parent_id: Optional[int] = Field(
        default=None,
        description="부모 버전 Content ID (첫 버전일 경우 None)",
    )
    version_tag: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="버전 태그 (예: v1.0, v1.1-human)",
    )
    text: str = Field(
        ...,
        min_length=1,
        max_length=500_000,
        description="소설 본문 내용",
    )
    author_type: AuthorType = Field(
        default="user",
        description="작성 주체: user(작가) | ai(자동 생성) | hybrid(AI 기반 작가 수정)",
    )

    @field_validator("author_type", mode="before")
    @classmethod
    def normalize_author_type(cls, v):
        if v is None or v == "":
            return "user"
        s = str(v).strip().lower()
        if s not in ("user", "ai", "hybrid"):
            raise ValueError("author_type must be one of: user, ai, hybrid")
        return s

    @field_validator("text")
    @classmethod
    def text_not_blank(cls, v: str) -> str:
        if not v or not str(v).strip():
            raise ValueError("text must not be empty")
        return v


class ContentCreate(ContentBase):
    pass


class DiffLineRow(BaseModel):
    op: str  # equal | delete | insert | replace
    left: Optional[str] = None
    right: Optional[str] = None


class ContentDiffResponse(BaseModel):
    left_id: int
    right_id: int
    left_tag: str
    right_tag: str
    rows: List[DiffLineRow]
    left_len: int
    right_len: int


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
            created_at=content.created_at,
        )

    model_config = {
        "from_attributes": True
    }


class PartialRewriteRequest(BaseModel):
    """H6: 선택 구간 + 지시 → AI 부분 재작성."""
    full_text: str = Field(..., min_length=1, max_length=500_000)
    selected_text: str = Field(..., min_length=1, max_length=100_000)
    instruction: str = Field(..., min_length=1, max_length=2000)
    parent_content_id: Optional[int] = Field(
        default=None,
        description="저장 시 parent_id 로 쓸 Content id",
    )
    save_as_version: bool = Field(
        default=False,
        description="true 이면 결과를 새 Content 버전으로 저장",
    )
    version_tag: Optional[str] = Field(default=None, max_length=50)


class PartialRewriteResponse(BaseModel):
    rewritten_span: str
    full_text: str
    content: Optional[ContentResponse] = None
