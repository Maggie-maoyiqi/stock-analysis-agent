"""内存任务管理器。"""
import asyncio
from datetime import datetime
from typing import Dict
from uuid import uuid4

from src.services.analysis_service import build_initial_state, run_analysis_workflow


class AnalysisTaskManager:
    """管理分析任务的生命周期。"""

    def __init__(self):
        self.tasks: Dict[str, dict] = {}

    def create_task(self, query: str) -> dict:
        """创建后台分析任务。"""
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
            "created_at": now,
            "updated_at": now,
            "execution_time": None,
        }
        self.tasks[task_id] = record
        asyncio.create_task(self._run_task(task_id, query))
        return record

    async def _run_task(self, task_id: str, query: str):
        """执行后台任务。"""
        record = self.tasks[task_id]
        record["status"] = "running"
        record["progress_percent"] = 5.0
        record["updated_at"] = datetime.utcnow().isoformat()
        try:
            async def progress_callback(step: str, status: str, progress: float, message: str = ""):
                if step in record["step_statuses"]:
                    record["step_statuses"][step] = status
                if step in record.get("step_progresses", {}):
                    record["step_progresses"][step] = round(progress * 100, 1)
                if step in record.get("step_messages", {}):
                    record["step_messages"][step] = message or record["step_messages"][step]
                record["progress_percent"] = round(progress * 100, 1)
                record["updated_at"] = datetime.utcnow().isoformat()

            final_state = await run_analysis_workflow(query, progress_callback=progress_callback)
            record.update(
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
                    "progress_percent": 100.0,
                    "updated_at": datetime.utcnow().isoformat(),
                }
            )
        except Exception as exc:
            record.update(
                {
                    "status": "failed",
                    "error": str(exc),
                    "progress_percent": record.get("progress_percent", 0.0),
                    "updated_at": datetime.utcnow().isoformat(),
                }
            )

    def get_task(self, task_id: str) -> dict | None:
        """查询任务。"""
        return self.tasks.get(task_id)


task_manager = AnalysisTaskManager()
