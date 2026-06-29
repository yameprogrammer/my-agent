from pydantic import BaseModel, Field
from typing import Optional

class CharacterBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=50, description="캐릭터 이름")
    description: str = Field(..., description="캐릭터 외모, 성격, 백스토리 등 세부 묘사")
    importance: str = Field(default="minor", description="스토리 내 비중 (protagonist | deuteragonist | major | minor)")

class CharacterCreate(CharacterBase):
    pass

class CharacterUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=50, description="캐릭터 이름")
    description: Optional[str] = Field(default=None, description="캐릭터 세부 묘사")
    importance: Optional[str] = Field(default=None, description="스토리 내 비중")

class CharacterResponse(BaseModel):
    id: int
    project_id: int
    name: str
    description: str
    importance: str

    model_config = {
        "from_attributes": True
    }
