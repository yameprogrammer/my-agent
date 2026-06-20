# LLM 에이전트 통합 구현 계획서 (LLM Agent Integration Plan)

> **작성일**: 2026-06-20  
> **목적**: 현재 모든 에이전트가 스텁(stub)으로 구현되어 있어 실제 LLM 기반 소설 생성이 동작하지 않는 문제를 해결하기 위한 단계적 구현 계획을 수립한다.

## 작업 진행 체크리스트

각 단계별 상세 사양서를 완료할 때마다 아래 체크리스트를 표시하세요:

- [ ] Step 1: LLM 클라이언트 추상화 (`llm-step-01-...`)
- [ ] Step 2: 프롬프트 템플릿 시스템 (`llm-step-02-...`)
- [ ] Step 3: SceneWriterAgent LLM화 (**M1** — 실제 본문 생성) (`llm-step-03-...`)
- [ ] Step 4: Planner 에이전트 LLM화
- [ ] Step 5: Episode 상세 계획 에이전트 LLM화
- [ ] Step 6: 생성 로깅
- [ ] Step 7: 워크플로우 통합
- [ ] Step 8: 마무리 및 문서화

**M1 완료 목표**: Step 1~3이 끝나면 Admin Console에서 실제 LLM이 쓴 소설 원고를 볼 수 있어야 합니다.

## 1. 개요

### 배경
- 현재 `packages/agents/` 하의 모든 에이전트(ThemeScoutAgent, MasterPlannerAgent, ArcPlannerAgent, EpisodeCycleAgent, EpisodeDetailAgent, SceneWriterAgent, Judge 계열)는 **실제 LLM 호출 없이** 동작한다.
- 생성 로직은 하드코딩된 seed 데이터, 문자열 템플릿, embedding cosine similarity에 의존한다.
- `SceneWriterAgent._build_draft_text()`는 장면 비트를 단순 나열한 구조화 텍스트만 반환한다 (실제 산문(prose) 생성 없음).
- Ollama는 **임베딩 전용**으로만 설정되어 있다 (`config/embedding_config.json`, `packages/embeddings.py`).
- `novel_blueprint/10_prompts_contracts.md`와 `05_agents.md`에는 이미 LLM + 구조화 출력 + 프롬프트 계약이 설계되어 있으나, 실제 구현이 누락된 상태다.
- `generation_runs`, `prompt_logs` 테이블은 스키마만 존재하고, 실제 LLM 실행 로깅은 이루어지지 않는다.

### 문제점
- 사용자가 아무리 강력한 로컬 LLM을 Ollama에 설치해도 소설 품질이 개선되지 않는다.
- "집필" 결과물이 항상 비슷한 템플릿 형태로 나와 몰입도와 창의성이 극히 낮다.
- 검수 루프(StyleJudge, ReaderHook, Continuity)는 의미가 반감된다 (입력 자체가 저품질).

### 목표
실제 LLM(주로 Ollama 로컬 모델)을 각 에이전트에 연결하여, **구조화된 계획 + 고품질 산문 생성**이 가능한 시스템으로 전환한다.
- 프롬프트 기반 창작
- 구조화 출력(Pydantic) 유지
- 메모리/RAG 컨텍스트 주입
- 생성 이력 추적 (generation_runs + prompt_logs)
- 스텁 모드 fallback 유지 (테스트/개발용)

**성공 기준 (Definition of Done)**
- `theme_to_arcs` → `episode_to_draft` 실행 시 실제 LLM이 생성한 logline, arcs, scene_beats, **draft_text(산문)** 이 생성된다.
- 생성된 본문이 단순 템플릿이 아닌, 서사적 흐름과 문장 스타일을 가진 텍스트다.
- 프롬프트 버전, 모델명, raw_output, retrieved memory가 `generation_runs` / `prompt_logs`에 기록된다.
- Admin Console에서 생성 결과의 품질을 체감할 수 있다.
- 기존 테스트와 스텁 fallback이 여전히 동작한다.

