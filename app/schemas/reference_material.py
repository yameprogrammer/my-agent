from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class ReferenceMaterialCreate(BaseModel):
    title: str = Field(..., max_length=200, description="참고 자료 제목")
    content: str = Field(..., description="참고 자료 본문 내용")
    category: str = Field(default="etc", description="자료 분류 (history, science, medical, law, etc)")
    source_type: str = Field(default="web", description="출처 소스 타입 (web, academic, sns, community)")
    source_url: Optional[str] = Field(default=None, max_length=500, description="출처 URL 링크")

class ReferenceMaterialResponse(BaseModel):
    id: int
    project_id: int
    title: str
    content: str
    category: str
    source_type: str
    source_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }

class ReferenceMaterialListResponse(BaseModel):
    items: List[ReferenceMaterialResponse]
    total: int
    page: int
    size: int

class ReferenceResearchRequest(BaseModel):
    topic: str = Field(..., min_length=2, description="리서치하고자 하는 핵심 주제 및 검색어")
    category: str = Field(default="etc", description="저장될 자료 카테고리")
    target_sources: List[str] = Field(
        default=["web"],
        description="검색 대상 데이터 풀 목록 (web, academic, sns, community)"
    )
