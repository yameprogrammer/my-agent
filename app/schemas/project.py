from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class ProjectBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=100, description="소설 프로젝트 제목")
    synopsis: Optional[str] = Field(default=None, description="소설 시놉시스/줄거리")
    llm_provider: str = Field(default="openai", description="소설 집필용 LLM 제공자 (openai | google | anthropic | ollama)")
    llm_model: str = Field(default="gpt-4o-mini", description="소설 집필용 LLM 모델명")

class ProjectCreate(ProjectBase):
    api_key_override: Optional[str] = Field(default=None, description="프로젝트 전용 API 키 (생략 시 전역 API 키 사용)")

class ProjectUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=100, description="소설 프로젝트 제목")
    synopsis: Optional[str] = Field(default=None, description="소설 시놉시스/줄거리")
    llm_provider: Optional[str] = Field(default=None, description="소설 집필용 LLM 제공자")
    llm_model: Optional[str] = Field(default=None, description="소설 집필용 LLM 모델명")
    api_key_override: Optional[str] = Field(default=None, description="프로젝트 전용 API 키")

class ProjectResponse(BaseModel):
    id: int
    title: str
    synopsis: Optional[str] = None
    llm_provider: str
    llm_model: str
    has_api_key: bool = False  # 보안상 API 키 원본은 리스폰스하지 않고 등록 여부만 노출
    created_at: datetime

    # SQLModel 인스턴스에서 Pydantic Response 스마로의 헬퍼 메서드
    @classmethod
    def from_orm_model(cls, project):
        return cls(
            id=project.id,
            title=project.title,
            synopsis=project.synopsis,
            llm_provider=project.llm_provider,
            llm_model=project.llm_model,
            has_api_key=project.api_key_override is not None and project.api_key_override != "",
            created_at=project.created_at
        )

    model_config = {
        "from_attributes": True
    }