## 2. 범위

### 포함 (이 계획의 대상)
- LLM 클라이언트 추상화 계층 (Ollama 중심 + 확장 가능)
- 프롬프트 템플릿 관리 시스템 (`prompts/` 디렉토리)
- 주요 에이전트 LLM화:
  - SceneWriterAgent (최우선 — 실제 본문 생성)
  - MasterPlannerAgent, ArcPlannerAgent
  - EpisodeCycleAgent, EpisodeDetailAgent
- Judge 에이전트는 heuristic + LLM 하이브리드 (후순위)
- 생성 로깅 (`GenerationRun`, `PromptLog`)
- LLM 설정 (`config/llm_config.json` 또는 통합 설정)
- 워크플로우 내 LLM 주입 및 메모리 컨텍스트 주입
- 기본적인 프롬프트 품질 가이드

### 제외 (이 단계)
- 상용 API (OpenAI, Anthropic, Grok 등) 완전 지원 (인터페이스만 열어둠)
- 자동 재작성 루프 (Style/ReaderHook 결과 기반 프롬프트 조정)
- 고급 기법 (Chain of Thought, Self-Consistency, Agentic tool use)
- 멀티모달 (이미지 등)
- 성능 최적화 (배치, 캐싱, 병렬 호출 등 고도화)

**기술 스택 유지**: LangGraph + Pydantic + 기존 Memory + Repository. LLM은 LangChain Chat 모델 인터페이스(`langchain-ollama` 또는 community) 추천.

## 3. 현재 구조 요약

| 컴포넌트 | 현재 상태 | 문제 |
|----------|-----------|------|
| `packages/agents/*.py` | 전부 stub | LLM 호출 0회 |
| `SceneWriterAgent` | 템플릿 조합 | 산문 생성 없음 |
| `packages/embeddings.py` | Ollama 지원 (embedding) | generation용 아님 |
| `packages/orchestrator/workflows.py` | 에이전트 호출 | 실제 지능 없음 |
| `generation_runs` / `prompt_logs` | 테이블 + list만 | 로깅 미구현 |
| `novel_blueprint/10_prompts_contracts.md` | 설계 문서 | 구현 없음 |
| Admin UI (Workflow Execution) | 결과 표시 | 항상 비슷한 출력 |

## 4. 단계별 세분화 실행 계획

아래 표는 전체 로드맵이며, **각 단계는 독립적인 상세 작업 사양서**로 구체화되어 있다. 각 사양서를 따라 순차적으로 구현할 수 있도록 설계했다.

| Step | 제목 | 주요 가치 | 우선순위 | 선행 단계 | 상세 사양서 |
|------|------|-----------|----------|-----------|-------------|
| 1 | LLM 클라이언트 추상화 + 설정 | 모델 주입 기반 | 높음 | - | [llm-step-01-llm-abstraction-spec.md](./llm-step-01-llm-abstraction-spec.md) |
| 2 | 프롬프트 템플릿 시스템 | 재사용/버전 관리 | 높음 | 1 | [llm-step-02-prompt-system-spec.md](./llm-step-02-prompt-system-spec.md) |
| 3 | SceneWriterAgent LLM화 | **실제 소설 본문 생성** | 최고 | 1,2 | [llm-step-03-scene-writer-spec.md](./llm-step-03-scene-writer-spec.md) |
| 4 | Planner 에이전트 LLM화 | 기획 품질 향상 | 높음 | 1,2 | [llm-step-04-planner-agents-spec.md](./llm-step-04-planner-agents-spec.md) |
| 5 | Episode 상세 계획 에이전트 LLM화 | 장면/화 비트 품질 | 중 | 3,4 | [llm-step-05-episode-agents-spec.md](./llm-step-05-episode-agents-spec.md) |
| 6 | 생성 로깅 및 프롬프트 이력 추적 | 투명성 + 디버깅 | 중 | 3 | [llm-step-06-logging-spec.md](./llm-step-06-logging-spec.md) |
| 7 | 워크플로우 + 메모리 통합 | RAG + LLM 결합 | 중 | 1~6 | [llm-step-07-workflow-integration-spec.md](./llm-step-07-workflow-integration-spec.md) |
| 8 | 마무리, 검증, 문서화 | 사용자 체감 + 유지보수 | 낮음 | 3,6,7 | [llm-step-08-finalization-spec.md](./llm-step-08-finalization-spec.md) |

