# LLM Step 1 Complete: LLM 클라이언트 추상화 계층

## 구현 범위
- **Step 1 목표**: LLM 클라이언트 추상화 + 설정 시스템 구축 (실제 LLM 호출은 아직 연결되지 않음)
- Stub 모드와 Ollama 모드를 지원하는 기반 마련
- EmbedderFactory와 유사한 일관된 팩토리 패턴 적용
- langchain_ollama 미설치 / 서버 미가동 시 graceful fallback

## 변경/생성된 파일
- `packages/llm/__init__.py`
- `packages/llm/base.py` — `LLMClient` 추상 클래스
- `packages/llm/stub_client.py` — `StubLLMClient` (기본 fallback)
- `packages/llm/ollama_client.py` — `OllamaLLMClient` (langchain_ollama 기반)
- `packages/llm/llm_factory.py` — `LLMFactory`
- `config/llm_config.json` — 새로운 설정 파일 (기본은 "stub")

## 시스템 아키텍처 변경
- **새 패키지**: `packages/llm/`
- LLM 주입은 향후 에이전트(`SceneWriterAgent` 등)와 워크플로우에 `llm_client` 인자로 전달 예정
- 현재는 어떤 에이전트에도 연결되지 않았음 (Step 3부터 본격 연결)
- `LLMFactory(mode="stub")` 는 항상 안전하게 동작
- `LLMFactory(mode="ollama")` 는 `langchain_ollama` 미설치 시 자동으로 stub으로 대체

## 검증 결과
- `python -c "from packages.llm import LLMFactory; ..."` 정상 동작
- Stub 모드에서 `generate_text()` / `generate_structured()` 호출 성공
- Structured output은 Pydantic 모델에 대해 기본값으로 채워 반환
- config/llm_config.json 로딩 정상 (파일 없으면 안전한 기본값 사용)
- 기존 pytest 전체 통과에 영향 없음

## 운영 가이드 (현재 단계)
1. 기본은 stub 모드이므로 별도 설정 없이 사용 가능
2. 실제 Ollama 사용을 원하면:
   ```json
   // config/llm_config.json
   {
     "mode": "ollama",
     "default_model": "qwen2.5:7b-instruct",
     "ollama": { "base_url": "http://localhost:11434", ... }
   }
   ```
3. `langchain-ollama` 설치 필요 (추후 requirements에 추가 예정):
   ```bash
   pip install langchain-ollama
   ```

## 향후 단계 연결
- **Step 2**: 프롬프트 템플릿 시스템 구축
- **Step 3**: `SceneWriterAgent`에 LLM 연결 (여기서부터 실제 본문 생성 시작)
- `LLMFactory`는 `EmbedderFactory`와 함께 워크플로우 생성 함수에 전달될 예정

## 참고
- 상세 작업 사양서: `docs/llm-step-01-llm-abstraction-spec.md`
- 전체 LLM 계획: `docs/llm-implementation-plan.md`
- 기존 패턴 참고: `packages/embeddings.py` (EmbedderFactory)

---

**Step 1 완료**. 기반이 준비되었으므로 다음 단계로 진행 가능.
