"""
IDEA-21: agents package — public API re-exported from role modules.

현재 본문은 _monolith 에 유지하고, 역할별 분리 진입점은 이 패키지를 통해 제공.
from app.services.agents import PlotterAgent 등 기존 import 경로 호환.
"""
from app.services.agents._monolith import *  # noqa: F401,F403
from app.services.agents import _monolith as _m

__all__ = [name for name in dir(_m) if not name.startswith("_")]
