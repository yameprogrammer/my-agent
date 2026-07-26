"""IDEA-11/12: 에이전트 호출 관측 — 프롬프트 전문 없이 해시·대략 토큰."""
from __future__ import annotations

import hashlib
import logging
import time
from contextlib import asynccontextmanager
from typing import Optional

from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import async_session_factory
from app.models import AgentUsageLog

logger = logging.getLogger(__name__)


def estimate_tokens(text: str) -> int:
    """한글·영문 혼합 대략치: 문자수 / 2.5 (과대 추정 방지용 휴리스틱)."""
    if not text:
        return 0
    return max(1, int(len(text) / 2.5))


def prompt_hash(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()[:16]


async def record_usage(
    *,
    project_id: int,
    agent_role: str,
    episode_id: Optional[int] = None,
    model_name: Optional[str] = None,
    provider: Optional[str] = None,
    latency_ms: int = 0,
    input_text: str = "",
    output_text: str = "",
    success: bool = True,
    error_message: Optional[str] = None,
) -> None:
    try:
        async with async_session_factory() as session:
            row = AgentUsageLog(
                project_id=project_id,
                episode_id=episode_id,
                agent_role=agent_role,
                model_name=model_name,
                provider=provider,
                latency_ms=latency_ms,
                prompt_hash=prompt_hash(input_text) if input_text else None,
                input_chars=len(input_text or ""),
                output_chars=len(output_text or ""),
                est_input_tokens=estimate_tokens(input_text),
                est_output_tokens=estimate_tokens(output_text),
                success=success,
                error_message=(error_message or "")[:500] or None,
            )
            session.add(row)
            await session.commit()
    except Exception as e:
        logger.debug("usage log skipped: %s", e)


@asynccontextmanager
async def track_agent_call(
    *,
    project_id: int,
    agent_role: str,
    episode_id: Optional[int] = None,
    model_name: Optional[str] = None,
    provider: Optional[str] = None,
    input_text: str = "",
):
    """with 블록: yield 콜백 set_output; 종료 시 로그."""
    t0 = time.perf_counter()
    box = {"output": "", "success": True, "error": None}

    class _Tracker:
        def set_output(self, text: str):
            box["output"] = text or ""

        def fail(self, err: str):
            box["success"] = False
            box["error"] = err

    tracker = _Tracker()
    try:
        yield tracker
    except Exception as e:
        box["success"] = False
        box["error"] = str(e)
        raise
    finally:
        ms = int((time.perf_counter() - t0) * 1000)
        await record_usage(
            project_id=project_id,
            agent_role=agent_role,
            episode_id=episode_id,
            model_name=model_name,
            provider=provider,
            latency_ms=ms,
            input_text=input_text,
            output_text=box["output"],
            success=box["success"],
            error_message=box["error"],
        )
