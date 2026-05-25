"""走势预测 Agent。"""
import asyncio
from collections.abc import Awaitable, Callable
from typing import Any, Dict

from ..tools.analysis_helpers import llm_generate_analysis
from ..tools.mcp_client import run_tools
from ..utils.logging_config import ERROR_ICON, SUCCESS_ICON, setup_logger
from ..utils.progress import run_with_heartbeat
from ..utils.state_definition import AgentState

logger = setup_logger(__name__)

FORECAST_SYSTEM_PROMPT = """你是一位专业的股票预测分析师。

请基于提供的预测结果和历史行情摘要完成：
1. 对短期走势方向的解读
2. 对预测置信度和局限性的说明
3. 对预测结果和技术面/基本面的结合建议
4. 明确区分模型信号与投资结论

要求：
- 不要夸大预测能力。
- 如果预测结果偏弱或中性，要明确说明。
- 输出使用 Markdown。"""


async def forecast_agent(
    state: AgentState,
    progress_callback: Callable[[str, str, float], Awaitable[None] | None] | None = None,
) -> Dict[str, Any]:
    """预测分析Agent。"""
    logger.info("%s 开始走势预测分析: %s", SUCCESS_ICON, state.get("stock_name", ""))

    async def notify(stage: str, progress: float):
        if progress_callback:
            result = progress_callback("forecast", stage, progress)
            if asyncio.iscoroutine(result):
                await result

    try:
        await notify("准备预测输入数据", 0.05)
        tool_payload = await run_with_heartbeat(
            run_tools(
                [
                    ("price_forecast", {"stock_code": state.get("stock_code", "")}),
                    (
                        "historical_k_data",
                        {
                            "stock_code": state.get("stock_code", ""),
                            "start_date": f"{int(state.get('current_date', '2025-01-01')[:4]) - 1}-01-01",
                            "end_date": state.get("current_date", ""),
                            "frequency": "d",
                            "adjustflag": "2",
                        },
                    ),
                ]
            ),
            notify,
            message="查询预测与历史行情",
            start=0.05,
            end=0.45,
            expected_seconds=10.0,
        )

        prompt = f"""请分析股票 {state.get("stock_name", "")}({state.get("stock_code", "")}) 的短期走势预测。
当前日期: {state.get("current_date", "")}

以下是工具返回的真实数据：

{tool_payload}
"""
        analysis = await run_with_heartbeat(
            llm_generate_analysis(FORECAST_SYSTEM_PROMPT, prompt),
            notify,
            message="生成走势预测解读",
            start=0.45,
            end=0.92,
            expected_seconds=15.0,
        )
        await notify("整理预测结论", 0.95)
        await notify("预测分析完成", 1.0)
        logger.info("%s 走势预测分析完成", SUCCESS_ICON)
        return {"forecast_analysis": analysis}
    except Exception as exc:
        logger.error("%s 走势预测分析失败: %s", ERROR_ICON, exc)
        return {
            "forecast_analysis": f"分析失败: {exc}",
            "errors": [*state.get("errors", []), str(exc)],
        }
