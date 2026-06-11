"""可复用的股票分析工作流服务。"""
import asyncio
import time
from datetime import datetime
import re
from typing import Optional, Tuple

from .chart_service import build_analysis_charts
from .langgraph_workflow import build_analysis_graph
from ..tools.mcp_client import analysis_tool_cache
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

    hk_match = re.search(r"(?<![A-Za-z0-9])(\d{4,5}\.HK)(?![A-Za-z0-9])", query, re.IGNORECASE)
    if hk_match:
        code = hk_match.group(1).upper()
        return code, f"港股{code}"

    us_match = re.search(r"(?<![A-Za-z0-9])([A-Z]{1,5})(?![A-Za-z0-9])", query)
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

    hk_digits = re.search(r"(?<!\d)(\d{4,5})(?!\d)", query)
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
        "charts": [],
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

    async def notify(step: str, status: str, progress: float, message: str = ""):
        if progress_callback:
            maybe_awaitable = progress_callback(step, status, progress, message)
            if asyncio.iscoroutine(maybe_awaitable):
                await maybe_awaitable

    specialist_steps = {"fundamental", "technical", "value", "news", "forecast"}
    specialist_progresses = {step: 0.0 for step in specialist_steps}

    async def graph_progress_callback(step: str, status: str, progress: float, message: str = ""):
        if step in specialist_steps:
            specialist_progresses[step] = max(specialist_progresses[step], progress)
            average_specialist_progress = sum(specialist_progresses.values()) / len(specialist_progresses)
            workflow_progress = 0.05 + average_specialist_progress * 0.75
            workflow_message = f"{initial_state['stock_name']} 分析中"
        elif step == "summary":
            workflow_progress = 0.8 + progress * 0.2
            workflow_message = "正在生成综合报告"
        else:
            workflow_progress = progress
            workflow_message = message or "分析中"
        await notify(step, status, progress, message)
        await notify(
            "workflow",
            "completed" if step == "summary" and status == "completed" else "running",
            min(workflow_progress, 1.0),
            workflow_message,
        )

    await notify("workflow", "running", 0.05, "识别股票并启动并行分析")
    async with analysis_tool_cache():
        graph = build_analysis_graph(graph_progress_callback)
        final_state = await graph.ainvoke(initial_state.copy())
        try:
            final_state["charts"] = await build_analysis_charts(final_state.get("stock_code", ""), final_state.get("stock_name", ""))
        except Exception as exc:
            logger.warning("图表数据生成失败，已跳过图表展示: %s", exc)
            final_state["charts"] = []
    await notify("workflow", "completed", 1.0, "分析完成")
    final_state["execution_time"] = time.time() - start_time

    if final_state.get("report_file"):
        logger.info("%s 报告文件: %s", SUCCESS_ICON, final_state["report_file"])
    if final_state.get("errors"):
        logger.warning("%s 运行中存在问题: %s", ERROR_ICON, "; ".join(final_state["errors"]))
    return final_state
