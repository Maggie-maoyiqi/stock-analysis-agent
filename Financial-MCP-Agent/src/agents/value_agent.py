"""估值分析Agent。"""
import asyncio
from collections.abc import Awaitable, Callable
from typing import Any, Dict

from ..tools.analysis_helpers import LLMUnavailableError, build_offline_analysis, llm_generate_analysis
from ..tools.mcp_client import run_tools
from ..utils.logging_config import ERROR_ICON, SUCCESS_ICON, setup_logger
from ..utils.progress import run_with_heartbeat
from ..utils.state_definition import AgentState

logger = setup_logger(__name__)

VALUE_SYSTEM_PROMPT = """你是一位专业的A股估值分析师。

请基于给出的真实数据完成估值分析，至少包括：
1. 当前估值线索
2. 分红与股息视角
3. 历史与行业对比的局限性说明
4. 对低估/合理/高估的谨慎判断
5. 主要估值风险

要求：
- 如果缺乏完整行业估值或历史分位数据，要明确说明数据不足。
- 不要把缺失的数据硬编成结论。
- 输出使用 Markdown。"""


async def value_agent(
    state: AgentState,
    progress_callback: Callable[[str, str, float], Awaitable[None] | None] | None = None,
) -> Dict[str, Any]:
    """估值分析Agent。"""
    logger.info("%s 开始估值分析: %s", SUCCESS_ICON, state.get("stock_name", ""))
    stock_code = state.get("stock_code", "")
    current_year = int(state.get("current_date", "2025-01-01")[:4])
    last_year = max(current_year - 1, 2020)

    async def notify(stage: str, progress: float):
        if progress_callback:
            result = progress_callback("value", stage, progress)
            if asyncio.iscoroutine(result):
                await result

    try:
        await notify("准备估值分析参数", 0.05)
        tool_payload = await run_with_heartbeat(
            run_tools(
                [
                    ("stock_basic_info", {"stock_code": stock_code}),
                    ("historical_k_data", {
                        "stock_code": stock_code,
                        "start_date": f"{last_year}-01-01",
                        "end_date": state.get("current_date", ""),
                        "frequency": "d",
                        "adjustflag": "2",
                    }),
                    ("dividend_data", {"stock_code": stock_code, "year": last_year}),
                    ("stock_industry", {"stock_code": stock_code}),
                ]
            ),
            notify,
            message="查询估值与分红数据",
            start=0.05,
            end=0.45,
            expected_seconds=8.0,
        )

        prompt = f"""请分析股票 {state.get("stock_name", "")}({stock_code}) 的估值水平。
当前日期: {state.get("current_date", "")}

以下是工具返回的真实数据：

{tool_payload}
"""
        try:
            analysis = await run_with_heartbeat(
                llm_generate_analysis(VALUE_SYSTEM_PROMPT, prompt),
                notify,
                message="生成估值分析",
                start=0.45,
                end=0.92,
                expected_seconds=18.0,
            )
        except LLMUnavailableError as exc:
            analysis = build_offline_analysis(
                title="估值分析",
                stock_name=state.get("stock_name", ""),
                stock_code=stock_code,
                tool_payload=tool_payload,
                reason=str(exc),
                bullet_points=[
                    "已成功获取基础信息、历史行情、分红和行业工具结果。",
                    "当前因模型不可用，无法自动形成低估/合理/高估的自然语言判断。",
                    "你仍可以根据下方原始估值相关数据和前端雷达图做人工复核。",
                ],
            )
        await notify("整理估值结论", 0.95)
        await notify("估值分析完成", 1.0)
        logger.info("%s 估值分析完成", SUCCESS_ICON)
        return {"value_analysis": analysis}
    except Exception as exc:
        logger.error("%s 估值分析失败: %s", ERROR_ICON, exc)
        return {
            "value_analysis": f"分析失败: {exc}",
            "errors": [*state.get("errors", []), str(exc)],
        }
