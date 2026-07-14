# 소설 마이그레이션 및 다운로드 기능 구현 마이크로 플랜 (상세 실무 버전)

본 문서는 데이터베이스 마이그레이션(Export/Import)과 소설 문서 다운로드(Compile & Download) 기능의 실제 코딩을 위해 **파일명, 함수명, 상세 알고리즘 및 쿼리 시나리오**까지 쪼갠 실무 구현 계획서입니다.

---

## 📅 1. 개발 마일스톤 및 일정 계획

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Phase 1: Migration Core (3일)                                              │
│  ├─ Task 1.1: 스키마 설계 ➔ Task 1.2: Export API ➔ Task 1.3: Import Service  │
├─────────────────────────────────────────────────────────────────────────────┤
│  Phase 2: Document Compiler (4일)                                           │
│  ├─ Task 2.1: 컴파일 쿼리 ➔ Task 2.2: TXT/EPUB ➔ Task 2.3: PDF/DOCX (Executor)│
├─────────────────────────────────────────────────────────────────────────────┤
│  Phase 3: Integration & Test (2일)                                          │
│  ├─ Task 3.1: 마이그레이션 E2E 테스트 ➔ Task 3.2: 다운로드 E2E 검증           │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ 2. 단계별 상세 태스크 및 코드 구조 설계

### 🚀 Phase 1: 프로젝트 마이그레이션 (Export & Import)

이관 중에 발생하는 외래 키(FK) 관계 붕괴와 버전 트리(Self-referencing FK) 손실을 완벽히 방어합니다.

#### [ ] Task 1.1: 직렬화 Pydantic 스키마 정의
* **파일명**: `app/schemas/migration.py` (신규 생성)
* **상세 구현**:
  * 외부로 내보낼 데이터 구조를 정의하며, 가져오기 시 수신 측의 자동 생성 ID와 충돌하지 않도록 원래 ID를 별도 임시 필드로 취급합니다.
  ```python
  from pydantic import BaseModel
  from typing import List, Optional
  from datetime import datetime

  class ContentExportSchema(BaseModel):
      old_id: int  # parent_id 트리 구조 매핑 복원을 위해 보존
      old_parent_id: Optional[int]
      content_text: str
      author_type: str
      version_tag: str
      is_approved: bool
      created_at: datetime

  class EpisodeExportSchema(BaseModel):
      old_id: int
      episode_number: int
      title: str
      outline: Optional[str]
      created_at: datetime
      contents: List[ContentExportSchema]

  class CharacterExportSchema(BaseModel):
      name: str
      description: str
      importance: str

  class WorldSettingExportSchema(BaseModel):
      keyword: str
      category: str
      description: str
      embedding: Optional[List[float]] = None  # pgvector 임베딩 리스트 보존

  class ProjectExportSchema(BaseModel):
      title: str
      synopsis: Optional[str]
      llm_provider: str
      llm_model: str
      # 오버라이드 설정 필드들 생략...
      world_settings: List[WorldSettingExportSchema]
      characters: List[CharacterExportSchema]
      episodes: List[EpisodeExportSchema]
  ```

#### [ ] Task 1.2: Export 비동기 데이터 쿼리 및 API 구현
* **파일명**: `app/routers/projects.py` (또는 `app/routers/migration.py` 신규 생성 및 `main.py` 라우터 등록)
* **함수명**: `async def export_project(project_id: int, db: AsyncSession)`
* **상세 구현**:
  * N+1 조회 문제를 피하기 위해 SQLAlchemy `selectinload`를 적극적으로 활용합니다.
  ```python
  from sqlalchemy.orm import selectinload
  from sqlmodel import select

  stmt = (
      select(Project)
      .where(Project.id == project_id)
      .options(
          selectinload(Project.world_settings),
          selectinload(Project.characters),
          selectinload(Project.episodes).selectinload(Episode.contents)
      )
  )
  result = await db.execute(stmt)
  project = result.scalars().first()
  if not project:
      raise HTTPException(status_code=404, detail="Project not found")
  ```
  * 로드된 객체를 `ProjectExportSchema` 구조로 매핑하여 JSON 형태로 Response 리턴합니다.

