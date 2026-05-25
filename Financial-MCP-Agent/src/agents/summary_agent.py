"""总结Agent。"""
import asyncio
import os
import time
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from ..utils.logging_config import ERROR_ICON, SUCCESS_ICON, setup_logger
from ..utils.progress import run_with_heartbeat
from ..utils.state_definition import AgentState

load_dotenv()
logger = setup_logger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parents[2]

SUMMARY_PROMPT = """你是一位专业的投资分析师。请根据以下分析结果，生成一份完整的投资分析报告。

## 用户问题
{user_query}

## 基本面分析结果
{fundamental_analysis}

## 技术面分析结果
{technical_analysis}

## 估值分析结果
{value_analysis}

## 新闻舆情分析结果
{news_analysis}

## 走势预测分析结果
{forecast_analysis}

请生成包含以下10个部分的Markdown报告：

1. **摘要** - 核心观点和投资结论（200字以内）
2. **公司概况** - 基本信息、主营业务
3. **基本面分析** - 盈利能力、成长性、偿债能力、现金流
4. **技术面分析** - 趋势、量价、关键价位、技术指标
5. **估值分析** - PE/PB/PS评估、行业对比、估值判断
6. **新闻舆情分析** - 风险等级、情绪倾向、关键事件
7. **综合评估** - SWOT分析（优势、劣势、机会、威胁）
8. **风险因素** - 主要风险点及影响程度
9. **投资建议** - 基于所有分析给出明确的 `买入 / 观望 / 减持 / 卖出` 倾向，并写出理由与主要触发条件
10. **附录** - 数据来源、免责声明

**重要声明：** 本报告仅供参考，不构成投资建议。投资有风险，入市需谨慎。

请直接输出Markdown格式的报告，不要有任何额外说明。"""


async def summary_agent(
    state: AgentState,
    progress_callback: Callable[[str, str, float], Awaitable[None] | None] | None = None,
) -> Dict[str, Any]:
    """总结Agent - 生成最终报告。"""
    logger.info("%s 开始生成最终报告", SUCCESS_ICON)
    start_time = time.time()

    async def notify(stage: str, progress: float):
        if progress_callback:
            result = progress_callback("summary", stage, progress)
            if asyncio.iscoroutine(result):
                await result

    try:
        await notify("准备汇总多 Agent 结果", 0.1)
        llm = ChatOpenAI(
            model=os.getenv("MODEL_NAME", "gpt-4o-mini"),
            api_key=os.getenv("OPENAI_COMPATIBLE_API_KEY"),
            base_url=os.getenv("OPENAI_COMPATIBLE_BASE_URL"),
            temperature=0.2,
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", "你是一位专业的投资分析师，擅长整合多维度信息生成投资报告。"),
                ("human", SUMMARY_PROMPT),
            ]
        )
        chain = prompt | llm

        result = await run_with_heartbeat(
            chain.ainvoke(
                {
                    "user_query": state.get("user_query", ""),
                    "fundamental_analysis": state.get("fundamental_analysis", "无数据"),
                    "technical_analysis": state.get("technical_analysis", "无数据"),
                    "value_analysis": state.get("value_analysis", "无数据"),
                    "news_analysis": state.get("news_analysis", "无数据"),
                    "forecast_analysis": state.get("forecast_analysis", "无数据"),
                }
            ),
            notify,
            message="生成综合投资报告",
            start=0.15,
            end=0.88,
            expected_seconds=35.0,
        )

        report = result.content
        reports_dir = PROJECT_ROOT / "reports"
        reports_dir.mkdir(exist_ok=True)
        report_file = reports_dir / f"report_{state.get('stock_code', 'unknown').replace('.', '_')}_{int(time.time())}.md"
        await notify("保存报告文件", 0.92)
        report_file.write_text(report, encoding="utf-8")

        await notify("汇总报告完成", 1.0)
        logger.info("%s 报告已保存至: %s", SUCCESS_ICON, report_file)
        logger.info("%s 报告生成完成，耗时: %.2f秒", SUCCESS_ICON, time.time() - start_time)
        return {"final_report": report, "report_file": str(report_file)}
    except Exception as exc:
        logger.error("%s 报告生成失败: %s", ERROR_ICON, exc)
        return {
            "final_report": f"报告生成失败: {exc}",
            "errors": [*state.get("errors", []), str(exc)],
        }
