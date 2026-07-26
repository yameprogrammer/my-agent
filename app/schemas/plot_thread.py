from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class PlotThreadBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="")
    status: str = Field(default="open", description="open | planted | resolved | dropped")
    planted_episode_id: Optional[int] = None
    target_episode_id: Optional[int] = None
    resolved_episode_id: Optional[int] = None
    notes: Optional[str] = None


class PlotThreadCreate(PlotThreadBase):
    pass


class PlotThreadUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None
    status: Optional[str] = None
    planted_episode_id: Optional[int] = None
    target_episode_id: Optional[int] = None
    resolved_episode_id: Optional[int] = None
    notes: Optional[str] = None


class PlotThreadResponse(PlotThreadBase):
    id: int
    project_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
