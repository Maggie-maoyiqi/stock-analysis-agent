"""股票分析工具函数。"""
import logging
from typing import Literal

logger = logging.getLogger(__name__)


def get_stock_analysis(
    stock_code: str,
    analysis_type: Literal["fundamental", "technical", "comprehensive"] = "comprehensive",
) -> str:
    """生成股票分析报告（数据驱动，非投资建议）。"""
    return f"""## {stock_code} 股票分析报告

**分析类型:** {analysis_type}

**重要声明:** 本报告基于公开数据生成，仅供参考，不构成投资建议。

请使用其他工具获取具体的财务数据、K线数据和新闻信息进行完整分析。

**建议获取的数据:**
1. 基本面分析: 调用 get_profit_data, get_growth_data, get_balance_data
2. 技术面分析: 调用 get_historical_k_data, get_stock_basic_info
3. 估值分析: 调用 get_dividend_data, get_stock_basic_info
4. 新闻分析: 调用 crawl_news
"""
