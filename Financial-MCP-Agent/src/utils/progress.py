"""Progress helpers used by individual analysis agents.

The agents have long phases (MCP tool calls and LLM generation) where no
discrete checkpoint can fire. ``run_with_heartbeat`` wraps such a coroutine
and emits smoothly advancing progress updates while it runs, asymptotically
approaching but never reaching the next checkpoint until the work finishes.
"""
from __future__ import annotations

import asyncio
import math
import time
from typing import Any, Awaitable, Callable, Coroutine, TypeVar

T = TypeVar("T")

NotifyCallable = Callable[[str, float], Any]


async def _emit(notify: NotifyCallable, message: str, progress: float) -> None:
    """Call the agent's ``notify`` and await it if it returned a coroutine."""
    result = notify(message, progress)
    if asyncio.iscoroutine(result):
        await result


async def run_with_heartbeat(
    coro: Coroutine[Any, Any, T] | Awaitable[T],
    notify: NotifyCallable,
    *,
    message: str,
    start: float,
    end: float,
    expected_seconds: float,
    interval: float = 0.5,
    cap_ratio: float = 0.95,
) -> T:
    """Run ``coro`` while smoothly advancing progress from ``start`` toward ``end``.

    The progress curve follows ``1 - exp(-t / tau)`` where ``tau`` is
    derived from ``expected_seconds``, so it always increases but never
    crosses ``end`` until the work itself completes (we then jump to ``end``
    on the caller side via the next checkpoint).

    Parameters
    ----------
    coro: the awaitable representing the actual work (tool call / LLM call)
    notify: ``async def notify(stage: str, progress: float)`` style callable
    message: text shown alongside the progress bar
    start, end: progress range (0.0 - 1.0) to occupy during this phase
    expected_seconds: roughly how long this phase normally takes; controls
        the easing curve
    interval: heartbeat tick interval in seconds
    cap_ratio: maximum fraction of the (start, end) span we are allowed to
        reach via the heartbeat itself; ensures the bar never *visually*
        finishes before the underlying work does.
    """
    task: asyncio.Task[T] = asyncio.ensure_future(coro)  # type: ignore[arg-type]
    started = time.monotonic()
    tau = max(expected_seconds, 1.0)
    span = max(end - start, 0.0)

    # Emit the floor immediately so the bar moves the moment we enter this phase.
    await _emit(notify, message, start)

    try:
        while True:
            done, _ = await asyncio.wait({task}, timeout=interval)
            if task in done:
                break
            elapsed = time.monotonic() - started
            ratio = 1.0 - math.exp(-elapsed / tau)
            target = start + span * min(cap_ratio, ratio)
            await _emit(notify, message, target)
        return await task
    except BaseException:
        if not task.done():
            task.cancel()
            try:
                await task
            except BaseException:
                pass
        raise
