# AI 장편 웹소설 제작 운영 시스템

Phase 1은 프로젝트 뼈대, SQLite DB 스키마, 도메인 모델, Pydantic 계약, 메모리 저장소 기본 CRUD를 제공한다.

## 핵심 범위

- multi-project 지원: 모든 핵심 엔터티에 `novel_id` 포함
- 승인 정책: `config/approval_policy.json`에서 자동/수동 비율 조정
- 메모리 저장소: SQLite + 로컬 임베딩 MVP, 이후 pgvector/Qdrant로 교체 가능
- 목표 장르: 판타지, 회귀/성장형

## 사용 가이드

설치 이후 실행·워크플로우·Admin Console 사용법은 [docs/usage_guide.md](docs/usage_guide.md)를 참고한다.

## 원터치 실행

환경 설정부터 Admin Console 기동까지 한 번에:

```powershell
# Windows — 더블클릭 가능
.\scripts\run.bat
# 또는
.\scripts\run.ps1
```

```bash
# Linux / macOS
chmod +x scripts/run.sh
./scripts/run.sh
```

개별 명령: `setup`, `init-db`, `bootstrap`, `test`, `admin`, `help`

## 환경 설정

Python **3.11 이상**이 필요하다 (3.12, 3.13 등 상위 버전도 사용 가능). `pyproject.toml`의 `requires-python = ">=3.11"`이 기준이다. 프로젝트 루트에서 가상환경을 생성하고 의존성을 설치한다.

**Windows (PowerShell)**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
```

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
```

또는 `scripts/setup.ps1` (Windows) / `scripts/setup.sh` (Unix) 로 한 번에 설정할 수 있다.

## 실행

가상환경을 활성화한 뒤, 프로젝트 루트에서 실행한다.

```bash
python main.py --init-db
pytest
```

**Admin Console (Streamlit)**

```bash
streamlit run apps/admin/main.py
```

또는 `.\scripts\run.bat` / `./scripts/run.sh` (권장)

## 구현 제외

- API 엔드포인트
- AI 에이전트
- 검증 로직
- UI

## 참고

- 기본 임베딩 모델: `sentence-transformers/all-MiniLM-L6-v2`
- 벡터 저장소는 `sqlite-vec`를 우선 시도하고, 실패 시 Python 폴백을 사용한다.
- Ollama 임베딩은 `config/embedding_config.json`에서 설정한다.