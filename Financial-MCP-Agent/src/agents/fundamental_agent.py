"""基本面分析Agent。"""
import asyncio
from collections.abc import Awaitable, Callable
from typing import Any, Dict

from ..tools.analysis_helpers import llm_generate_analysis
from ..tools.mcp_client import run_tools
from ..utils.execution_logger import get_execution_logger
from ..utils.logging_config import ERROR_ICON, SUCCESS_ICON, setup_logger
from ..utils.state_definition import AgentState

logger = setup_logger(__name__)

FUNDAMENTAL_SYSTEM_PROMPT = """你是一位专业的A股基本面分析师。

请基于已给出的真实工具数据，完成以下内容：
1. 公司基本信息
2. 盈利能力分析
3. 成长能力分析
4. 偿债能力分析
5. 现金流分析
6. 杜邦分析
7. 分红情况
8. 行业对比与长期投资价值

要求：
- 结论必须引用给定数据，不能编造。
- 明确写出优势、风险和需要持续跟踪的指标。
- 输出结构化 Markdown。"""


async def fundamental_agent(
    state: AgentState,
    progress_callback: Callable[[str, str, float], Awaitable[None] | None] | None = None,
) -> Dict[str, Any]:
    """基本面分析Agent。"""
    logger.info("%s 开始基本面分析: %s", SUCCESS_ICON, state.get("stock_name", ""))
    stock_code = state.get("stock_code", "")
    current_year = int(state.get("current_date", "2025-01-01")[:4])
    last_year = max(current_year - 1, 2020)

    async def notify(stage: str, progress: float):
        if progress_callback:
            result = progress_callback("fundamental", stage, progress)
            if asyncio.iscoroutine(result):
                await result

    try:
        await notify("准备分析上下文", 0.1)
        await notify("查询财务与分红数据", 0.35)
        tool_payload = await run_tools(
            [
                ("stock_basic_info", {"stock_code": stock_code}),
                ("profit_data", {"stock_code": stock_code, "year": last_year, "quarter": 4}),
                ("growth_data", {"stock_code": stock_code, "year": last_year, "quarter": 4}),
                ("balance_data", {"stock_code": stock_code, "year": last_year, "quarter": 4}),
                ("cash_flow_data", {"stock_code": stock_code, "year": last_year, "quarter": 4}),
                ("dupont_data", {"stock_code": stock_code, "year": last_year, "quarter": 4}),
                ("dividend_data", {"stock_code": stock_code, "year": last_year}),
                ("stock_industry", {"stock_code": stock_code}),
            ]
        )

        await notify("生成基本面分析", 0.72)
        prompt = f"""请分析股票 {state.get("stock_name", "")}({stock_code}) 的基本面情况。
当前日期: {state.get("current_date", "")}

以下是工具返回的真实数据：

{tool_payload}
"""
        analysis = await llm_generate_analysis(FUNDAMENTAL_SYSTEM_PROMPT, prompt)
        await notify("整理基本面结论", 0.92)
        get_execution_logger().log_interaction(
            "fundamental_agent",
            {"stock_code": stock_code},
            {"analysis_length": len(analysis)},
            0.0,
        )
        await notify("基本面分析完成", 1.0)
        logger.info("%s 基本面分析完成", SUCCESS_ICON)
        return {"fundamental_analysis": analysis}
    except Exception as exc:
        logger.error("%s 基本面分析失败: %s", ERROR_ICON, exc)
        return {
            "fundamental_analysis": f"分析失败: {exc}",
            "errors": [*state.get("errors", []), str(exc)],
        }
