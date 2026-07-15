# 리서치 에이전트 리팩토링 개발 계획서 및 타당성 평가 (Implementation Plan)

본 문서는 리서치 에이전트와 참고 자료(`ReferenceMaterial`) 저장소 기능을 실제로 안전하게 이식하기 위한 마이크로 플랜과 자체 구현 타당성 평가(Feasibility Assessment) 결과를 담고 있습니다.

---

## 🏗️ 1. 구현 타당성 평가 (Feasibility Assessment)

개발에 착수하기 전, 아키텍처 및 소스 코드 복잡도 분석을 통해 기술적 실행 가능성을 자가 채점합니다.

| 검증 항목 | 난이도 | 리스크 요인 | 극복 방안 | 점수 (10점 만점) |
| :--- | :--- | :--- | :--- | :--- |
| **DB 모델 추가** | 하 | 테이블 단독 추가로 기존 스키마 깨짐 현상 없음 | alembic 자동 생성 또는 init_db 기동 시 자동 DDL 생성 연동 | 10 / 10 |
| **API Endpoints 구현** | 중하 | 페이징 및 필터링 등 기존 템플릿 코드 재활용 가능 | FastAPI APIRouter 구조 내에 `references` 라우터 신설 | 9.5 / 10 |
| **LangGraph 리서치 노드** | 중 | 외부 검색 API(Tavily 등) 키 부재 시 대체 로직 필요 | Tavily/Google API 호출 코드를 작성하되, Key 부재 시 자체 백업 LLM 지식 기반 Mocking 리서치 기능 하이브리드 설계 | 8.5 / 10 |
| **집필 연계 (Context RAG)** | 중 | 기존 프롬프트 파싱 로직과의 충돌 위험 | 기존 Episode 작성 프롬프트 템플릿의 끝부분에 Optional 참고자료 섹션만 변수로 공급하여 사이드이펙트 최소화 | 9.0 / 10 |

* **종합 평가 결과**: **실무 구현 즉시 가능 (FEASIBLE)**
* **평가 근거**: 기존 DB 구조와 에이전트 그래프를 파괴하지 않고 추가 독립 노드 및 테이블 형태로 꼽아 넣는(Add-on) 아키텍처이므로 안정성이 극히 높음.

---

## 📅 2. 마이크로 개발 계획 (Micro Plan)

### 📅 Phase 1: DB 스키마 추가 및 마이그레이션
* **목표**: `ReferenceMaterial` 모델 정의 및 `Project` 일대다 관계 연동.
1. `app/models.py` 파일의 하단부에 `ReferenceMaterial` 클래스 스펙 추가.
2. `Project` 클래스 내부에 `reference_materials` 관계 필드 정의.
3. 로컬 DB 리셋/마이그레이션 스크립트를 돌려 테이블 구조 갱신.

### 📅 Phase 2: 참고 자료 관리 API 구현 (`references.py` 신설)
* **목표**: 참고 문헌 등록, 조회, 삭제 CRUD API 제공.
1. `app/routers/references.py` 생성.
2. `GET /projects/{id}/references` (조회/검색)
3. `POST /projects/{id}/references` (수동 등록)
4. `DELETE /projects/{id}/references/{ref_id}` (삭제)
5. `app/main.py`에 이 라우터 신규 등록.

### 📅 Phase 3: 리서치 에이전트(Researcher) 그래프 구축
* **목표**: 검색 툴을 이용해 고증 정보를 수집하고 가독성 높은 보고서로 팩킹하여 DB에 적재하는 백그라운드 태스크 구현.
1. `app/services/researcher.py` 생성: LangGraph 엔진 연동.
2. `POST /projects/{id}/references/research` 엔드포인트 구현: 비동기 BackgroundTasks로 리서치 에이전트 트리거 구동.
3. 툴 연동: 웹 검색 API 가용성 체크 및 요약 프롬프트 프레임워크 작성.

### 📅 Phase 4: 집필 프롬프트(RAG) 연동 및 E2E 검증
* **목표**: 실제 에피소드 작성 시 참고 자료가 자동으로 컨텍스트에 덧붙여지도록 에이전트 결합 및 E2E 테스트 검증.
1. `app/services/writer.py` (또는 집필 에이전트의 노드 코드)를 조회하여 프롬프트 빌더에 `reference_materials` 목록 조회를 임포트해 주입.
2. `tests/test_research.py` E2E 테스트 생성 및 팩트 체크 검증 수행.
3. 프론트엔드 UI 관리 화면 구현 (참고자료 목록 조회/수동추가/리서치 요청 바인딩).
