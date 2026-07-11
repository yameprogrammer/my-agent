from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_anthropic import ChatAnthropic
from langchain_ollama import ChatOllama
from typing import Optional
from app.core.config import settings
from app.core.crypto import decrypt_api_key

class LLMFactory:
    @staticmethod
    def get_model(
        provider: str,
        model_name: str,
        api_key_override: Optional[str] = None,
        temperature: float = 0.7
    ) -> BaseChatModel:
        """
        제공자(Provider)에 따라 적절한 LangChain 비동기 호환 챗 모델 인스턴스 반환
        """
        provider_lower = provider.lower()
        
        if provider_lower == "openai":
            api_key = decrypt_api_key(api_key_override) or settings.OPENAI_API_KEY
            return ChatOpenAI(
                model=model_name,
                api_key=api_key,
                temperature=temperature
            )
        elif provider_lower == "google":
            api_key = decrypt_api_key(api_key_override) or settings.GOOGLE_API_KEY
            # ChatGoogleGenerativeAI expects google_api_key
            return ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=api_key,
                temperature=temperature
            )
        elif provider_lower == "anthropic":
            api_key = decrypt_api_key(api_key_override) or settings.ANTHROPIC_API_KEY
            return ChatAnthropic(
                model=model_name,
                api_key=api_key,
                temperature=temperature
            )
        elif provider_lower == "ollama":
            # Ollama는 로컬 API를 사용 (기본 localhost:11434)
            # 로컬 모델의 컨텍스트 및 텍스트 잘림 현상을 방지하기 위해 최대 출력 토큰 수(num_predict)를 4096, 컨텍스트 창(num_ctx)을 8192로 확장합니다.
            # 또한, 로컬 모델의 JSON 구조화 추론 붕괴(Hallucination/정크 숫자 출력)를 차단하기 위해 온도를 0.1로 강제 제한합니다.
            return ChatOllama(
                model=model_name,
                temperature=0.1,
                num_predict=4096,
                num_ctx=8192
            )
        else:
            raise ValueError(f"지원하지 않는 LLM 제공자입니다: {provider}")

    @staticmethod
    def get_model_for_agent(
        project,
        agent_type: str,
        temperature: float = 0.7
    ) -> BaseChatModel:
        """
        프로젝트와 에이전트 타입(plotter, writer, judge, editor, reviewer)에 따른 챗 모델 인스턴스 반환.
        개별 에이전트 설정이 지정되지 않았거나 빈 값일 경우 프로젝트 기본 설정을 폴백으로 사용합니다.
        """
        provider = getattr(project, f"{agent_type}_provider", None)
        model_name = getattr(project, f"{agent_type}_model", None)
        api_key_override = getattr(project, f"{agent_type}_api_key", None)

        # 개별 설정이 완전하지 않은 경우 프로젝트 대표 설정을 Fallback으로 사용
        if not provider or not model_name:
            provider = project.llm_provider
            model_name = project.llm_model
            api_key_override = project.api_key_override

        return LLMFactory.get_model(
            provider=provider,
            model_name=model_name,
            api_key_override=api_key_override,
            temperature=temperature
        )
