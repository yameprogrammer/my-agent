from pydantic import BaseModel
from typing import List, Optional, Literal
from datetime import datetime

class AdminStatsResponse(BaseModel):
    total_users: int
    pending_users: int
    total_projects: int
    total_episodes: int

class UserStatusChangeRequest(BaseModel):
    action: Literal["approve", "reject", "suspend"]

class UserRoleChangeRequest(BaseModel):
    is_admin: bool

class AdminUserResponse(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    is_active: bool
    is_admin: bool
    created_at: datetime
    rejected_at: Optional[datetime] = None

class AdminUserListResponse(BaseModel):
    items: List[AdminUserResponse]
    total: int
    page: int
    size: int
