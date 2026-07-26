from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class CharacterBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=50, description="캐릭터 이름")
    description: str = Field(..., description="캐릭터 외모, 성격, 백스토리 등 세부 묘사")
    importance: str = Field(default="minor", description="스토리 내 비중 (protagonist | deuteragonist | major | minor)")
    status_location: Optional[str] = Field(default=None, description="현재 위치")
    status_condition: Optional[str] = Field(default=None, description="상태: healthy|injured|missing|dead|unknown")
    status_notes: Optional[str] = Field(default=None, description="관계·아크 진행 메모")

class CharacterCreate(CharacterBase):
    pass

class CharacterUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=50, description="캐릭터 이름")
    description: Optional[str] = Field(default=None, description="캐릭터 세부 묘사")
    importance: Optional[str] = Field(default=None, description="스토리 내 비중")
    status_location: Optional[str] = Field(default=None)
    status_condition: Optional[str] = Field(default=None)
    status_notes: Optional[str] = Field(default=None)

class CharacterResponse(BaseModel):
    id: int
    project_id: int
    name: str
    description: str
    importance: str
    status_location: Optional[str] = None
    status_condition: Optional[str] = None
    status_notes: Optional[str] = None
    status_updated_at: Optional[datetime] = None

    model_config = {
        "from_attributes": True
    }
