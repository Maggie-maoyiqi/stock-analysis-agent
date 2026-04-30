"""可复用的股票分析工作流服务。"""
import asyncio
import time
from datetime import datetime
from typing import Optional, Tuple
import re

from ..agents import (
    fundamental_agent,
    forecast_agent,
    news_agent,
    summary_agent,
    technical_agent,
    value_agent,
)
from ..utils.logging_config import ERROR_ICON, SUCCESS_ICON, setup_logger
from ..utils.state_definition import AgentState

logger = setup_logger(__name__)


def extract_stock_info(query: str) -> Tuple[Optional[str], Optional[str]]:
    """从用户查询中提取股票代码和公司名。"""
    stock_map = {
        "茅台": ("sh.600519", "贵州茅台"),
        "贵州茅台": ("sh.600519", "贵州茅台"),
        "宁德时代": ("sz.300750", "宁德时代"),
        "比亚迪": ("sz.002594", "比亚迪"),
        "招商银行": ("sh.600036", "招商银行"),
        "中国平安": ("sh.601318", "中国平安"),
        "腾讯": ("00700.HK", "腾讯控股"),
        "阿里巴巴": ("BABA", "阿里巴巴"),
        "苹果": ("AAPL", "Apple"),
        "特斯拉": ("TSLA", "Tesla"),
        "英伟达": ("NVDA", "NVIDIA"),
    }

    for name, (code, full_name) in stock_map.items():
        if name in query:
            return code, full_name

    hk_match = re.search(r"\b(\d{4,5}\.HK)\b", query, re.IGNORECASE)
    if hk_match:
        code = hk_match.group(1).upper()
        return code, f"港股{code}"

    us_match = re.search(r"\b([A-Z]{1,5})\b", query)
    if us_match:
        code = us_match.group(1).upper()
        if code not in {"HK", "SH", "SZ"}:
            return code, code

    match = re.search(r"(\d{6})", query)
    if match:
        code_num = match.group(1)
        if code_num.startswith("6"):
            code = f"sh.{code_num}"
        elif code_num.startswith(("0", "3")):
            code = f"sz.{code_num}"
        else:
            code = f"sh.{code_num}"
        return code, f"股票{code_num}"

    hk_digits = re.search(r"\b(\d{4,5})\b", query)
    if hk_digits and any(keyword in query for keyword in ["港股", "H股", "hk", "HK"]):
        code = f"{hk_digits.group(1)[-4:].zfill(4)}.HK"
        return code, f"港股{code}"

    return "sh.600519", "贵州茅台"


def build_initial_state(query: str) -> AgentState:
    """创建分析初始状态。"""
    stock_code, stock_name = extract_stock_info(query)
    return {
        "user_query": query,
        "stock_code": stock_code or "",
        "stock_name": stock_name or "",
        "fundamental_analysis": "",
        "technical_analysis": "",
        "value_analysis": "",
        "news_analysis": "",
        "forecast_analysis": "",
        "final_report": "",
        "report_file": "",
        "current_date": datetime.now().strftime("%Y-%m-%d"),
        "execution_time": 0.0,
        "errors": [],
    }


async def run_analysis_workflow(query: str, progress_callback=None) -> AgentState:
    """执行完整分析工作流并返回最终状态。"""
    logger.info("%s 开始分析: %s", SUCCESS_ICON, query)
    start_time = time.time()

    initial_state = build_initial_state(query)
    logger.info("识别到股票: %s (%s)", initial_state["stock_name"], initial_state["stock_code"])

    state: AgentState = initial_state.copy()

    async def notify(step: str, status: str, progress: float, message: str = ""):
        if progress_callback:
            maybe_awaitable = progress_callback(step, status, progress, message)
            if asyncio.iscoroutine(maybe_awaitable):
                await maybe_awaitable

    async def run_step(step_key: str, func):
        await notify(step_key, "running", 0.02, "等待调度")

        async def step_progress_callback(_: str, message: str, local_progress: float):
            workflow_progress = min(0.79, 0.1 + sum(1 for candidate, _ in parallel_steps if state.get(
                {
                    "fundamental": "fundamental_analysis",
                    "technical": "technical_analysis",
                    "value": "value_analysis",
                    "news": "news_analysis",
                    "forecast": "forecast_analysis",
                }[candidate],
                "",
            )) * 0.13)
            await notify(step_key, "running", max(0.03, local_progress), message)
            await notify("workflow", "running", workflow_progress, f"{state.get('stock_name', '')} 分析中")

        result = await func(state, progress_callback=step_progress_callback)
        state.update(result)
        result_text = state.get(
            {
                "fundamental": "fundamental_analysis",
                "technical": "technical_analysis",
                "value": "value_analysis",
                "news": "news_analysis",
                "forecast": "forecast_analysis",
            }[step_key],
            "",
        )
        step_status = "failed" if isinstance(result_text, str) and result_text.startswith("分析失败") else "completed"
        await notify(step_key, step_status, 1.0 if step_status == "completed" else 0.95, "已完成" if step_status == "completed" else "执行失败")

    parallel_steps = [
        ("fundamental", fundamental_agent),
        ("technical", technical_agent),
        ("value", value_agent),
        ("news", news_agent),
        ("forecast", forecast_agent),
    ]

    await notify("workflow", "running", 0.05, "识别股票并启动并行分析")
    parallel_steps = [
        ("fundamental", fundamental_agent),
        ("technical", technical_agent),
        ("value", value_agent),
        ("news", news_agent),
        ("forecast", forecast_agent),
    ]
    tasks = [asyncio.create_task(run_step(step_key, func)) for step_key, func in parallel_steps]
    for completed_count, task in enumerate(asyncio.as_completed(tasks), start=1):
        await task
        await notify("workflow", "running", 0.1 + completed_count * 0.13, f"已完成 {completed_count}/{len(tasks)} 个分析 Agent")

    await notify("summary", "running", 0.05, "等待汇总")

    async def summary_progress_callback(_: str, message: str, local_progress: float):
        overall_progress = 0.8 + local_progress * 0.2
        await notify("summary", "running", local_progress, message)
        await notify("workflow", "running", overall_progress, "正在生成综合报告")

    summary_result = await summary_agent(state, progress_callback=summary_progress_callback)
    state.update(summary_result)
    await notify("summary", "completed", 1.0, "综合报告已完成")
    await notify("workflow", "completed", 1.0, "分析完成")
    final_state = state
    final_state["execution_time"] = time.time() - start_time

    if final_state.get("report_file"):
        logger.info("%s 报告文件: %s", SUCCESS_ICON, final_state["report_file"])
    if final_state.get("errors"):
        logger.warning("%s 运行中存在问题: %s", ERROR_ICON, "; ".join(final_state["errors"]))
    return final_state
