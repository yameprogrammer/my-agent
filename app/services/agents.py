from typing import List, Optional
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.language_models.chat_models import BaseChatModel

OLLAMA_JSON_SCHEMAS = {
    "EpisodePlan": """
[반드시 다음 JSON 형식에 정확히 맞추어 응답하십시오. 다른 키나 설명 텍스트는 사용할 수 없으며 오직 JSON만 반환해야 합니다]
{{
  "scenes": [
    {{
      "index": 0,
      "title": "씬 제목",
      "plot": "씬의 구체적인 전개 계획 (줄거리)",
      "tension": 5, // 권장 긴장도 수치 (1-10)
      "pace": 5 // 권장 전개 속도 수치 (1-10)
    }}
  ]
}}""",
    "JudgeResult": """
[반드시 다음 JSON 형식에 정확히 맞추어 응답하십시오. 다른 키나 설명 텍스트는 사용할 수 없으며 오직 JSON만 반환해야 합니다]
{{
  "is_passed": true, // 설정 검수 통과 여부 (true/false)
  "critique": "통과하지 못했을 경우의 상세 피드백. 통과한 경우 빈 문자열 또는 통과 사유."
}}""",
    "ReviewReport": """
[반드시 다음 JSON 형식에 정확히 맞추어 응답하십시오. 다른 키나 설명 텍스트는 사용할 수 없으며 오직 JSON만 반환해야 합니다]
{{
  "score": 90, // 종합 평점 (1-100점)
  "readability": 8, // 가독성 및 문장 흐름 분석 점수 (1-10)
  "tension": 7, // 긴장감 및 완급 전개 속도 점수 (1-10)
  "strengths": ["본 작품에서 가장 몰입도 높고 잘 작성된 강점 요소 리스트 (3가지 내외)"],
  "weaknesses": ["설정 불일치, 흐름 비약 등 개선이 필요한 보완점 리스트 (인용 구문 명시 필수)"],
  "suggestions": ["수정 및 조율 가이드라인 (인용 부분을 어떻게 바꿀지 예시 문구 제시 필수)"],
  "summary": "전체 드래프트에 대한 에디터 관점의 종합 리뷰 의견"
}}""",
    "BrainstormResult": """
[반드시 다음 JSON 형식에 정확히 맞추어 응답하십시오. 다른 키나 설명 텍스트는 사용할 수 없으며 오직 JSON만 반환해야 합니다]
[중요: lores의 모든 항목은 반드시 'keyword', 'category', 'description' 3가지 키를 전부 포함해야 하며, characters의 모든 항목은 반드시 'name', 'importance', 'description' 3가지 키를 전부 포함해야 합니다. 임의로 키를 누락시키지 마십시오]
{{
  "lores": [
    {{
      "keyword": "세계관 키워드 (예: 오르비스 제국, 마나 크리스탈)",
      "category": "lore", // 반드시 'lore', 'location', 'item' 중 하나여야 함
      "description": "세계관 설정에 대한 구체적인 설명 (2~4문장)"
    }}
  ],
  "characters": [
    {{
      "name": "캐릭터 이름",
      "importance": "major", // 반드시 'protagonist', 'deuteragonist', 'major', 'minor' 중 하나여야 함
      "description": "외양, 성격, 배경, 동기 등 상세 묘사 (3~5문장)"
    }}
  ]
}}"""
}

def create_agent_chain(model: BaseChatModel, system_prompt: str, user_prompt: str, schema, schema_key: str):
    """
    Ollama 등 로컬 모델의 경우 JSON 포맷 템플릿을 프롬프트에 동적 삽입하고
    json_mode로 바인딩하여 안정적으로 구조화 답변을 받아내는 체인 생성 헬퍼 함수.
    """
    model_type = type(model).__name__
    if "Ollama" in model_type and schema_key in OLLAMA_JSON_SCHEMAS:
        final_system = system_prompt + "\n\n" + OLLAMA_JSON_SCHEMAS[schema_key]
        prompt = ChatPromptTemplate.from_messages([
            ("system", final_system),
            ("human", user_prompt)
        ])
        structured_model = model.with_structured_output(schema, method="json_mode")
    else:
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", user_prompt)
        ])
        structured_model = model.with_structured_output(schema)
    
    return prompt | structured_model

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
3. 캐릭터들의 목표, 갈등 구조, 세계관 규칙에 위배되지 않는 개연성 있는 전개를 설계하십시오.

