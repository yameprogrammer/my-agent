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
            return ChatOllama(
                model=model_name,
                temperature=temperature
            )
        else:
            raise ValueError(f"지원하지 않는 LLM 제공자입니다: {provider}")
