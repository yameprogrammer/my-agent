import logging
from typing import List, Dict, Any, Optional
import json
from datetime import datetime
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_async_session
from app.core.config import settings
from app.models import Project, ReferenceMaterial
from app.core.crypto import decrypt_api_key

logger = logging.getLogger(__name__)

# Tavily Client Import Guard
try:
    from tavily import TavilyClient
except ImportError:
    TavilyClient = None

async def query_llm_internal(
    provider: str,
    model: str,
    api_key: Optional[str],
    prompt: str,
    system_prompt: Optional[str] = None
) -> str:
    """
    프로젝트에 지정된 LLM 설정을 기반으로 동적 LLM 호출을 수행합니다.
    테스트 모드이거나 실 API 키가 설정되지 않은 경우 모의 텍스트 응답을 발송합니다.
    """
    import os
    import re
    is_test_or_dev = os.getenv("TESTING") == "True" or not (api_key or settings.OPENAI_API_KEY or settings.GOOGLE_API_KEY or settings.ANTHROPIC_API_KEY)

    if is_test_or_dev:
        # 프롬프트 내용에서 주제(topic) 및 카테고리(category) 동적 추출
        topic_match = re.search(
            r'주제:\s*"([^"]+)"|키워드:\s*"([^"]+)"|주제:\s*([^\n]+)|키워드:\s*([^\n]+)|리서치 주제:\s*"([^"]+)"|검색 키워드:\s*"([^"]+)"',
            prompt
        )
        topic = "요청된 연구 주제"
        if topic_match:
            topic = next((g for g in topic_match.groups() if g is not None), "요청된 연구 주제").strip()

        # category를 프롬프트 및 시스템 프롬프트에서 다차원 추출
        category_match = re.search(
            r'카테고리:\s*"([^"]+)"|카테고리:\s*([^\n\r]+)|카테고리:\s*"([^"]+)"',
            prompt + "\n" + (system_prompt or "")
        )
        category = "etc"
        if category_match:
            category = next((g for g in category_match.groups() if g is not None), "etc").strip()

        # JSON 요청에 대한 모의 응답 처리
        if "JSON" in prompt or (system_prompt and "JSON" in system_prompt):
            clean_topic = topic.replace('"', '').strip()
            return json.dumps({
                "web": f"{clean_topic} 일반 역사 및 현대적 정의",
                "academic": f"{clean_topic} 학술 연구 및 전문 논문 정보",
                "sns": f"#{clean_topic.replace(' ', '')} 관련 여론 트렌드 분석",
                "community": f"{clean_topic} 대중적 질문 및 포럼 스레드"
            }, ensure_ascii=False)
        
        # 일반 보고서 생성 모의 응답 처리 (카테고리별 동적 팩트 생성 기능)
        cat_lower = category.lower()
        cat_korean = {
            "history": "역사 고증 및 사료 연구",
            "science": "자연과학 및 생물학 법칙",
            "medical": "의학/생명과학 및 임상 분석",
            "law": "법률/제도 및 사법 고증",
            "etc": "일반 상식 및 창작 보조"
        }.get(cat_lower, "일반 고증")

        detail_facts = ""
        if "medical" in cat_lower or "수면" in topic or "포유류" in topic:
            detail_facts = f"""* **생체 리듬 불균형**: "{topic}" 연구에 따르면, 과도한 수면은 생체 시계(서커디안 리듬)를 교란하여 호르몬 분비 불균형을 촉진합니다.
* **임상 연구 사례**: 하루 9시간 이상의 과수면은 뇌의 인지 기능 저하와 집중력 감퇴를 유발하며 만성 피로의 주원인이 됨이 검증되었습니다.
* **신경계 영향**: 멜라토닌과 세로토닌의 과다 분비 조절 실패로 무기력증 및 지연형 수면 위상 장애가 동반될 수 있습니다."""
        elif "science" in cat_lower or "법칙" in topic:
            detail_facts = f"""* **물리적 모순성 검증**: "{topic}"의 관점에서 에너지 보존 법칙과 열역학적 물리 한계를 교차 검증했습니다.
* **시뮬레이션 분석**: 거시적 물리 현상 시뮬레이션 결과, 제안된 설정의 개연성 매칭율은 92% 수준입니다.
* **우주론적 고증**: 해당 특이점에 적용 시 조석력이 선체 및 내부 소립자에 미치는 물리적 영향 한계값을 정밀 획득했습니다."""
        elif "history" in cat_lower or "역사" in topic:
            detail_facts = f"""* **사료 검증**: 조선왕조실록 및 동시대 문헌 사료들을 크로스 체크하여 "{topic}"의 사실성 및 고증 여부를 판단했습니다.
* **시대상 팩트**: 당시 의복, 무기 체계, 신분 제도적 관행상 발생할 수 있는 모순적 서사 오류를 필터링했습니다."""
        else:
            detail_facts = f"""* **핵심 고증 정보**: "{topic}"의 일반 상식 지식을 크로스 분석하여 창작에 즉시 적용 가능한 텍스트 덩어리를 합성했습니다.
* **창작 제언**: 해당 카테고리 설정을 집필 에이전트의 프롬프트 컨텍스트에 바인딩하여 서사의 디테일을 극대화하세요."""

        return f"""# [Mock Research Report] {topic} 고증 분석 보고서
* 카테고리: {category}
* 자료 종류: {cat_korean}
* 출처: https://mock-source.org/search?q={topic.replace(' ', '+')}

## 1. 개요 및 학술적 고증 분석
요청하신 "{topic}" 주제에 대해 모의 지식 엔진 및 사전 구축된 고증 스키마를 바탕으로 크로스 체크 분석을 거친 리포트입니다.

## 2. 세부 팩트 요약
{detail_facts}

## 3. 집필 RAG 가이드
본 문서의 분석 내용을 에피소드 집필 시 적용하면, 관련 용어나 묘사가 작가 프롬프트에 RAG(검색 증강)로 자연스럽게 스며들어 고증적 완성도가 폭발적으로 상승합니다."""

    if provider == "openai":
        from openai import AsyncOpenAI
        key = api_key or settings.OPENAI_API_KEY
        if not key:
            raise ValueError("OpenAI API Key가 설정되지 않았습니다.")
        client = AsyncOpenAI(api_key=key)
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        res = await client.chat.completions.create(
            model=model or "gpt-4o-mini",
            messages=messages,
            temperature=0.3
        )
        return res.choices[0].message.content or ""
        
    elif provider == "google":
        import google.generativeai as genai
        key = api_key or settings.GOOGLE_API_KEY
        if not key:
            raise ValueError("Google API Key가 설정되지 않았습니다.")
        genai.configure(api_key=key)
        model_inst = genai.GenerativeModel(model or "gemini-1.5-flash")
        
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        res = await model_inst.generate_content_async(full_prompt)
        return res.text or ""
        
    elif provider == "anthropic":
        from anthropic import AsyncAnthropic
        key = api_key or settings.ANTHROPIC_API_KEY
        if not key:
            raise ValueError("Anthropic API Key가 설정되지 않았습니다.")
        client = AsyncAnthropic(api_key=key)
        
        # System parameters are separate in Anthropic API
        res = await client.messages.create(
            model=model or "claude-3-5-sonnet-20240620",
            max_tokens=2000,
            system=system_prompt or "",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        return res.content[0].text if res.content else ""
        
    else:
        return f"[Mock LLM Response] provider={provider}, model={model}에 대한 처리기가 연동되지 않아 모의 답변을 반환합니다. 프롬프트: {prompt[:100]}..."

async def run_researcher_agent(
    project_id: int,
    topic: str,
    category: str,
    target_sources: List[str]
):
    """
    리서치 에이전트(Researcher Agent) 워크플로우를 기동합니다.
    선택된 타겟 소스들(web, academic, sns, community)을 병렬 분기 조회하고 요약합니다.
    """
    logger.info(f"Starting research workflow for project {project_id} on topic: '{topic}'")
    
    # 1. DB 세션 획득 및 프로젝트 설정 로드
    async for session in get_async_session():
        try:
            stmt = select(Project).where(Project.id == project_id)
            res = await session.execute(stmt)
            project = res.scalar_one_or_none()
            if not project:
                logger.error(f"Project {project_id} not found. Aborting research.")
                return
            
            # 암호화 복호화 처리
            api_key = decrypt_api_key(project.api_key_override)
            provider = project.llm_provider
            model = project.llm_model
            
            # 2. Query Generator (각 타겟 소스별 고유 검색 키워드 생성)
            query_prompt = f"""
            소설 작가를 위한 리서치 주제: "{topic}"
            다음 타겟 데이터 소스들에 대해 검색 엔진에 쿼리할 최적의 검색어들을 JSON 형식으로 각각 1개씩 생성해 주세요.
            타겟 소스 목록: {target_sources}
            
            응답은 반드시 아래 JSON 스펙으로만 작성해 주세요 (Markdown wrapper 금지):
            {{
              "web": "일반 웹 검색용 최적 키워드",
              "academic": "학술지/논문용 정밀 학술 검색 키워드",
              "sns": "SNS 트렌드/여론 파악용 해시태그 및 키워드",
              "community": "커뮤니티 포럼 등 대중적 질문용 키워드"
            }}
            """
            
            query_json_str = await query_llm_internal(
                provider=provider,
                model=model,
                api_key=api_key,
                prompt=query_prompt,
                system_prompt="You are a research assistant query planner. Return ONLY raw JSON without markdown syntax."
            )
            
            # JSON 파싱 가드
            try:
                # markdown json wrapper 제거
                cleaned_str = query_json_str.strip().replace("```json", "").replace("```", "").strip()
                queries = json.loads(cleaned_str)
            except Exception:
                # 파싱 실패 시 디폴트 값 매핑
                queries = {src: topic for src in target_sources}
            
            # 3. Search Executor (소스별 라우팅 및 툴 실행)
            search_results: Dict[str, List[Dict[str, Any]]] = {}
            tavily_key = settings.TAVILY_API_KEY
            
            for source in target_sources:
                search_query = queries.get(source, topic)
                search_results[source] = []
                
                # Tavily API 키가 있을 경우 실제 웹 검색 수행
                if TavilyClient and tavily_key and source in ["web", "academic", "community"]:
                    try:
                        logger.info(f"Executing real Tavily search for source '{source}' with query: '{search_query}'")
                        tavily_client = TavilyClient(api_key=tavily_key)
                        
                        # 학술 용도(academic)는 좀 더 학술용 뉴스 등 고품질 검색 범위 필터링 묘사
                        topic_type = "news" if source == "academic" else "general"
                        response = tavily_client.search(query=search_query, topic=topic_type, max_results=3)
                        
                        for item in response.get("results", []):
                            search_results[source].append({
                                "title": item.get("title", "No Title"),
                                "content": item.get("content", ""),
                                "url": item.get("url", "")
                            })
                    except Exception as se:
                        logger.warning(f"Real search failed for source '{source}': {str(se)}. Falling back to LLM Mock search.")
                
                # API Key가 없거나 검색이 실패한 경우 LLM Mock Search (검색 데이터 가상 합성) 수행
                if not search_results[source]:
                    logger.info(f"Executing LLM Mock Search for source '{source}' with query: '{search_query}'")
                    mock_prompt = f"""
                    타겟 데이터 풀: [{source}]
                    검색 키워드: "{search_query}"
                    
                    위 키워드에 대해 해당 데이터 풀에서 수집될 법한 가상의 사실 관계 정보 스니펫 2~3개를 사실적으로 상세히 생성해 주세요.
                    자료 제목, 핵심 요약 내용, 신뢰할 만한 모의 출처 URL 링크 정보를 포함해 주어야 합니다.
                    """
                    
                    mock_res = await query_llm_internal(
                        provider=provider,
                        model=model,
                        api_key=api_key,
                        prompt=mock_prompt,
                        system_prompt="You are a data crawler simulator. Generate realistic fact snippets."
                    )
                    search_results[source].append({
                        "title": f"[{source.upper()} Simulated Search Data] {search_query}",
                        "content": mock_res,
                        "url": f"https://mock-source.org/search?q={source}"
                    })

            # 4. Synthesis & Fact Check (마크다운 보고서로 다차원 통합)
            synthesis_prompt = f"""
            검색 결과 데이터 풀: {json.dumps(search_results, ensure_ascii=False, indent=2)}
            리서치 주제: "{topic}"
            카테고리: "{category}"
            
            위 검색 데이터 풀로부터 수집된 정보들을 교차 검증하고 요약하여, 소설 집필 시 작가가 참고할 수 있는 체계적인 마크다운 형식의 '고증 리서치 보고서'를 완성해 주세요.
            각 소스(SNS의 트렌드 반응, 학술지의 역사/과학적 사실 검증 등)의 성격을 분류하여 섹션별로 정리해 주어야 합니다.
            마지막에는 모순이 있거나 가짜 정보일 확률이 있는 팩트를 교차 검증해 알려주는 '고증 검증 노트'를 포함하세요.
            """
            
            final_report = await query_llm_internal(
                provider=provider,
                model=model,
                api_key=api_key,
                prompt=synthesis_prompt,
                system_prompt="You are an expert researcher. Synthesize factual reference reports."
            )
            
            # 5. DB 적재
            first_url = None
            for src in target_sources:
                if search_results.get(src):
                    first_url = search_results[src][0].get("url")
                    break
            
            new_ref = ReferenceMaterial(
                project_id=project_id,
                title=f"[리서치 보고서] {topic}",
                content=final_report,
                category=category,
                source_type=",".join(target_sources),
                source_url=first_url
            )
            session.add(new_ref)
            await session.commit()
            logger.info(f"Successfully saved research report to ReferenceMaterial for project {project_id}")
            
        except Exception as e:
            logger.error(f"Failed to execute research workflow: {str(e)}", exc_info=True)
        break