중요: 출력은 어떠한 인사말이나 부연 설명 없이, 오직 아래의 JSON 형식을 엄격하게 준수하여 반환하십시오. 다른 키를 추가하거나 구조를 임의로 변경하면 안 됩니다.
```json
{{
  "scenes": [
    {{
      "index": 0,
      "title": "씬 제목",
      "plot": "씬의 구체적인 전개 계획 (줄거리)",
      "tension": 5,
      "pace": 5
    }}
  ]
}}
```"""

    def __init__(self, model: BaseChatModel):
        self.chain = create_agent_chain(
            model=model,
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt="위 정보를 바탕으로 이번 회차의 씬 계획(EpisodePlan)을 상세히 설계해 주세요.",
            schema=EpisodePlan,
            schema_key="EpisodePlan"
        )
        
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
        pace_level: int,
        on_chunk = None
    ) -> str:
        tension_instruction = self.get_tension_instruction(tension_level)
        pace_instruction = self.get_pace_instruction(pace_level)
        
        input_data = {
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
        }
        
        if on_chunk:
            full_text = ""
            async for chunk in self.chain.astream(input_data):
                content = chunk.content if hasattr(chunk, "content") else str(chunk)
                full_text += content
                await on_chunk(content)
            return full_text
        else:
            result = await self.chain.ainvoke(input_data)
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

검수 결과는 구조화된 포맷(is_passed: True/False, critique: 상세 피드백)으로 반환해야 합니다. 통과하지 못한 경우(is_passed=False), 수정 방향성을 구체적으로 critique에 명시해 주십시오. 설정 충돌이 없고 개연성이 완벽하다면 is_passed=True로 승인하십시오.

중요: 출력은 어떠한 인사말이나 부연 설명 없이, 오직 아래의 JSON 형식을 엄격하게 준수하여 반환하십시오. 다른 키를 추가하거나 구조를 임의로 변경하면 안 됩니다.
```json
{{
  "is_passed": true,
  "critique": "통과하지 못했을 경우의 상세 피드백. 통과한 경우 빈 문자열 또는 통과 사유."
}}
```"""

    def __init__(self, model: BaseChatModel):
        self.chain = create_agent_chain(
            model=model,
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt="초안을 검수하고 결과를 JudgeResult 객체로 반환해 주세요.",
            schema=JudgeResult,
            schema_key="JudgeResult"
        )

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
        user_feedback: Optional[str] = None,
        on_chunk = None
    ) -> str:
        input_data = {
            "lore_context": lore_context,
            "draft": draft,
            "critique": critique,
            "user_feedback": user_feedback or "N/A"
        }
        
        if on_chunk:
            full_text = ""
            async for chunk in self.chain.astream(input_data):
                content = chunk.content if hasattr(chunk, "content") else str(chunk)
                full_text += content
                await on_chunk(content)
            return full_text
        else:
            result = await self.chain.ainvoke(input_data)
            return result.content if hasattr(result, "content") else str(result)


class ReviewReport(BaseModel):
    score: int = Field(description="종합 평점 (1-100점)")
    readability: int = Field(description="가독성 및 문장 흐름 분석 점수 (1-10)")
    tension: int = Field(description="긴장감 및 완급 전개 속도 점수 (1-10)")
    strengths: List[str] = Field(description="본 작품에서 가장 몰입도 높고 잘 작성된 강점 요소 리스트 (3가지 내외)")
    weaknesses: List[str] = Field(description="설정 불일치, 흐름 비약 등 개선이 필요한 보완점 리스트 (반드시 본문의 특정 대사나 문장, 장면을 직접 인용하여 구체적인 근거를 명시해야 함)")
    suggestions: List[str] = Field(description="작가가 피드백 입력 시 바로 참고할 수 있는 수정 및 조율 가이드라인 (인용 부분을 어떻게 바꿀지 예시 문구 제시 필수)")
    summary: str = Field(description="전체 드래프트에 대한 에디터 관점의 종합 리뷰 의견")


class ReviewerAgent:
    """
    Reviewer 에이전트: 완성된 에피소드 전체 드래프트를 문학적, 설정적 관점에서 종합 평가합니다.
    """
    SYSTEM_PROMPT = """당신은 완성된 웹소설 1개 회차의 드래프트를 분석하여 문학적 완성도, 독자 몰입도, 문체 완성도를 정량적으로 평가하고 
구체적 보완 지시서를 생성하는 전문 소설 기획 편집자(Reviewer)입니다.

제시된 [전체 소설 시놉시스]와 [세계관/캐릭터 설정]을 바탕으로, 완성된 [에피소드 드래프트 전체 본문]을 꼼꼼하게 검수하십시오.

[전체 소설 시놉시스]
{project_synopsis}

[세계관 및 캐릭터 설정]
{lore_context}

[에피소드 드래프트 전체 본문]
{draft}

검수 분석 기준 및 지침 (중요):
1. 문장 가독성 및 가독 흐름이 자연스러운가?
2. 회차 전체의 긴장도(Tension) 완급조절이 성공적으로 달성되었는가?
3. 캐릭터 고유의 말투와 세계관 속성들이 흐름 내에서 개연성 있게 묘사되었는가?
4. 독자 입장에서 흥미 유발 및 클리프행어 연출이 양호한가?

★ 환각(Hallucination) 방지 지침 (필수):
- weaknesses(보완점) 및 suggestions(개선 제안)를 작성할 때는, 절대 본문에 존재하지 않는 가상의 사실이나 설정 오류를 임의로 지어내어 지적해서는 안 됩니다.
- 반드시 [에피소드 드래프트 전체 본문]에 실제로 등장하는 구체적인 대사, 단어, 혹은 특정 문장(장면)을 직접 인용(Citation)하여 지적의 명확한 근거를 최소 1개 이상 명시하십시오.
- suggestions 작성 시에는, 인용한 부분을 작가가 어떻게 고치면 좋을지 구체적인 대체 대사나 교정 문구 예시를 작성해 주십시오.

중요: 인사말이나 메타 설명 없이 오직 규정된 JSON 포맷(ReviewReport 구조)에 맞춰 출력하십시오."""

    def __init__(self, model: BaseChatModel):
        self.chain = create_agent_chain(
            model=model,
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt="드래프트 분석을 정밀 실행한 뒤 결과를 ReviewReport 스키마에 맞추어 반환해 주세요.",
            schema=ReviewReport,
            schema_key="ReviewReport"
        )

    async def run(self, project_synopsis: str, lore_context: str, draft: str) -> ReviewReport:
        return await self.chain.ainvoke({
            "project_synopsis": project_synopsis,
            "lore_context": lore_context,
            "draft": draft
        })