**권장 작업 순서**: Step 1 → Step 2 → Step 3 (여기까지 완료되면 실제 본문이 나오는 M1 마일스톤 달성) → 이후 단계.

각 단계의 **상세 작업 사양서**를 참고하여 구현하라. 사양서에는 파일 변경 목록, 인터페이스 정의, 코드 스케치, 프롬프트 예시, 수용 기준 체크리스트가 포함되어 있다.

---

### Step 1: LLM 클라이언트 추상화 계층 + 설정 (상세 사양서 참조)

**상세 사양서**: [docs/llm-step-01-llm-abstraction-spec.md](./llm-step-01-llm-abstraction-spec.md)

요약 목표: 어떤 LLM이든 쉽게 주입하고 교체할 수 있는 기반을 마련한다. Stub 모드를 기본으로 유지하여 기존 동작을 보장.

**목표**: 어떤 LLM이든 쉽게 교체할 수 있는 기반을 만든다.

**주요 작업**:
- `packages/llm/` 디렉토리 생성 (또는 `packages/llm_client.py`)
- `LLMFactory` / `LLMClient` 추상화 (`.generate_structured()` 또는 `.invoke_with_schema()`)
- `config/llm_config.json` 신규 작성
  - `mode`: "ollama" | "stub" | "openai" (미래)
  - `ollama_model`: "qwen2.5:7b" 등 추천
  - `base_url`, `temperature`, `max_tokens`, `timeout`
- 스텁 LLM 구현 (기존 에이전트 동작과 동일한 출력 반환)
- `EmbedderFactory`와 유사한 팩토리 패턴

**산출물**:
- `packages/llm/llm_factory.py`
- `config/llm_config.json` 예시
- 기본 ChatOllama 연동 코드 (langchain-ollama 권장)

**수용 기준**:
- `LLMFactory(mode="stub")`로 기존 에이전트 테스트 통과
- `LLMFactory(mode="ollama")`로 간단한 structured 호출 성공
- requirements에 필요한 패키지 추가 제안 (`langchain-ollama`)

**선행 단계**: 없음

### Step 2 ~ Step 8

각 단계의 **상세한 작업 목록, 파일 변경, 인터페이스, 코드 예시, 프롬프트 템플릿 예시, 수용 기준 체크리스트**는 아래 별도 사양서에 정리되어 있다.

- **Step 2**: [llm-step-02-prompt-system-spec.md](./llm-step-02-prompt-system-spec.md)
- **Step 3**: [llm-step-03-scene-writer-spec.md](./llm-step-03-scene-writer-spec.md) ← **가장 먼저 집중할 단계**
- **Step 4**: [llm-step-04-planner-agents-spec.md](./llm-step-04-planner-agents-spec.md)
- **Step 5**: [llm-step-05-episode-agents-spec.md](./llm-step-05-episode-agents-spec.md)
- **Step 6**: [llm-step-06-logging-spec.md](./llm-step-06-logging-spec.md)
- **Step 7**: [llm-step-07-workflow-integration-spec.md](./llm-step-07-workflow-integration-spec.md)
- **Step 8**: [llm-step-08-finalization-spec.md](./llm-step-08-finalization-spec.md)

