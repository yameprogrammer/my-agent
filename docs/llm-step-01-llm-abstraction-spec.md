# Step 1: LLM 클라이언트 추상화 계층 + 설정 — 상세 작업 사양서

## 1. 목적
- 기존 에이전트들이 LLM에 의존하지 않고 스텁으로 동작하는 구조를 유지하면서, 실제 LLM을 주입할 수 있는 기반을 만든다.
- `EmbedderFactory`와 유사한 패턴으로 `LLMFactory`를 제공한다.
- Ollama 로컬 모델을 1순위로 지원하고, "stub" 모드로 항상 fallback이 가능하게 한다.
- 향후 OpenAI 등 다른 백엔드 확장을 위한 인터페이스를 정의한다.

## 2. 선행 조건
- 기존 `packages/embeddings.py`의 `EmbedderFactory` 패턴을 참고한다.
- `packages/agents/`의 모든 Agent가 `embedder_factory`를 받는 구조를 이해한다.
- `requirements.txt`에 `langchain`과 `langchain-community`가 이미 있음.

## 3. 상세 작업 목록

### 3.1 디렉토리 및 파일 생성
- `packages/llm/__init__.py` 생성
- `packages/llm/llm_factory.py` 생성
- `packages/llm/base.py` 생성 (추상 인터페이스)
- `packages/llm/ollama_client.py` 생성
- `packages/llm/stub_client.py` 생성 (기존 스텁 동작 재현)
- `config/llm_config.json` 생성 (예시)

### 3.2 config/llm_config.json 예시
```json
{
  "mode": "stub",
  "default_model": "qwen2.5:7b-instruct",
  "ollama": {
    "base_url": "http://localhost:11434",
    "temperature": 0.65,
    "max_tokens": 4096,
    "timeout": 120
  },
  "stub": {
    "enabled": true
  }
}
```

### 3.3 핵심 인터페이스 정의 (base.py)
```python
from abc import ABC, abstractmethod
from typing import Any, Type
from pydantic import BaseModel

class LLMClient(ABC):
    def __init__(self, model_name: str, **kwargs):
        self.model_name = model_name

    @abstractmethod
    def generate_structured(
        self, 
        prompt: str, 
        output_schema: Type[BaseModel],
        system_prompt: str | None = None,
        **kwargs
    ) -> BaseModel:
        """구조화된 출력을 반환한다."""
        pass

    @abstractmethod
    def generate_text(
        self, 
        prompt: str, 
        system_prompt: str | None = None,
        **kwargs
    ) -> str:
        pass
```

### 3.4 LLMFactory 구현 (llm_factory.py)
- `LLMFactory` 클래스
- `create(mode: str | None = None) -> LLMClient`
- config 로딩: `config/llm_config.json` 읽기
- mode="stub" → StubClient
- mode="ollama" → OllamaClient (langchain_ollama.ChatOllama 사용 권장)

### 3.5 StubClient 구현
- 기존 에이전트들의 하드코딩된 출력 패턴을 최대한 재현
- 예: ThemeScout은 seed_bank 기반, SceneWriter는 템플릿 기반 반환
- 테스트 시 완벽 호환 보장

### 3.6 OllamaClient 구현
- `langchain_ollama import ChatOllama`
- `with_structured_output(output_schema)` 사용 추천
- 실패 시 재시도 로직 (최대 2회)
- raw_output과 parsed_output 기록을 위해 `invoke` 결과를 반환할 수 있게 설계

### 3.7 requirements 업데이트 제안
`requirements.txt`에 추가:
```
langchain-ollama>=0.2.0
```

## 4. Agent 주입 패턴 변경 예시 (향후 사용)
```python
from packages.llm import LLMFactory

llm = LLMFactory().create()
agent = SceneWriterAgent(
    repository=repo,
    memory_store=memory,
    embedder_factory=embedder_factory,
    llm_client=llm   # 추가
)
```

## 5. 수용 기준 (체크리스트)
- [ ] `LLMFactory(mode="stub").create()` 호출 성공
- [ ] `LLMFactory().create()` (config 기본값)가 stub을 반환
- [ ] `config/llm_config.json` 로드 정상
- [ ] 기존 테스트 전체 통과 (pytest)
- [ ] `python -c "from packages.llm import LLMFactory; ..."` 로 import 에러 없음
- [ ] Ollama 모드에서 간단한 structured call이 (모델 있으면) 동작

## 6. 테스트 방법
- 단위 테스트: `tests/test_llm_factory.py` 작성 (stub 모드 중심)
- 기존 `tests/test_admin_workflow.py` 등이 여전히 통과하는지 확인
- `python main.py --init-db` 후 bootstrap으로 스텁 모드 동작 확인

## 7. 산출물
- `packages/llm/` 전체 모듈
- `config/llm_config.json`
- `tests/test_llm_factory.py`
- `requirements.txt` 업데이트 제안
- 이 사양서의 체크리스트 통과

## 8. 다음 단계 연결
Step 1 완료 후 **Step 2** (프롬프트 시스템)로 진행. Step 1이 완료되지 않으면 이후 모든 LLM 주입이 불가능하다.

**참고**: 이 단계에서는 아직 실제 LLM 호출로 창작을 하지 않는다. 기반만 마련.