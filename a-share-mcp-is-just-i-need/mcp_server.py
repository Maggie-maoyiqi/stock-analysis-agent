"""MCP服务器 - 注册所有金融分析工具。"""
import logging
import os
import sys

from mcp.server.fastmcp import FastMCP

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP("A-Share-MCP-Server")

from src.tools.analysis import get_stock_analysis  # noqa: E402
from src.tools.date_utils import get_latest_trading_date, get_market_analysis_timeframe  # noqa: E402
from src.tools.financial_reports import (  # noqa: E402
    get_balance_data,
    get_cash_flow_data,
    get_dupont_data,
    get_growth_data,
    get_profit_data,
)
from src.tools.indices import (  # noqa: E402
    get_hs300_stocks,
    get_stock_industry,
    get_sz50_stocks,
    get_zz500_stocks,
)
from src.tools.macroeconomic import (  # noqa: E402
    get_deposit_rate_data,
    get_loan_rate_data,
    get_money_supply_data_month,
    get_required_reserve_ratio_data,
)
from src.tools.market_overview import get_all_stock, get_trade_dates  # noqa: E402
from src.tools.news_crawler import crawl_news as crawl_news_tool  # noqa: E402
from src.tools.forecasting import forecast_price_trend  # noqa: E402
from src.tools.briefing import get_market_context, get_stock_snapshot  # noqa: E402
from src.tools.stock_market import (  # noqa: E402
    get_dividend_data,
    get_historical_k_data,
    get_stock_basic_info,
)


@mcp.tool()
def historical_k_data(stock_code: str, start_date: str, end_date: str, frequency: str = "d", adjustflag: str = "2") -> str:
    """获取股票历史K线数据。"""
    return get_historical_k_data(stock_code, start_date, end_date, frequency, adjustflag)


@mcp.tool()
def stock_basic_info(stock_code: str) -> str:
    """获取股票基本信息。"""
    return get_stock_basic_info(stock_code)


@mcp.tool()
def dividend_data(stock_code: str, year: int) -> str:
    """获取股票分红数据。"""
    return get_dividend_data(stock_code, year)


@mcp.tool()
def profit_data(stock_code: str, year: int, quarter: int) -> str:
    """获取盈利能力数据（ROE、净利润率等）。"""
    return get_profit_data(stock_code, year, quarter)


@mcp.tool()
def growth_data(stock_code: str, year: int, quarter: int) -> str:
    """获取成长能力数据（营收/净利润增长率）。"""
    return get_growth_data(stock_code, year, quarter)


@mcp.tool()
def balance_data(stock_code: str, year: int, quarter: int) -> str:
    """获取资产负债表/偿债能力数据。"""
    return get_balance_data(stock_code, year, quarter)


@mcp.tool()
def cash_flow_data(stock_code: str, year: int, quarter: int) -> str:
    """获取现金流量数据。"""
    return get_cash_flow_data(stock_code, year, quarter)


@mcp.tool()
def dupont_data(stock_code: str, year: int, quarter: int) -> str:
    """获取杜邦分析数据（ROE分解）。"""
    return get_dupont_data(stock_code, year, quarter)


@mcp.tool()
def hs300_stocks(date: str = None) -> str:
    """获取沪深300成分股。"""
    return get_hs300_stocks(date)


@mcp.tool()
def zz500_stocks(date: str = None) -> str:
    """获取中证500成分股。"""
    return get_zz500_stocks(date)


@mcp.tool()
def sz50_stocks(date: str = None) -> str:
    """获取上证50成分股。"""
    return get_sz50_stocks(date)


@mcp.tool()
def stock_industry(stock_code: str = None) -> str:
    """获取股票行业分类。"""
    return get_stock_industry(stock_code)


@mcp.tool()
def latest_trading_date() -> str:
    """获取最近交易日。"""
    return get_latest_trading_date()


@mcp.tool()
def market_analysis_timeframe(time_range: str = "recent") -> str:
    """获取市场分析时间范围。"""
    return get_market_analysis_timeframe(time_range)


@mcp.tool()
def crawl_news(query: str, top_k: int = 10, stock_code: str = "") -> str:
    """爬取相关新闻并进行分析。"""
    return crawl_news_tool(query, top_k, stock_code)


@mcp.tool()
def stock_analysis(stock_code: str, analysis_type: str = "comprehensive") -> str:
    """生成股票分析报告。"""
    return get_stock_analysis(stock_code, analysis_type)


@mcp.tool()
def deposit_rate_data(start_date: str, end_date: str) -> str:
    """获取存款利率数据。"""
    return get_deposit_rate_data(start_date, end_date)


@mcp.tool()
def loan_rate_data(start_date: str, end_date: str) -> str:
    """获取贷款利率数据。"""
    return get_loan_rate_data(start_date, end_date)


@mcp.tool()
def money_supply_month(start_date: str, end_date: str) -> str:
    """获取月度货币供应量。"""
    return get_money_supply_data_month(start_date, end_date)


@mcp.tool()
def reserve_ratio_data(start_date: str, end_date: str) -> str:
    """获取存款准备金率。"""
    return get_required_reserve_ratio_data(start_date, end_date)


@mcp.tool()
def trade_dates(start_date: str = None, end_date: str = None) -> str:
    """获取交易日历。"""
    return get_trade_dates(start_date, end_date)


@mcp.tool()
def all_stock(date: str = None) -> str:
    """获取全市场股票列表。"""
    return get_all_stock(date)


@mcp.tool()
def price_forecast(stock_code: str) -> str:
    """获取股票短期走势预测。"""
    return forecast_price_trend(stock_code)


@mcp.tool()
def stock_snapshot(stock_code: str, stock_name: str = "") -> str:
    """获取结构化个股快照，返回 JSON 字符串。"""
    return get_stock_snapshot(stock_code, stock_name)


@mcp.tool()
def market_context(session: str = "morning") -> str:
    """获取结构化市场环境摘要，返回 JSON 字符串。"""
    return get_market_context(session)


if __name__ == "__main__":
    logger.info("启动 A-Share MCP Server...")
    mcp.run()
