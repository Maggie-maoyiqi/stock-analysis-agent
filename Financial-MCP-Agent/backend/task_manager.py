"""Persistent task manager with SSE subscriptions."""
from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Any, AsyncIterator, Dict
from uuid import uuid4

from backend.storage import create_task_record, get_task_record, update_task_record
from src.services.analysis_service import build_initial_state, run_analysis_workflow


class AnalysisTaskManager:
    """Manage background analysis tasks and push updates to SSE subscribers."""

    def __init__(self):
        self.subscribers: Dict[str, set[asyncio.Queue[str]]] = {}

    def create_task(self, query: str) -> dict:
        """Create a background analysis task."""
        task_id = uuid4().hex
        state = build_initial_state(query)
        now = datetime.utcnow().isoformat()
        record = {
            "task_id": task_id,
            "status": "queued",
            "query": query,
            "stock_code": state["stock_code"],
            "stock_name": state["stock_name"],
            "final_report": None,
            "report_file": None,
            "fundamental_analysis": None,
            "technical_analysis": None,
            "value_analysis": None,
            "news_analysis": None,
            "forecast_analysis": None,
            "error": None,
            "progress_percent": 0.0,
            "step_statuses": {
                "fundamental": "pending",
                "technical": "pending",
                "value": "pending",
                "news": "pending",
                "forecast": "pending",
                "summary": "pending",
            },
            "step_progresses": {
                "fundamental": 0.0,
                "technical": 0.0,
                "value": 0.0,
                "news": 0.0,
                "forecast": 0.0,
                "summary": 0.0,
            },
            "step_messages": {
                "fundamental": "等待开始",
                "technical": "等待开始",
                "value": "等待开始",
                "news": "等待开始",
                "forecast": "等待开始",
                "summary": "等待开始",
            },
            "charts": [],
            "created_at": now,
            "updated_at": now,
            "execution_time": None,
        }
        create_task_record(record)
        asyncio.create_task(self._run_task(task_id, query))
        return record

    async def _publish(self, task_id: str, record: Dict[str, Any]) -> None:
        payload = json.dumps(record, ensure_ascii=False)
        for queue in list(self.subscribers.get(task_id, set())):
            await queue.put(payload)

    async def _run_task(self, task_id: str, query: str):
        """Execute the background task."""
        record = update_task_record(
            task_id,
            {
                "status": "running",
                "progress_percent": 5.0,
                "updated_at": datetime.utcnow().isoformat(),
            },
        )
        await self._publish(task_id, record)
        try:

            async def progress_callback(step: str, status: str, progress: float, message: str = ""):
                current = get_task_record(task_id) or {}
                if step in current.get("step_statuses", {}):
                    current["step_statuses"][step] = status
                if step in current.get("step_progresses", {}):
                    current["step_progresses"][step] = round(progress * 100, 1)
                if step in current.get("step_messages", {}):
                    current["step_messages"][step] = message or current["step_messages"][step]
                if step == "workflow":
                    current["progress_percent"] = round(progress * 100, 1)
                current["updated_at"] = datetime.utcnow().isoformat()
                updated = update_task_record(
                    task_id,
                    {
                        "step_statuses": current.get("step_statuses", {}),
                        "step_progresses": current.get("step_progresses", {}),
                        "step_messages": current.get("step_messages", {}),
                        "progress_percent": current["progress_percent"],
                        "updated_at": current["updated_at"],
                    },
                )
                await self._publish(task_id, updated)

            final_state = await run_analysis_workflow(query, progress_callback=progress_callback)
            current = get_task_record(task_id) or {}
            final_report = final_state.get("final_report") or ""
            summary_failed = str(final_report).startswith("报告生成失败")
            step_statuses = current.get("step_statuses", {}).copy()
            step_progresses = current.get("step_progresses", {}).copy()
            step_messages = current.get("step_messages", {}).copy()
            for step_key in ["fundamental", "technical", "value", "news", "forecast"]:
                if step_statuses.get(step_key) != "failed":
                    step_statuses[step_key] = "completed"
                    step_progresses[step_key] = 100.0
                    step_messages[step_key] = "已完成"
            step_statuses["summary"] = "failed" if summary_failed else "completed"
            step_progresses["summary"] = 95.0 if summary_failed else 100.0
            step_messages["summary"] = "执行失败" if summary_failed else "综合报告已完成"
            updated = update_task_record(
                task_id,
                {
                    "status": "completed",
                    "stock_code": final_state.get("stock_code"),
                    "stock_name": final_state.get("stock_name"),
                    "final_report": final_state.get("final_report"),
                    "report_file": final_state.get("report_file"),
                    "fundamental_analysis": final_state.get("fundamental_analysis"),
                    "technical_analysis": final_state.get("technical_analysis"),
                    "value_analysis": final_state.get("value_analysis"),
                    "news_analysis": final_state.get("news_analysis"),
                    "forecast_analysis": final_state.get("forecast_analysis"),
                    "execution_time": final_state.get("execution_time"),
                    "charts": final_state.get("charts", []),
                    "progress_percent": 100.0,
                    "step_statuses": step_statuses,
                    "step_progresses": step_progresses,
                    "step_messages": step_messages,
                    "updated_at": datetime.utcnow().isoformat(),
                },
            )
            await self._publish(task_id, updated)
        except Exception as exc:
            updated = update_task_record(
                task_id,
                {
                    "status": "failed",
                    "error": str(exc),
                    "updated_at": datetime.utcnow().isoformat(),
                },
            )
            await self._publish(task_id, updated)

    def get_task(self, task_id: str) -> dict | None:
        """Get a task by id."""
        return get_task_record(task_id)

    async def stream(self, task_id: str) -> AsyncIterator[str]:
        """Yield task updates as SSE frames."""
        queue: asyncio.Queue[str] = asyncio.Queue()
        self.subscribers.setdefault(task_id, set()).add(queue)
        initial = self.get_task(task_id)
        if initial:
            yield f"event: task\ndata: {json.dumps(initial, ensure_ascii=False)}\n\n"
        try:
            while True:
                try:
                    payload = await asyncio.wait_for(queue.get(), timeout=15)
                    yield f"event: task\ndata: {payload}\n\n"
                    record = json.loads(payload)
                    if record.get("status") in {"completed", "failed"}:
                        break
                except asyncio.TimeoutError:
                    yield "event: ping\ndata: keep-alive\n\n"
        finally:
            self.subscribers.get(task_id, set()).discard(queue)


task_manager = AnalysisTaskManager()
