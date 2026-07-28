from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_anthropic import ChatAnthropic
from langchain_ollama import ChatOllama
from typing import Optional
from app.core.config import settings
from app.core.crypto import decrypt_api_key

# NVIDIA NIM 호스티드 OpenAI 호환 엔드포인트
# 문서: https://docs.api.nvidia.com/nim/reference/llm-apis
NVIDIA_NIM_BASE_URL = "https://integrate.api.nvidia.com/v1"


class LLMFactory:
    @staticmethod
    def _request_timeout() -> Optional[float]:
        """단일 LLM HTTP 요청 타임아웃(초). 0 이하이면 None(비활성)."""
        try:
            sec = float(getattr(settings, "LLM_REQUEST_TIMEOUT_SECONDS", 120.0) or 0)
        except (TypeError, ValueError):
            sec = 120.0
        return sec if sec > 0 else None

    @staticmethod
    def get_model(
        provider: str,
        model_name: str,
        api_key_override: Optional[str] = None,
        temperature: float = 0.7
    ) -> BaseChatModel:
        """
        제공자(Provider)에 따라 적절한 LangChain 비동기 호환 챗 모델 인스턴스 반환.
        모든 제공자에 보수적 request timeout 을 적용해 hang 을 방지한다.
        """
        provider_lower = provider.lower()
        timeout = LLMFactory._request_timeout()
        
        if provider_lower == "openai" or provider_lower == "custom_openai":
            decrypted = decrypt_api_key(api_key_override)
            base_url = None
            api_key = decrypted
            
            if decrypted and "::" in decrypted:
                parts = decrypted.split("::", 1)
                api_key = parts[0]
                base_url = parts[1]
                
            if not api_key:
                api_key = settings.OPENAI_API_KEY

            # OpenAI 호환 Base URL 정규화
            # - Ollama Cloud 직접 접근: https://ollama.com  → https://ollama.com/v1
            #   (ChatOpenAI 는 base_url + /chat/completions 를 붙인다.
            #    네이티브 /api 경로나 루트만 넣으면 404/실패)
            # - 로컬 Ollama OpenAI 호환: http://127.0.0.1:11434 → …/v1
            if base_url:
                bu = base_url.strip().rstrip("/")
                low = bu.lower()
                if "ollama.com" in low and not low.endswith("/v1"):
                    # https://ollama.com 또는 https://ollama.com/api → /v1
                    if low.endswith("/api"):
                        bu = bu[: -len("/api")] + "/v1"
                    else:
                        bu = bu + "/v1"
                elif (
                    ("11434" in low or low.endswith("/ollama") or "localhost" in low)
                    and not low.endswith("/v1")
                    and provider_lower == "custom_openai"
                ):
                    if not low.endswith("/v1"):
                        bu = bu + "/v1"
                base_url = bu

            # --- 인증 가드 (401 예방) ---
            # custom_openai 인데 base_url 이 없으면 OpenAI 공식 호스트로 가서
            # Ollama/DeepSeek 키가 401 을 낸다.
            if provider_lower == "custom_openai" and not base_url:
                raise ValueError(
                    "OpenAI 호환(custom) 사용 시 API Base URL 이 필요합니다. "
                    "예: https://ollama.com/v1 또는 https://api.deepseek.com/v1 "
                    "(설정 저장 시 API 키와 Base URL을 함께 다시 입력해 주세요.)"
                )

            is_ollama_cloud = bool(base_url and "ollama.com" in base_url.lower())
            is_local_ollama = bool(
                base_url
                and (
                    "11434" in base_url
                    or "localhost" in base_url.lower()
                    or "127.0.0.1" in base_url
                )
            )

            # Ollama Cloud 는 반드시 ollama.com 에서 발급한 실 키 필요
            # (키 없이 저장되면 빈 키 → 예전 코드가 'ollama' 로 폴백 → 401)
            if is_ollama_cloud:
                if not api_key or api_key.strip() in ("", "ollama", "dummy", "test"):
                    raise ValueError(
                        "Ollama Cloud 401 방지: API 키가 없거나 플레이스홀더입니다. "
                        "https://ollama.com/settings/keys 에서 키를 만들고, "
                        "설정에 Base URL=https://ollama.com/v1 과 함께 키를 다시 저장하세요. "
                        "(키만 바꾸고 URL 없이 저장하면 키가 유실될 수 있습니다.)"
                    )
                resolved_key = api_key.strip()
            elif is_local_ollama:
                # 로컬 Ollama 는 키가 형식상만 필요
                resolved_key = (api_key or "ollama").strip()
            else:
                if not api_key:
                    raise ValueError(
                        "OpenAI 호환 API 키가 비어 있습니다. 프로젝트 설정에 키를 저장하세요."
                    )
                resolved_key = api_key.strip()

            kwargs = dict(
                model=model_name,
                api_key=resolved_key,
                base_url=base_url,
                temperature=temperature,
            )
            if timeout is not None:
                # langchain-openai: timeout / request_timeout 모두 호환 시도
                kwargs["timeout"] = timeout
            return ChatOpenAI(**kwargs)
        elif provider_lower == "nvidia":
            # NVIDIA NIM: OpenAI Chat Completions 호환 + 고정 base_url
            # 모델 ID 예: meta/llama-3.1-8b-instruct, nvidia/nemotron-3-nano-30b-a3b
            api_key = decrypt_api_key(api_key_override) or settings.NVIDIA_API_KEY
            kwargs = dict(
                model=model_name,
                api_key=api_key,
                base_url=NVIDIA_NIM_BASE_URL,
                temperature=temperature,
            )
            if timeout is not None:
                kwargs["timeout"] = timeout
            return ChatOpenAI(**kwargs)
        elif provider_lower == "google":
            api_key = decrypt_api_key(api_key_override) or settings.GOOGLE_API_KEY
            kwargs = dict(
                model=model_name,
                google_api_key=api_key,
                temperature=temperature,
            )
            if timeout is not None:
                kwargs["timeout"] = timeout
            return ChatGoogleGenerativeAI(**kwargs)
        elif provider_lower == "anthropic":
            api_key = decrypt_api_key(api_key_override) or settings.ANTHROPIC_API_KEY
            kwargs = dict(
                model=model_name,
                api_key=api_key,
                temperature=temperature,
            )
            if timeout is not None:
                kwargs["default_request_timeout"] = timeout
                kwargs["timeout"] = timeout
            try:
                return ChatAnthropic(**kwargs)
            except TypeError:
                kwargs.pop("timeout", None)
                kwargs.pop("default_request_timeout", None)
                if timeout is not None:
                    kwargs["default_request_timeout"] = timeout
                return ChatAnthropic(**kwargs)
        elif provider_lower == "ollama":
            # Ollama는 로컬 API를 사용 (기본 localhost:11434)
            # 로컬 모델의 컨텍스트 및 텍스트 잘림 현상을 방지하기 위해 최대 출력 토큰 수(num_predict)를 4096, 컨텍스트 창(num_ctx)을 8192로 확장합니다.
            # 또한, 로컬 모델의 JSON 구조화 추론 붕괴(Hallucination/정크 숫자 출력)를 차단하기 위해 온도를 0.1로 강제 제한합니다.
            kwargs = dict(
                model=model_name,
                temperature=0.1,
                num_predict=4096,
                num_ctx=8192,
            )
            if timeout is not None:
                # ChatOllama: client kwargs / timeout 필드 버전별 상이
                kwargs["timeout"] = timeout
            try:
                return ChatOllama(**kwargs)
            except TypeError:
                kwargs.pop("timeout", None)
                return ChatOllama(**kwargs)
        else:
            raise ValueError(f"지원하지 않는 LLM 제공자입니다: {provider}")

    # IDEA-13: 저비용 모드 시 비-Writer 역할에 쓸 소형 모델 프리셋
    LOW_COST_MODELS = {
        "openai": "gpt-4o-mini",
        "google": "gemini-2.0-flash",
        "anthropic": "claude-3-5-haiku-latest",
        "nvidia": "meta/llama-3.1-8b-instruct",
        "ollama": "llama3.2",
        "custom_openai": "gpt-4o-mini",
    }

    @staticmethod
    def get_model_for_agent(
        project,
        agent_type: str,
        temperature: float = 0.7
    ) -> BaseChatModel:
        """
        프로젝트와 에이전트 타입(plotter, writer, judge, editor, reviewer)에 따른 챗 모델 인스턴스 반환.
        개별 에이전트 설정이 지정되지 않았거나 빈 값일 경우 프로젝트 기본 설정을 폴백으로 사용합니다.
        IDEA-13 low_cost_mode: writer 제외 역할은 소형 모델 프리셋 (에이전트 전용 오버라이드가 없을 때).
        """
        provider = getattr(project, f"{agent_type}_provider", None)
        model_name = getattr(project, f"{agent_type}_model", None)
        api_key_override = getattr(project, f"{agent_type}_api_key", None)

        # 개별 설정이 완전하지 않은 경우 프로젝트 대표 설정을 Fallback으로 사용
        if not provider or not model_name:
            provider = project.llm_provider
            model_name = project.llm_model
            api_key_override = project.api_key_override
            # 저비용: Writer 만 기본(대형) 유지, 나머지 소형
            if getattr(project, "low_cost_mode", False) and agent_type != "writer":
                provider_key = (provider or "openai").lower()
                model_name = LLMFactory.LOW_COST_MODELS.get(
                    provider_key, LLMFactory.LOW_COST_MODELS["openai"]
                )

        return LLMFactory.get_model(
            provider=provider,
            model_name=model_name,
            api_key_override=api_key_override,
            temperature=temperature
        )
