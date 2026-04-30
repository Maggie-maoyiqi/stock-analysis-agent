"""技术分析Agent。"""
import asyncio
from collections.abc import Awaitable, Callable
from typing import Any, Dict

from ..tools.analysis_helpers import llm_generate_analysis
from ..tools.mcp_client import run_tools
from ..utils.logging_config import ERROR_ICON, SUCCESS_ICON, setup_logger
from ..utils.state_definition import AgentState

logger = setup_logger(__name__)

TECHNICAL_SYSTEM_PROMPT = """你是一位专业的A股技术分析师。

请基于提供的K线和基础信息完成技术分析，至少覆盖：
1. 趋势判断
2. 量价关系
3. 关键支撑位和压力位
4. 近中期观察结论
5. 风险提示

说明：
- 若数据中缺少MACD/RSI等指标，请明确说明无法直接计算，不要编造。
- 输出使用 Markdown。
- 结论仅基于数据，不构成投资建议。"""


async def technical_agent(
    state: AgentState,
    progress_callback: Callable[[str, str, float], Awaitable[None] | None] | None = None,
) -> Dict[str, Any]:
    """技术分析Agent。"""
    logger.info("%s 开始技术分析: %s", SUCCESS_ICON, state.get("stock_name", ""))
    stock_code = state.get("stock_code", "")
    current_date = state.get("current_date", "")
    start_date = f"{int(current_date[:4]) - 1}-{current_date[5:]}" if len(current_date) >= 10 else "2024-01-01"

    async def notify(stage: str, progress: float):
        if progress_callback:
            result = progress_callback("technical", stage, progress)
            if asyncio.iscoroutine(result):
                await result

    try:
        await notify("准备K线分析参数", 0.1)
        await notify("查询历史K线与市场范围", 0.35)
        tool_payload = await run_tools(
            [
                ("historical_k_data", {
                    "stock_code": stock_code,
                    "start_date": start_date,
                    "end_date": current_date,
                    "frequency": "d",
                    "adjustflag": "2",
                }),
                ("stock_basic_info", {"stock_code": stock_code}),
                ("market_analysis_timeframe", {"time_range": "recent"}),
            ]
        )

        await notify("生成技术面分析", 0.72)
        prompt = f"""请分析股票 {state.get("stock_name", "")}({stock_code}) 的技术面情况。
当前日期: {current_date}

以下是工具返回的真实数据：

{tool_payload}
"""
        analysis = await llm_generate_analysis(TECHNICAL_SYSTEM_PROMPT, prompt)
        await notify("整理技术结论", 0.92)
        await notify("技术分析完成", 1.0)
        logger.info("%s 技术分析完成", SUCCESS_ICON)
        return {"technical_analysis": analysis}
    except Exception as exc:
        logger.error("%s 技术分析失败: %s", ERROR_ICON, exc)
        return {
            "technical_analysis": f"分析失败: {exc}",
            "errors": [*state.get("errors", []), str(exc)],
        }