**M1 마일스톤 (가장 중요한 가치 제공)**: Step 1 + Step 2 + Step 3 완료 시, 실제 LLM이 생성한 소설 본문을 Episode Build에서 확인할 수 있게 된다.

## 5. 기술 아키텍처 제안

### 추천 구조
```
packages/
  llm/
    __init__.py
    llm_factory.py          # LLMFactory
    base.py                 # LLMClient 추상
    ollama_client.py
    stub_client.py
  prompts/
    loader.py
    templates/
      scene_writer/
        v1.md
        v2.md
```

### LLM 호출 인터페이스 예시 (계획)
```python
class LLMClient:
    def generate_structured(self, prompt: str, output_schema: type[BaseModel], **kwargs) -> BaseModel:
        ...
```

### 설정 예시 (`config/llm_config.json`)
```json
{
  "mode": "ollama",
  "ollama": {
    "model": "qwen2.5:7b-instruct",
    "base_url": "http://localhost:11434",
    "temperature": 0.7,
    "max_tokens": 4096
  },
  "stub": {
    "enabled": true
  }
}
```

### 프롬프트 원칙 (blueprint 10_ 준수)
- JSON 최우선 출력 강제
- `assumptions`, `writer_warning` 필드 적극 활용
- 상위 산출물은 절대 덮어쓰지 않음

## 6. 모델 추천 (로컬 기준)

| 용도 | 추천 모델 (Ollama) | 비고 |
|------|---------------------|------|
| 기획 (Planner) | qwen2.5:7b / llama3.1:8b | 지시 따르기 강함 |
| 본문 집필 (SceneWriter) | qwen2.5:14b 또는 qwen2.5:7b | 창의성 + 한국어 |
| 검수 (Judge) | 더 가벼운 모델 or heuristic 혼용 | 비용 절감 |
| 임베딩 | nomic-embed-text (기존 유지) | - |

**주의**: 3B 이하 모델은 소설 품질이 매우 낮을 수 있음. 최소 7B 이상 강력 추천.

## 7. 리스크 및 완화 전략

- **토큰 비용 / 속도**: 로컬 Ollama 기준으로 단계별 호출 제한. 긴 본문은 청크 분할.
- **구조화 출력 실패**: Pydantic 파싱 + 재시도 로직 (최대 2회).
- **기존 테스트 파괴**: 항상 `mode="stub"`로 기본 동작 유지.
- **프롬프트 품질 관리**: 템플릿 버전 관리 + 샘플 출력 저장.
- **RAG 과도 주입**: search_scope + top_k 제한.

## 8. 구현 우선순위 및 마일스톤

- **M1 (빠른 가치)**: Step 1 + Step 2 + Step 3 → 실제 본문 1화 생성 가능
- **M2 (전체 흐름)**: Step 4 + Step 5 + Step 6
- **M3 (완성)**: Step 7 + Step 8 + 문서화

## 9. 참고 문서

- [novel_blueprint/10_prompts_contracts.md](../novel_blueprint/10_prompts_contracts.md)
- [novel_blueprint/05_agents.md](../novel_blueprint/05_agents.md)
- [novel_blueprint/02_architecture.md](../novel_blueprint/02_architecture.md)
- `packages/schemas/agent_schemas.py`
- `src/my_agent/database.py` (generation_runs, prompt_logs)
- `docs/usage_guide.md`
- `AGENTS.md` (Ollama embedding 규칙)

---

**이 계획에 따라 진행하면** 사용자는 다음과 같은 경험을 하게 된다:

1. LLM 설정 변경 → 실제 창의적 출력 생성
2. Story Build → 다양한 logline / arcs
3. Episode Build → 읽을 만한 산문 원고 확인
4. 검수 루프가 의미를 가짐

이 문서를 기반으로 Step 1부터 순차적으로 구현을 시작할 수 있다. 

필요 시 이 파일을 기반으로 더 세부적인 하위 스펙(예: SceneWriter 프롬프트 스펙)도 작성 가능하다.