#### [ ] Task 1.3: Import 서비스 알고리즘 구현
* **파일명**: `app/services/migration.py` (신규 생성)
* **함수명**: `async def import_project_data(user_id: int, data: ProjectExportSchema, db: AsyncSession) -> Project`
* **상세 구현 (관계성 복원 핵심 알고리즘)**:
  * 외래 키(FK) 제약조건에 저촉되지 않도록 아래 순서대로 실행하는 트랜잭션 함수를 구성합니다.
  1. **Project 레코드 생성**: 전달받은 설정값을 바탕으로 새 Project 객체를 만들고 `db.add(project)` 후 `await db.flush()`를 수행하여 새로운 `new_project_id`를 발급받습니다.
  2. **WorldSetting 및 Character 생성**: 새 `new_project_id`를 바인딩하여 순회 삽입합니다.
  3. **Episode 및 Content 생성 (트리 복원)**:
     * 각 에피소드를 삽입한 후 `episode_id_map: dict[int, int] = {}` (구 ID ➔ 신규 ID)에 매핑을 기록합니다.
     * Content의 경우, 생성 시간(`created_at`)을 기준으로 **오름차순 정렬**하여 순서대로 삽입합니다. (부모가 자식보다 항상 먼저 DB에 들어가야 하기 때문)
     * `content_id_map: dict[int, int] = {}` 사전을 관리하여 다음과 같이 `parent_id`를 복원합니다:
       ```python
       content_id_map = {}
       # created_at 정렬
       sorted_contents = sorted(episode_data.contents, key=lambda c: c.created_at)
       
       for c_data in sorted_contents:
           # parent_id 값 결정
           new_parent_id = None
           if c_data.old_parent_id:
               new_parent_id = content_id_map.get(c_data.old_parent_id)
               
           new_content = Content(
               episode_id=new_episode_id,
               parent_id=new_parent_id,
               content_text=c_data.content_text,
               author_type=c_data.author_type,
               version_tag=c_data.version_tag,
               is_approved=c_data.is_approved,
               created_at=c_data.created_at
           )
           db.add(new_content)
           await db.flush()  # new_content.id 획득
           content_id_map[c_data.old_id] = new_content.id
       ```

#### [ ] Task 1.4: Import API 엔드포인트 구현 및 트랜잭션 안전장치
* **파일명**: `app/routers/migration.py`
* **함수명**: `async def import_project(file: UploadFile = File(...), db: AsyncSession)`
* **상세 구현**:
  * 전체 가져오기 과정을 하나의 `async with db.begin():` 혹은 `db.begin_nested()` 블록 안에 가두어 예외 발생 시 인서트가 발생하기 전의 상태로 완전히 롤백되도록 안전장치를 설계합니다.
  * pgvector 지원 여부 검증: 가져오기 대상 서버의 DB가 `Vector` 데이터 타입을 지원하지 않는 경우, 캐치문을 통하여 임베딩 입력을 스킵 처리하고 `Warning` 로그만 남기도록 구현합니다.

---

### 📄 Phase 2: 소설 원고 다운로드 (Compile & Download)

에피소드별로 산재된 최종 승인 원고를 모아 출판 가능한 포맷으로 렌더링하고 스트리밍합니다.

#### [ ] Task 2.1: 컴파일 데이터 수집 및 Fallback 서비스 구현
* **파일명**: `app/services/compiler.py` (신규 생성)
* **함수명**: `async def compile_novel_draft(project_id: int, db: AsyncSession) -> List[dict]`
* **상세 구현**:
  1. 해당 프로젝트 하위의 모든 에피소드를 `episode_number` 오름차순으로 쿼리합니다.
  2. 에피소드 루프를 돌며 `Content.is_approved == True`인 데이터를 1차 탐색합니다.
  3. 만약 승인본이 없다면, 해당 에피소드 내에서 가장 최근 생성된 버전(`created_at.desc()`)을 강제 바인딩(Fallback)합니다.
  ```python
  # Fallback 쿼리
  stmt = (
      select(Content)
      .where(Content.episode_id == episode.id)
      .order_by(Content.created_at.desc())
      .limit(1)
  )
  fallback_content = (await db.execute(stmt)).scalar_one_or_none()
  ```
  4. 최종 결과를 `[{"episode_title": ep.title, "text": content.content_text}, ...]` 리스트로 정형화하여 반환합니다.

