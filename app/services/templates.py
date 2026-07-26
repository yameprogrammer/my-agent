"""IDEA-19: 장르별 템플릿 프로젝트 스켈레톤."""
from __future__ import annotations

from typing import Dict, List

TEMPLATES: Dict[str, dict] = {
    "fantasy": {
        "title": "새 판타지 연재",
        "synopsis": "평범한 주인공이 숨겨진 마력의 각성을 계기로 왕국을 뒤흔드는 음모에 휘말린다.",
        "characters": [
            {"name": "주인공", "importance": "protagonist", "description": "평범한 일상에서 벗어나 각성하는 인물. 내적 갈등과 성장 욕구가 핵심."},
            {"name": "멘토", "importance": "major", "description": "주인공을 인도하지만 숨긴 사정이 있는 조력자."},
            {"name": "라이벌", "importance": "major", "description": "주인공과 대척점에 선 인물. 목표는 유사하나 수단이 다르다."},
        ],
        "lores": [
            {"keyword": "마력 체계", "category": "concept", "description": "세상에는 원소 마력이 흐르며, 각성자는 계약 없이 제한된 권능을 쓴다."},
            {"keyword": "왕도", "category": "location", "description": "정치와 마탑이 공존하는 중심 도시."},
        ],
        "episodes": [
            {"episode_number": 1, "title": "각성의 징조", "outline": "일상 붕괴와 첫 각성 사건."},
            {"episode_number": 2, "title": "선택의 갈림길", "outline": "멘토를 만나고 첫 목표를 정한다."},
        ],
    },
    "romance": {
        "title": "새 로맨스 연재",
        "synopsis": "엇갈린 인연을 가진 두 사람이 다시 만나 상처와 비밀을 마주한다.",
        "characters": [
            {"name": "히로인", "importance": "protagonist", "description": "자기 방어가 강하고 일과 감정을 분리하려는 인물."},
            {"name": "히어로", "importance": "deuteragonist", "description": "과거를 숨긴 채 다가오는 상대."},
        ],
        "lores": [
            {"keyword": "카페 라비앙", "category": "location", "description": "두 사람이 처음 재회하는 동네 카페."},
        ],
        "episodes": [
            {"episode_number": 1, "title": "우연한 재회", "outline": "일상의 균열과 재회 훅."},
        ],
    },
    "modern_action": {
        "title": "새 현대 액션",
        "synopsis": "지하 조직과 공권력이 뒤얽힌 도시에서 주인공이 복수를 계획한다.",
        "characters": [
            {"name": "주인공", "importance": "protagonist", "description": "냉정한 실행력, 그러나 남은 인간성."},
            {"name": "정보원", "importance": "major", "description": "이중 스파이 가능성을 품은 조력자."},
        ],
        "lores": [
            {"keyword": "지하 경매장", "category": "location", "description": "불법 거래가 이루어지는 은밀한 공간."},
        ],
        "episodes": [
            {"episode_number": 1, "title": "계약", "outline": "첫 임무와 배신 암시."},
        ],
    },
}


def list_template_ids() -> List[dict]:
    return [
        {"id": k, "title": v["title"], "synopsis": v["synopsis"][:120]}
        for k, v in TEMPLATES.items()
    ]


def get_template(template_id: str) -> dict:
    key = (template_id or "").lower().strip()
    if key not in TEMPLATES:
        raise KeyError(template_id)
    return TEMPLATES[key]
