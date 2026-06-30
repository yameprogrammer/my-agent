from typing import List, Optional
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.language_models.chat_models import BaseChatModel

# ==========================================
# 1. Pydantic 구조화 출력 스키마 정의 (Schemas)
# ==========================================

class ScenePlan(BaseModel):
    index: int = Field(description="씬 번호 (0부터 시작)")
    title: str = Field(description="씬 제목")
    plot: str = Field(description="씬의 구체적인 전개 계획 (줄거리)")
    tension: int = Field(description="권장 긴장도 수치 (1-10)")
    pace: int = Field(description="권장 전개 속도 수치 (1-10)")

class EpisodePlan(BaseModel):
    scenes: List[ScenePlan] = Field(description="해당 회차를 구성하는 씬 계획 목록")

class JudgeResult(BaseModel):
    is_passed: bool = Field(description="검수 통과 여부 (설정 충돌이 없을 시 True, 있을 시 False)")
    critique: str = Field(description="검수 피드백 및 모순 지적 사항 (통과하지 못했을 경우 필수)")


# ==========================================
# 2. 에이전트 클래스 정의 (Agents)
# ==========================================

class PlotterAgent:
    """
    Plotter 에이전트: 작품 시놉시스와 이번 회차 정보를 바탕으로 씬 단위 상세 스토리 보드를 기획합니다.
    """
    SYSTEM_PROMPT = """당신은 베스트셀러 소설의 스토리 구조를 설계하는 전문 웹소설 PD이자 시놉시스 설계자(Plotter)입니다.
작품의 전체 시놉시스와 이번 에피소드(회차)의 정보를 바탕으로, 해당 회차를 유기적이고 짜임새 있는 씬(Scene) 단위로 나누어 상세 설계해 주세요.

[작품 전체 시놉시스]
{project_synopsis}

[이번 에피소드 정보]
- 회차 번호: {episode_number}화
- 회차 제목: {episode_title}
- 회차 대략적 개요: {episode_outline}

[세계관 및 등장인물 설정]
{lore_context}

작성 지침:
1. 에피소드를 극적 긴장과 완급 조절이 이루어지는 3~5개의 씬 단위로 세분화하십시오.
2. 각 씬마다 긴장도(Tension, 1~10)와 전개 속도(Pace, 1~10)를 설정하십시오.
3. 캐릭터들의 목표, 갈등 구조, 세계관 규칙에 위배되지 않는 개연성 있는 전개를 설계하십시오."""

    def __init__(self, model: BaseChatModel):
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.SYSTEM_PROMPT),
            ("user", "위 정보를 바탕으로 이번 회차의 씬 계획(EpisodePlan)을 상세히 설계해 주세요.")
        ])
        structured_model = model.with_structured_output(EpisodePlan)
        self.chain = prompt | structured_model
        
    async def run(
        self,
        project_synopsis: str,
        episode_number: int,
        episode_title: str,
        episode_outline: str,
        lore_context: str
    ) -> EpisodePlan:
        result = await self.chain.ainvoke({
            "project_synopsis": project_synopsis,
            "episode_number": episode_number,
            "episode_title": episode_title,
            "episode_outline": episode_outline,
            "lore_context": lore_context
        })
        return result


class WriterAgent:
    """
    Writer 에이전트: 개별 씬의 설정을 바탕으로 웹소설 본문을 직접 집필합니다. (Tension & Pace 컨트롤러 반영)
    """
    SYSTEM_PROMPT = """당신은 몰입감 있고 수려한 문체로 독자를 사로잡는 전문 웹소설 작가(Writer)입니다.
아래의 정보를 바탕으로 지정된 [현재 씬]의 본문을 집필해 주세요.

[작품 전체 시놉시스]
{project_synopsis}

[이번 에피소드 정보]
- 회차 번호: {episode_number}화
- 회차 제목: {episode_title}

[세계관 및 등장인물 설정]
{lore_context}

[이전 씬 진행 요약 및 본문]
{previous_scenes_context}

[현재 씬 설계 계획]
- 씬 번호: {scene_index}
- 씬 제목: {scene_title}
- 씬 줄거리: {scene_plot}
- 권장 긴장도(Tension): {tension_level}/10 ({tension_instruction})
- 권장 전개 속도(Pace): {pace_level}/10 ({pace_instruction})

집필 지침:
1. 이전 씬들의 전개와 유기적으로 이어지도록 문맥을 맞추십시오.
2. 권장 긴장도와 전개 속도 지침을 철저히 반영하여 서술 및 대사 분량을 조절하십시오.
3. 3인칭 제한적 작가 시점 또는 주인공 시점으로 독자가 캐릭터의 감정에 몰입할 수 있도록 묘사하십시오.
4. 완성본의 씬 텍스트만 출력하세요. 부연 설명이나 메타 텍스트는 포함하지 마십시오."""

    def __init__(self, model: BaseChatModel):
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.SYSTEM_PROMPT),
            ("user", "지침을 반영하여 지정된 [현재 씬]의 소설 본문만을 작성해 주세요.")
        ])
        self.chain = prompt | model

    @staticmethod
    def get_tension_instruction(level: int) -> str:
        if level <= 3:
            return "여유롭고 서정적인 묘사 위주로 작성하며, 인물의 심리적 안정감을 강조하세요."
        elif level <= 7:
            return "일상적인 긴장감을 유지하며 대화와 행동을 균형 있게 배치하세요."
        else:
            return "문장을 단문 위주로 호흡을 짧게 가져가고, 극적인 갈등이나 위험 요소를 즉각 부각하여 극단적인 긴장감을 유도하세요."

    @staticmethod
    def get_pace_instruction(level: int) -> str:
        if level <= 3:
            return "배경 묘사와 세부 묘사를 장황하고 풍부하게 작성하세요."
        elif level <= 7:
            return "대화와 행동 묘사의 밸런스를 맞추어 표준적인 속도로 전개하세요."
        else:
            return "부가적인 환경 묘사는 최소화하고, 인물의 핵심 행동과 사건 중심의 빠른 이야기 전개에 집중하세요."

    async def run(
        self,
        project_synopsis: str,
        episode_number: int,
        episode_title: str,
        lore_context: str,
        previous_scenes_context: str,
        scene_index: int,
        scene_title: str,
        scene_plot: str,
        tension_level: int,
        pace_level: int
    ) -> str:
        tension_instruction = self.get_tension_instruction(tension_level)
        pace_instruction = self.get_pace_instruction(pace_level)
        
        result = await self.chain.ainvoke({
            "project_synopsis": project_synopsis,
            "episode_number": episode_number,
            "episode_title": episode_title,
            "lore_context": lore_context,
            "previous_scenes_context": previous_scenes_context,
            "scene_index": scene_index,
            "scene_title": scene_title,
            "scene_plot": scene_plot,
            "tension_level": tension_level,
            "tension_instruction": tension_instruction,
            "pace_level": pace_level,
            "pace_instruction": pace_instruction
        })
        
        return result.content if hasattr(result, "content") else str(result)


