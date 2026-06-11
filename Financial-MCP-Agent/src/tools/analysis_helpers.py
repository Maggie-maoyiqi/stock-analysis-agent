"""Helpers for LLM-backed analysis with graceful fallback."""
from __future__ import annotations

import os
from typing import Iterable

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

_LLM_DISABLED_REASON: str | None = None


class LLMUnavailableError(RuntimeError):
    """Raised when the configured LLM cannot be used."""


def _looks_like_placeholder(value: str) -> bool:
    lowered = value.strip().lower()
    return not lowered or "your_" in lowered or "api_key_here" in lowered or lowered in {"sk-", "null", "none"}


def _is_auth_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return "authentication" in text or "invalid api key" in text or "api key" in text and "invalid" in text


def _is_connection_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return "connection error" in text or "connecterror" in text or "nodename nor servname provided" in text


def _is_llm_configured() -> tuple[bool, str]:
    api_key = os.getenv("OPENAI_COMPATIBLE_API_KEY", "")
    base_url = os.getenv("OPENAI_COMPATIBLE_BASE_URL", "")
    if _looks_like_placeholder(api_key):
        return False, "未配置有效的 OPENAI_COMPATIBLE_API_KEY"
    if not base_url.strip():
        return False, "未配置 OPENAI_COMPATIBLE_BASE_URL"
    return True, ""


async def llm_generate_analysis(system_prompt: str, user_prompt: str) -> str:
    """Call the configured OpenAI-compatible model."""
    global _LLM_DISABLED_REASON

    configured, reason = _is_llm_configured()
    if not configured:
        _LLM_DISABLED_REASON = reason
        raise LLMUnavailableError(reason)
    if _LLM_DISABLED_REASON:
        raise LLMUnavailableError(_LLM_DISABLED_REASON)

    llm = ChatOpenAI(
        model=os.getenv("MODEL_NAME", "gpt-4o-mini"),
        api_key=os.getenv("OPENAI_COMPATIBLE_API_KEY"),
        base_url=os.getenv("OPENAI_COMPATIBLE_BASE_URL"),
        temperature=0.3,
    )
    try:
        response = await llm.ainvoke(
            [
                ("system", system_prompt),
                ("human", user_prompt),
            ]
        )
        return response.content
    except Exception as exc:
        if _is_auth_error(exc):
            _LLM_DISABLED_REASON = f"模型鉴权失败：{exc}"
            raise LLMUnavailableError(_LLM_DISABLED_REASON) from exc
        if _is_connection_error(exc):
            _LLM_DISABLED_REASON = f"模型服务连接失败：{exc}"
            raise LLMUnavailableError(_LLM_DISABLED_REASON) from exc
        raise


def build_offline_analysis(
    *,
    title: str,
    stock_name: str,
    stock_code: str,
    tool_payload: str,
    reason: str,
    bullet_points: Iterable[str],
) -> str:
    """Build a deterministic markdown analysis when the LLM is unavailable."""
    points = "\n".join(f"- {point}" for point in bullet_points)
    clipped_payload = tool_payload[:3000].strip()
    return (
        f"## {title}\n\n"
        f"**标的：** {stock_name} ({stock_code})\n\n"
        f"**当前模式：** 降级分析\n\n"
        f"**原因：** {reason}\n\n"
        f"### 可得结论\n"
        f"{points if points else '- 当前仅能返回工具原始数据，建议修复模型配置后重试。'}\n\n"
        f"### 工具原始数据摘录\n\n"
        f"```text\n{clipped_payload or '暂无工具数据'}\n```\n\n"
        f"### 说明\n\n"
        f"- 数据层结果已尽量保留。\n"
        f"- 当前结论未经过大模型润色与归纳。\n"
        f"- 修复模型配置后可获得更完整的自然语言分析报告。\n"
    )


def build_offline_summary_report(state: dict, reason: str) -> str:
    """Build the final report without using the LLM."""
    sections = [
        f"# {state.get('stock_name', '未知标的')} ({state.get('stock_code', '')}) 投资分析报告",
        "",
        "## 摘要",
        f"- 当前以降级模式生成报告，原因：{reason}",
        f"- 用户问题：{state.get('user_query', '')}",
        f"- 若需完整生成式报告，请修复模型 API 配置后重试。",
        "",
        "## 基本面分析",
        state.get("fundamental_analysis", "暂无数据"),
        "",
        "## 技术面分析",
        state.get("technical_analysis", "暂无数据"),
        "",
        "## 估值分析",
        state.get("value_analysis", "暂无数据"),
        "",
        "## 新闻舆情分析",
        state.get("news_analysis", "暂无数据"),
        "",
        "## 走势预测分析",
        state.get("forecast_analysis", "暂无数据"),
        "",
        "## 风险提示",
        "- 当前报告包含外部依赖失败后的降级内容，请重点关注原始数据摘录。",
        "- 本报告仅供研究和决策辅助，不构成投资建议。",
    ]
    return "\n".join(sections)
