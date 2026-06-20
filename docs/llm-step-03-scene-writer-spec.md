# Step 3: SceneWriterAgent LLM화 — 상세 작업 사양서 (최우선)

## 1. 목적
이 단계가 끝나면 **실제로 읽을 수 있는 소설 본문**이 생성된다. 전체 프로젝트에서 사용자 가치가 가장 큰 단계.

## 2. 선행 조건
- Step 1: LLMFactory + LLMClient 완성
- Step 2: PromptLoader + scene_writer_v1.md 완성

## 3. 변경 대상 파일

### 3.1 packages/agents/scene_writer_agent.py
- `__init__`에 `llm_client: LLMClient | None = None` 추가
- `__post_init__`에서 `llm_client` 설정
- `_build_draft_text` 메서드 리팩토링 또는 대체
- 새 메서드: `_generate_with_llm(self, payload) -> str`

주요 변경 포인트:

```python
@dataclass(slots=True)
class SceneWriterAgent:
    ...
    llm_client: Any = field(default=None)   # LLMClient

    def run(self, payload: SceneWriterInput) -> SceneWriterOutput:
        ...
        if self.llm_client and self.llm_client != "stub":
            draft_text = self._generate_with_llm(payload)
        else:
            draft_text = self._build_draft_text(payload)  # 기존 스텁 유지
        ...
```

### 3.2 _generate_with_llm 구현 스케치
```python
def _generate_with_llm(self, payload):
    context = load_scoped_documents(...)  # 기존 RAG
    prompt = self.prompt_loader.render(
        "episode/scene_writer_v1",
        episode_card=payload.episode_card,
        scene_beats=payload.scene_beats,
        retrieved_context=...
    )
    
    result = self.llm_client.generate_structured(
        prompt=prompt,
        output_schema=SceneWriterOutput,   # 또는 내부 DraftOutput 스키마
    )
    return result.draft_text
```

### 3.3 기존 _build_draft_text는 스텁 fallback으로 남겨둔다.

## 4. 스키마 활용
- `packages/schemas/agent_schemas.py`의 `SceneWriterOutput`를 최대한 재사용
- 필요시 `DraftTextOutput` 같은 내부 스키마 추가 고려

## 5. 생성 로깅 (Step 6과 연계)
- LLM 호출 직후 간단히 `repository`에 raw_output과 parsed 결과를 기록할 수 있는 hook 준비
- (Step 6에서 본격 구현)

## 6. 수용 기준 (강력 체크)
- [ ] `LLMFactory(mode="stub")` 사용 시 기존과 100% 동일한 동작
- [ ] `LLMFactory(mode="ollama")` 사용 시 `draft_text`가 600자 이상의 자연스러운 한국어 산문
- [ ] 생성된 텍스트가 scene_beats의 objective/conflict/outcome을 반영
- [ ] 상위 arc/premise를 무시하는 경우가 거의 없음 (writer_warning으로 보고)
- [ ] episode_to_draft 워크플로우 전체 실행 성공
- [ ] Admin Console "Episode Build"에서 `st.markdown`으로 예쁘게 보임

## 7. 검증 방법
1. bootstrap으로 novel 생성
2. theme_to_arcs 실행
3. 특정 화 선택 후 episode_to_draft 실행 (LLM 모드)
4. 생성된 draft_text를 직접 읽어보기
5. 스텁 모드와 비교

## 8. 리스크
- 구조화 출력 파싱 실패 → 재시도 로직 구현
- 너무 긴 응답 → max_tokens 및 청크 전략 (MVP에서는 1회 호출로 제한)

## 9. 산출물
- 수정된 `scene_writer_agent.py`
- 개선된 `prompts/episode/scene_writer_v1.md`
- Step 3 완료 후 실행 예시 (텍스트 파일 또는 스크린샷)

**이 단계 완료 시 M1 달성** — 사용자가 "실제로 쓴 소설"을 볼 수 있게 된다.