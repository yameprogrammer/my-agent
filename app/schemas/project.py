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
    plotter_provider: Optional[str] = Field(default=None, description="Plotter LLM 제공자")
    plotter_model: Optional[str] = Field(default=None, description="Plotter LLM 모델명")
    plotter_api_key: Optional[str] = Field(default=None, description="Plotter 전용 API 키")
    
    writer_provider: Optional[str] = Field(default=None, description="Writer LLM 제공자")
    writer_model: Optional[str] = Field(default=None, description="Writer LLM 모델명")
    writer_api_key: Optional[str] = Field(default=None, description="Writer 전용 API 키")
    
    judge_provider: Optional[str] = Field(default=None, description="Judge LLM 제공자")
    judge_model: Optional[str] = Field(default=None, description="Judge LLM 모델명")
    judge_api_key: Optional[str] = Field(default=None, description="Judge 전용 API 키")
    
    editor_provider: Optional[str] = Field(default=None, description="Editor LLM 제공자")
    editor_model: Optional[str] = Field(default=None, description="Editor LLM 모델명")
    editor_api_key: Optional[str] = Field(default=None, description="Editor 전용 API 키")
    
    reviewer_provider: Optional[str] = Field(default=None, description="Reviewer LLM 제공자")
    reviewer_model: Optional[str] = Field(default=None, description="Reviewer LLM 모델명")
    reviewer_api_key: Optional[str] = Field(default=None, description="Reviewer 전용 API 키")

class ProjectUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=100, description="소설 프로젝트 제목")
    synopsis: Optional[str] = Field(default=None, description="소설 시놉시스/줄거리")
    llm_provider: Optional[str] = Field(default=None, description="소설 집필용 LLM 제공자")
    llm_model: Optional[str] = Field(default=None, description="소설 집필용 LLM 모델명")
    api_key_override: Optional[str] = Field(default=None, description="프로젝트 전용 API 키")
    
    plotter_provider: Optional[str] = Field(default=None, description="Plotter LLM 제공자")
    plotter_model: Optional[str] = Field(default=None, description="Plotter LLM 모델명")
    plotter_api_key: Optional[str] = Field(default=None, description="Plotter 전용 API 키")
    
    writer_provider: Optional[str] = Field(default=None, description="Writer LLM 제공자")
    writer_model: Optional[str] = Field(default=None, description="Writer LLM 모델명")
    writer_api_key: Optional[str] = Field(default=None, description="Writer 전용 API 키")
    
    judge_provider: Optional[str] = Field(default=None, description="Judge LLM 제공자")
    judge_model: Optional[str] = Field(default=None, description="Judge LLM 모델명")
    judge_api_key: Optional[str] = Field(default=None, description="Judge 전용 API 키")
    
    editor_provider: Optional[str] = Field(default=None, description="Editor LLM 제공자")
    editor_model: Optional[str] = Field(default=None, description="Editor LLM 모델명")
    editor_api_key: Optional[str] = Field(default=None, description="Editor 전용 API 키")
    
    reviewer_provider: Optional[str] = Field(default=None, description="Reviewer LLM 제공자")
    reviewer_model: Optional[str] = Field(default=None, description="Reviewer LLM 모델명")
    reviewer_api_key: Optional[str] = Field(default=None, description="Reviewer 전용 API 키")

class ProjectResponse(BaseModel):
    id: int
    title: str
    synopsis: Optional[str] = None
    llm_provider: str
    llm_model: str
    has_api_key: bool = False
    
    plotter_provider: Optional[str] = None
    plotter_model: Optional[str] = None
    has_plotter_api_key: bool = False
    
    writer_provider: Optional[str] = None
    writer_model: Optional[str] = None
    has_writer_api_key: bool = False
    
    judge_provider: Optional[str] = None
    judge_model: Optional[str] = None
    has_judge_api_key: bool = False
    
    editor_provider: Optional[str] = None
    editor_model: Optional[str] = None
    has_editor_api_key: bool = False
    
    reviewer_provider: Optional[str] = None
    reviewer_model: Optional[str] = None
    has_reviewer_api_key: bool = False
    
    created_at: datetime

    @classmethod
    def from_orm_model(cls, project):
        return cls(
            id=project.id,
            title=project.title,
            synopsis=project.synopsis,
            llm_provider=project.llm_provider,
            llm_model=project.llm_model,
            has_api_key=project.api_key_override is not None and project.api_key_override != "",
            
            plotter_provider=project.plotter_provider,
            plotter_model=project.plotter_model,
            has_plotter_api_key=project.plotter_api_key is not None and project.plotter_api_key != "",
            
            writer_provider=project.writer_provider,
            writer_model=project.writer_model,
            has_writer_api_key=project.writer_api_key is not None and project.writer_api_key != "",
            
            judge_provider=project.judge_provider,
            judge_model=project.judge_model,
            has_judge_api_key=project.judge_api_key is not None and project.judge_api_key != "",
            
            editor_provider=project.editor_provider,
            editor_model=project.editor_model,
            has_editor_api_key=project.editor_api_key is not None and project.editor_api_key != "",
            
            reviewer_provider=project.reviewer_provider,
            reviewer_model=project.reviewer_model,
            has_reviewer_api_key=project.reviewer_api_key is not None and project.reviewer_api_key != "",
            
            created_at=project.created_at
        )

    model_config = {
        "from_attributes": True
    }


# ── Brainstorm DTO ──────────────────────────────────────────────
class BrainstormRequest(BaseModel):
    user_instruction: Optional[str] = None
    current_lores: Optional[list] = Field(default_factory=list)
    current_characters: Optional[list] = Field(default_factory=list)

class BrainstormApplyRequest(BaseModel):
    lores: list = Field(default_factory=list)
    characters: list = Field(default_factory=list)
