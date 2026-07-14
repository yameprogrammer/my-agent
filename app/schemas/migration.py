from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class ContentExportSchema(BaseModel):
    old_id: int
    old_parent_id: Optional[int] = None
    content_text: str
    author_type: str
    version_tag: str
    is_approved: bool
    created_at: datetime

class EpisodeExportSchema(BaseModel):
    old_id: int
    episode_number: int
    title: str
    outline: Optional[str] = None
    created_at: datetime
    contents: List[ContentExportSchema]

class CharacterExportSchema(BaseModel):
    name: str
    description: str
    importance: str

class WorldSettingExportSchema(BaseModel):
    keyword: str
    category: str
    description: str
    embedding: Optional[List[float]] = None

class ProjectExportSchema(BaseModel):
    title: str
    synopsis: Optional[str] = None
    llm_provider: str
    llm_model: str
    api_key_override: Optional[str] = None
    
    # plotter override
    plotter_provider: Optional[str] = None
    plotter_model: Optional[str] = None
    plotter_api_key: Optional[str] = None
    
    # writer override
    writer_provider: Optional[str] = None
    writer_model: Optional[str] = None
    writer_api_key: Optional[str] = None
    
    # judge override
    judge_provider: Optional[str] = None
    judge_model: Optional[str] = None
    judge_api_key: Optional[str] = None
    
    # editor override
    editor_provider: Optional[str] = None
    editor_model: Optional[str] = None
    editor_api_key: Optional[str] = None
    
    # reviewer override
    reviewer_provider: Optional[str] = None
    reviewer_model: Optional[str] = None
    reviewer_api_key: Optional[str] = None
    
    world_settings: List[WorldSettingExportSchema]
    characters: List[CharacterExportSchema]
    episodes: List[EpisodeExportSchema]
