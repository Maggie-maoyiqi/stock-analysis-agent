"""LangGraph workflow for multi-agent stock analysis."""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, Dict

from langgraph.graph import END, START, StateGraph

from ..agents import (
    fundamental_agent,
    forecast_agent,
    news_agent,
    summary_agent,
    technical_agent,
    value_agent,
)
from ..utils.state_definition import AgentState

ProgressCallback = Callable[[str, str, float, str], Awaitable[None] | None]


def build_analysis_graph(progress_callback: ProgressCallback | None = None):
    """Build the analysis graph with parallel specialist agents."""
    graph = StateGraph(AgentState)

    async def run_specialist(step_key: str, func, state: AgentState) -> Dict[str, Any]:
        async def child_progress_callback(_: str, message: str, local_progress: float):
            if progress_callback:
                maybe_awaitable = progress_callback(step_key, "running", local_progress, message)
                if maybe_awaitable is not None:
                    await maybe_awaitable

        if progress_callback:
            maybe_awaitable = progress_callback(step_key, "running", 0.02, "等待调度")
            if maybe_awaitable is not None:
                await maybe_awaitable

        result = await func(state, progress_callback=child_progress_callback)
        if progress_callback:
            field_name = {
                "fundamental": "fundamental_analysis",
                "technical": "technical_analysis",
                "value": "value_analysis",
                "news": "news_analysis",
                "forecast": "forecast_analysis",
            }[step_key]
            failed = str(result.get(field_name, "")).startswith("分析失败")
            maybe_awaitable = progress_callback(
                step_key,
                "failed" if failed else "completed",
                0.95 if failed else 1.0,
                "执行失败" if failed else "已完成",
            )
            if maybe_awaitable is not None:
                await maybe_awaitable
        return result

    async def run_summary(state: AgentState) -> Dict[str, Any]:
        async def child_progress_callback(_: str, message: str, local_progress: float):
            if progress_callback:
                maybe_awaitable = progress_callback("summary", "running", local_progress, message)
                if maybe_awaitable is not None:
                    await maybe_awaitable

        if progress_callback:
            maybe_awaitable = progress_callback("summary", "running", 0.05, "等待汇总")
            if maybe_awaitable is not None:
                await maybe_awaitable

        result = await summary_agent(state, progress_callback=child_progress_callback)
        if progress_callback:
            failed = str(result.get("final_report", "")).startswith("报告生成失败")
            maybe_awaitable = progress_callback(
                "summary",
                "failed" if failed else "completed",
                0.95 if failed else 1.0,
                "执行失败" if failed else "综合报告已完成",
            )
            if maybe_awaitable is not None:
                await maybe_awaitable
        return result

    graph.add_node("fundamental", lambda state: run_specialist("fundamental", fundamental_agent, state))
    graph.add_node("technical", lambda state: run_specialist("technical", technical_agent, state))
    graph.add_node("value", lambda state: run_specialist("value", value_agent, state))
    graph.add_node("news", lambda state: run_specialist("news", news_agent, state))
    graph.add_node("forecast", lambda state: run_specialist("forecast", forecast_agent, state))
    graph.add_node("summary", run_summary)

    for node_name in ["fundamental", "technical", "value", "news", "forecast"]:
        graph.add_edge(START, node_name)
    graph.add_edge(["fundamental", "technical", "value", "news", "forecast"], "summary")
    graph.add_edge("summary", END)
    return graph.compile()
