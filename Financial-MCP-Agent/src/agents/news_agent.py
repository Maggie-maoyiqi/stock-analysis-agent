"""新闻分析Agent。"""
import asyncio
from collections.abc import Awaitable, Callable
from typing import Any, Dict

from ..tools.analysis_helpers import llm_generate_analysis
from ..tools.mcp_client import run_tools
from ..utils.logging_config import ERROR_ICON, SUCCESS_ICON, setup_logger
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
        await notify("准备新闻检索关键词", 0.1)
        await notify("查询新闻与舆情数据", 0.35)
        tool_payload = await run_tools([("crawl_news", {"query": query, "top_k": 10, "stock_code": state.get("stock_code", "")})])
        await notify("生成新闻舆情分析", 0.72)
        prompt = f"""请分析 {state.get("stock_name", "")}({state.get("stock_code", "")}) 的新闻舆情。
当前日期: {state.get("current_date", "")}

以下是工具返回的真实数据：

{tool_payload}
"""
        analysis = await llm_generate_analysis(NEWS_SYSTEM_PROMPT, prompt)
        await notify("整理新闻结论", 0.92)
        await notify("新闻分析完成", 1.0)
        logger.info("%s 新闻分析完成", SUCCESS_ICON)
        return {"news_analysis": analysis}
    except Exception as exc:
        logger.error("%s 新闻分析失败: %s", ERROR_ICON, exc)
        return {
            "news_analysis": f"分析失败: {exc}",
            "errors": [*state.get("errors", []), str(exc)],
        }
