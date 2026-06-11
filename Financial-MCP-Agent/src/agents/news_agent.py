"""新闻分析Agent。"""
import asyncio
from collections.abc import Awaitable, Callable
from typing import Any, Dict

from ..tools.analysis_helpers import LLMUnavailableError, build_offline_analysis, llm_generate_analysis
from ..tools.mcp_client import run_tools
from ..utils.logging_config import ERROR_ICON, SUCCESS_ICON, setup_logger
from ..utils.progress import run_with_heartbeat
from ..utils.state_definition import AgentState

logger = setup_logger(__name__)

NEWS_SYSTEM_PROMPT = """你是一位专业的A股新闻分析师。

请基于给出的新闻结果完成：
1. 关键新闻摘要
2. 风险等级分析
3. 情绪倾向分析
4. 对短期关注点的总结

要求：
- 只依据给定新闻内容，不引入外部事实。
- 明确区分事实、推断和风险提示。
- 输出使用 Markdown。"""


async def news_agent(
    state: AgentState,
    progress_callback: Callable[[str, str, float], Awaitable[None] | None] | None = None,
) -> Dict[str, Any]:
    """新闻分析Agent。"""
    logger.info("%s 开始新闻分析: %s", SUCCESS_ICON, state.get("stock_name", ""))

    async def notify(stage: str, progress: float):
        if progress_callback:
            result = progress_callback("news", stage, progress)
            if asyncio.iscoroutine(result):
                await result

    try:
        query = f"{state.get('stock_name', '')} {state.get('stock_code', '')}".strip()
        await notify("准备新闻检索关键词", 0.05)
        tool_payload = await run_with_heartbeat(
            run_tools(
                [("crawl_news", {"query": query, "top_k": 10, "stock_code": state.get("stock_code", "")})]
            ),
            notify,
            message="查询新闻与舆情数据",
            start=0.05,
            end=0.45,
            expected_seconds=12.0,
        )
        prompt = f"""请分析 {state.get("stock_name", "")}({state.get("stock_code", "")}) 的新闻舆情。
当前日期: {state.get("current_date", "")}

以下是工具返回的真实数据：

{tool_payload}
"""
        try:
            analysis = await run_with_heartbeat(
                llm_generate_analysis(NEWS_SYSTEM_PROMPT, prompt),
                notify,
                message="生成新闻舆情分析",
                start=0.45,
                end=0.92,
                expected_seconds=15.0,
            )
        except LLMUnavailableError as exc:
            analysis = build_offline_analysis(
                title="新闻舆情分析",
                stock_name=state.get("stock_name", ""),
                stock_code=state.get("stock_code", ""),
                tool_payload=tool_payload,
                reason=str(exc),
                bullet_points=[
                    "已成功获取新闻工具结果或兜底新闻内容。",
                    "当前因模型不可用，无法自动总结风险等级与情绪倾向。",
                    "你可以先从下方新闻标题、摘要、来源中人工判断短期舆情方向。",
                ],
            )
        await notify("整理新闻结论", 0.95)
        await notify("新闻分析完成", 1.0)
        logger.info("%s 新闻分析完成", SUCCESS_ICON)
        return {"news_analysis": analysis}
    except Exception as exc:
        logger.error("%s 新闻分析失败: %s", ERROR_ICON, exc)
        return {
            "news_analysis": f"分析失败: {exc}",
            "errors": [*state.get("errors", []), str(exc)],
        }
