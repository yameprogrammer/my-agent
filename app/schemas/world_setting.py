from pydantic import BaseModel, Field
from typing import Optional, List

class WorldSettingBase(BaseModel):
    keyword: str = Field(..., min_length=1, max_length=100, description="설정 키워드 (예: 아르카나 마법학교)")
    category: str = Field(..., description="설정 카테고리 (lore | location | item | concept)")
    description: str = Field(..., description="설정 세부 내용")

class WorldSettingCreate(WorldSettingBase):
    pass

class WorldSettingUpdate(BaseModel):
    keyword: Optional[str] = Field(default=None, min_length=1, max_length=100, description="설정 키워드")
    category: Optional[str] = Field(default=None, description="설정 카테고리")
    description: Optional[str] = Field(default=None, description="설정 세부 내용")

class WorldSettingResponse(BaseModel):
    id: int
    project_id: int
    keyword: str
    category: str
    description: str
    # RAG 임베딩 값(embedding)은 데이터 크기가 크므로 응답에서 제외하여 트래픽 오버헤드 방지

    model_config = {
        "from_attributes": True
    }
