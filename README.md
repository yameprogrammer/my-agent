# AI 장편 웹소설 제작 운영 시스템

Phase 1은 프로젝트 뼈대, SQLite DB 스키마, 도메인 모델, Pydantic 계약, 메모리 저장소 기본 CRUD를 제공한다.

## 핵심 범위

- multi-project 지원: 모든 핵심 엔터티에 `novel_id` 포함
- 승인 정책: `config/approval_policy.json`에서 자동/수동 비율 조정
- 메모리 저장소: SQLite + 로컬 임베딩 MVP, 이후 pgvector/Qdrant로 교체 가능
- 목표 장르: 판타지, 회귀/성장형

## 실행

```bash
python main.py --init-db
pytest
```

## 구현 제외

- API 엔드포인트
- AI 에이전트
- 검증 로직
- UI

## 참고

- 기본 임베딩 모델: `sentence-transformers/all-MiniLM-L6-v2`
- 벡터 저장소는 `sqlite-vec`를 우선 시도하고, 실패 시 Python 폴백을 사용한다.