# ── Brainstorm 출력 스키마 ──────────────────────────────────────
class LoreSuggestion(BaseModel):
    keyword: str = Field(description="세계관 키워드 (예: 오르비스 제국, 마나 크리스탈)")
    category: str = Field(description="카테고리: 'lore', 'location', 'item' 중 하나")
    description: str = Field(description="세계관 설정에 대한 구체적인 설명 (2~4문장)")

class CharacterSuggestion(BaseModel):
    name: str = Field(description="캐릭터 이름")
    importance: str = Field(description="중요도: 'protagonist', 'deuteragonist', 'major', 'minor' 중 하나")
    description: str = Field(description="외양, 성격, 배경, 동기 등 상세 묘사 (3~5문장)")

class BrainstormResult(BaseModel):
    lores: List[LoreSuggestion] = Field(description="추천 세계관 설정 목록 (3~5개)")
    characters: List[CharacterSuggestion] = Field(description="추천 캐릭터 목록 (3~4명)")


class BrainstormAgent:
    """프로젝트 시놉시스 기반 세계관 & 캐릭터 공동 기획 에이전트."""

    SYSTEM_PROMPT = """당신은 베스트셀러 웹소설과 판타지 소설을 기획하는 전문 스토리 아키텍트입니다.
사용자가 제공하는 소설 프로젝트의 제목과 시놉시스를 깊이 분석하여, 그 세계관을 풍성하게 만들 매력적인 설정과 캐릭터를 추천 및 기획합니다.

[작동 규칙]
1. 시놉시스와 자연스럽게 연결되며 작품의 깊이를 더해줄 세계관 설정(Lorebook) 3~5개와 개성 넘치는 캐릭터 3~4명을 기획하세요.
2. 만약 기존 기획안과 사용자 피드백이 주어진다면, 피드백을 충실히 반영하여 기존 기획안을 수정·개선·확장하세요.
3. 세계관 카테고리는 반드시 'lore'(역사/법칙), 'location'(지리/공간), 'item'(아이템/마법 도구) 중 하나만 사용하세요.
4. 캐릭터 중요도는 반드시 'protagonist', 'deuteragonist', 'major', 'minor' 중 하나만 사용하세요.
5. 모든 설명은 소설 집필 시 바로 활용될 수 있을 만큼 구체적이고 매력적으로 작성하세요.
6. 기존 세계관/캐릭터가 있을 경우 서로 모순이 없도록 통합적으로 설계하세요."""

    def __init__(self, model: BaseChatModel):
        self.chain = create_agent_chain(
            model=model,
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=(
                "[소설 기본 정보]\n"
                "- 제목: {title}\n"
                "- 시놉시스: {synopsis}\n\n"
                "[이전 기획안 (있을 경우)]\n"
                "- 기존 세계관:\n{existing_lores}\n"
                "- 기존 캐릭터:\n{existing_characters}\n\n"
                "[사용자 피드백 / 추가 요청]\n"
                "{instruction}\n\n"
                "위 정보를 종합하여, 매력적인 세계관 설정과 등장인물 시트를 작성해 주세요."
            ),
            schema=BrainstormResult,
            schema_key="BrainstormResult"
        )

    async def run(
        self,
        project_title: str,
        project_synopsis: str,
        user_instruction: Optional[str] = None,
        current_lores: Optional[List[dict]] = None,
        current_characters: Optional[List[dict]] = None,
    ) -> BrainstormResult:
        # 기존 기획안을 사람이 읽기 쉬운 문자열로 직렬화
        lores_str = "(없음)"
        if current_lores:
            lores_str = "\n".join(
                f"  - [{l['category']}] {l['keyword']}: {l['description']}"
                for l in current_lores
            )

        chars_str = "(없음)"
        if current_characters:
            chars_str = "\n".join(
                f"  - {c['name']} ({c['importance']}): {c['description']}"
                for c in current_characters
            )

        instruction_str = user_instruction or "시놉시스를 분석하여 기본 세계관과 캐릭터를 자유롭게 창작해 주세요."

        result = await self.chain.ainvoke({
            "title": project_title,
            "synopsis": project_synopsis,
            "existing_lores": lores_str,
            "existing_characters": chars_str,
            "instruction": instruction_str,
        })
        return result