#### [ ] Task 2.2: TXT / EPUB 컴파일러 구현
* **파일명**: `app/services/compiler.py`
* **클래스명**: `class TxtCompiler`, `class EpubCompiler`
* **상세 구현**:
  * **TXT**: 각 에피소드 본문 사이에 `\n\n\n◆ ◆ ◆\n\n\n` 문양을 삽입하여 하나의 문자열 바이트 파일로 직렬화합니다.
  * **EPUB**: `ebooklib` 패키지를 연동하여 도서 정보(Title, Author)를 추가하고, 각 에피소드를 개별 HTML 파일 구조로 랩핑하여 추가합니다.
  ```python
  from ebooklib import epub

  book = epub.EpubBook()
  book.set_title(project.title)
  book.add_author(user.username)
  
  spine_list = ['nav']
  for idx, ep in enumerate(compiled_episodes):
      chapter = epub.EpubHtml(title=ep["episode_title"], file_name=f'chap_{idx}.xhtml', lang='ko')
      chapter.content = f'<h1>{ep["episode_title"]}</h1><p>{ep["text"].replace(chr(10), "<br/>")}</p>'
      book.add_item(chapter)
      spine_list.append(chapter)
      
  book.spine = spine_list
  # epub.write_epub(byte_stream_io)
  ```

#### [ ] Task 2.3: PDF / DOCX 컴파일러 구현
* **파일명**: `app/services/compiler.py`
* **클래스명**: `class PdfCompiler`, `class DocxCompiler`
* **상세 구현**:
  * **PDF (WeasyPrint)**: `app/templates/pdf_layout.html` 공통 템플릿(A4 여백 설정 및 CSS 페이지 넘버링 탑재)을 빌드하고 `weasyprint.HTML`로 PDF 파일 스트림을 렌더링합니다.
    ```css
    @page {
        size: A5;
        margin: 20mm 15mm 20mm 15mm;
        @bottom-center { content: counter(page); }
    }
    body { font-family: "KoPub Batang", serif; line-height: 1.8; text-align: justify; }
    ```
  * **DOCX (python-docx)**: 문단 들여쓰기(`first_line_indent = Pt(10)`), 줄간격 `1.6`, 챕터 구분 시 페이지 나누기(`doc.add_page_break()`) 속성을 반영하여 Word 바이너리를 생성합니다.

#### [ ] Task 2.4: 비동기 스레드 풀 격리 및 API 엔드포인트 구현
* **파일명**: `app/routers/projects.py`
* **함수명**: `async def download_novel(project_id: int, format: str = "txt")`
* **상세 구현**:
  * WeasyPrint, python-docx 및 EbookLib 처리는 CPU 바운드 연산이므로 메인 루프를 블로킹하지 않도록 비동기 스레드 풀에서 돌려 실행을 격리시킵니다.
  ```python
  import asyncio
  from concurrent.futures import ThreadPoolExecutor

  executor = ThreadPoolExecutor(max_workers=3)

  # 라우터 엔드포인트 내에서 백그라운드 호출
  loop = asyncio.get_running_loop()
  file_bytes = await loop.run_in_executor(
      executor, 
      compiler.generate_file_bytes, 
      format, 
      compiled_data
  )
  ```
  * 리턴된 바이트 파일을 `StreamingResponse(BytesIO(file_bytes), media_type=media_type)`로 내려보냅니다.

---

## 🧪 3. 테스트 코드 작성 및 검증 (E2E)

코딩 완료 후 수동 테스트에 의존하지 않고 단위 테스트 자동화로 동작을 최종 승인합니다.

#### [ ] Task 3.1: 마이그레이션 관계 보존 E2E 테스트
* **파일명**: `tests/test_migration.py`
* **테스트 케이스명**: `async def test_project_migration_flow_e2e(db_session: AsyncSession)`
* **검증 시나리오**:
  1. 모의(Mock) 프로젝트(Lore 2개, 캐릭터 2개, 에피소드 2개 및 상호 parent-child 관계를 맺은 Content 4개)를 DB에 셋업합니다.
  2. `export_project_data` 서비스를 실행하여 반환된 JSON을 검수합니다. (구 ID 보존 여부 확인)
  3. `import_project_data` 서비스를 실행하여 새 프로젝트 ID로 인서트합니다.
  4. 새로 등록된 Content들의 `parent_id` 값들이 DB에서 새로 갱신된 부모 Content ID들과 완벽하게 대칭 매칭되는지 `assert` 합니다.

#### [ ] Task 3.2: 다운로드 형식별 바이트 무결성 테스트
* **파일명**: `tests/test_download.py`
* **테스트 케이스명**: `async def test_download_all_formats_success(db_session: AsyncSession)`
* **검증 시나리오**:
  1. 가상의 테스트용 소설 텍스트 데이터를 구성합니다.
  2. `txt`, `epub`, `pdf`, `docx` 포맷의 API 다운로드 호출을 순차적으로 수행합니다.
  3. 반환된 헤더(`Content-Disposition`), 파일 스트림 크기가 0바이트 이상인지 검증하고 각 파일 유형의 헤더 시그니처 바이트를 대조합니다.
