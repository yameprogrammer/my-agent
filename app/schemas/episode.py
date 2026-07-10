from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class EpisodeBase(BaseModel):
    episode_number: int = Field(..., ge=1, description="회차 번호 (예: 1화의 1)")
    title: str = Field(..., min_length=1, max_length=100, description="회차 제목 (예: 새로운 시작)")
    outline: Optional[str] = Field(default=None, description="회차 개요/작가 가이드 (Plotter 입력)")

class EpisodeCreate(EpisodeBase):
    pass

class EpisodeUpdate(BaseModel):
    episode_number: Optional[int] = Field(default=None, ge=1, description="회차 번호")
    title: Optional[str] = Field(default=None, min_length=1, max_length=100, description="회차 제목")
    outline: Optional[str] = Field(default=None, description="회차 개요/작가 가이드")

class EpisodeResponse(BaseModel):
    id: int
    project_id: int
    episode_number: int
    title: str
    outline: Optional[str] = None
    created_at: datetime

    model_config = {
        "from_attributes": True
    }