class JudgeAgent:
    """
    Judge 에이전트 (Consistency Guard): 작성된 초안을 세계관 및 캐릭터 설정과 비교 검수하여 설정 붕괴 및 모순을 확인합니다.
    """
    SYSTEM_PROMPT = """당신은 소설의 개연성과 설정 일관성을 정밀하게 검수하는 전문 편집자이자 설정 관리 가드(Judge)입니다.
아래의 [세계관 및 캐릭터 설정]과 [작성된 초안]을 철저히 비교하여, 모순되거나 설정이 붕괴된 지점을 찾아내십시오.

[세계관 및 캐릭터 설정]
{lore_context}

[작성된 초안]
{draft}

검수 기준:
1. 초안에 세계관 설정과 충돌하거나 모순되는 설명이 있는가? (예: 마법을 못 쓰는 캐릭터가 마법을 쓰거나, 사망한 캐릭터가 등장하는 등)
2. 등장인물의 성격, 말투, 대사 방식이 캐릭터 설정 시트와 부합하는가?
3. 이야기 흐름상 시간적, 공간적 모순이나 비약이 없는가?

검수 결과는 구조화된 포맷(is_passed: True/False, critique: 상세 피드백)으로 반환해야 합니다. 통과하지 못한 경우(is_passed=False), 수정 방향성을 구체적으로 critique에 명시해 주십시오. 설정 충돌이 없고 개연성이 완벽하다면 is_passed=True로 승인하십시오."""

    def __init__(self, model: BaseChatModel):
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.SYSTEM_PROMPT),
            ("user", "초안을 검수하고 결과를 JudgeResult 객체로 반환해 주세요.")
        ])
        structured_model = model.with_structured_output(JudgeResult)
        self.chain = prompt | structured_model

    async def run(
        self,
        lore_context: str,
        draft: str
    ) -> JudgeResult:
        result = await self.chain.ainvoke({
            "lore_context": lore_context,
            "draft": draft
        })
        return result


class EditorAgent:
    """
    Editor 에이전트: Judge 또는 사용자 피드백을 기반으로 초안 본문을 수정 보강합니다.
    """
    SYSTEM_PROMPT = """당신은 피드백을 바탕으로 소설의 초안을 다듬고 오류를 수정하는 전문 윤문 작가이자 교열가(Editor)입니다.
[작성된 초안]에서 지적된 [검수 피드백(Critique)] 및 [사용자 피드백]을 반영하여 본문을 수정 및 보강해 주세요.

[세계관 및 캐릭터 설정]
{lore_context}

[작성된 초안]
{draft}

[지적된 검수 피드백(Critique)]
{critique}

[사용자 피드백 (선택사항)]
{user_feedback}

수정 지침:
1. 지적된 모순 사항과 피드백을 철저하게 반영하되, 기존 초안의 좋은 문체와 전체적인 흐름은 최대한 유지하십시오.
2. 설정을 정상적으로 바로잡고 개연성을 보강하십시오.
3. 완성된 수정본 본문만 출력하고, 다른 설명이나 메타 텍스트는 포함하지 마십시오."""

    def __init__(self, model: BaseChatModel):
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.SYSTEM_PROMPT),
            ("user", "피드백을 모두 반영하여 보완된 완성 소설 본문만을 리턴해 주세요.")
        ])
        self.chain = prompt | model

    async def run(
        self,
        lore_context: str,
        draft: str,
        critique: str,
        user_feedback: Optional[str] = None
    ) -> str:
        result = await self.chain.ainvoke({
            "lore_context": lore_context,
            "draft": draft,
            "critique": critique,
            "user_feedback": user_feedback or "N/A"
        })
        
        return result.content if hasattr(result, "content") else str(result)
