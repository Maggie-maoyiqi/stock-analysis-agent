"""股票市场工具函数。"""
import json
import logging

from ..data_source_factory import get_data_source

logger = logging.getLogger(__name__)


def get_historical_k_data(
    stock_code: str,
    start_date: str,
    end_date: str,
    frequency: str = "d",
    adjustflag: str = "2",
) -> str:
    """获取股票历史K线数据。"""
    data_source = get_data_source(stock_code)
    data = data_source.get_historical_k_data(stock_code, start_date, end_date, frequency, adjustflag)
    if not data:
        return f"未获取到股票 {stock_code} 在 {start_date} 至 {end_date} 期间的K线数据"

    headers = ["日期", "开盘", "最高", "最低", "收盘", "成交量", "涨跌幅(%)", "市盈率", "市净率"]
    rows = []
    for item in data[:50]:
        rows.append(
            [
                item.get("date", ""),
                item.get("open", ""),
                item.get("high", ""),
                item.get("low", ""),
                item.get("close", ""),
                item.get("volume", ""),
                item.get("pctChg", ""),
                item.get("peTTM", ""),
                item.get("pbMRQ", ""),
            ]
        )

    table = "| " + " | ".join(headers) + " |\n"
    table += "|" + "|".join([" --- " for _ in headers]) + "|\n"
    for row in rows:
        table += "| " + " | ".join(str(cell) for cell in row) + " |\n"
    return f"## {stock_code} K线数据 ({start_date} 至 {end_date})\n\n{table}"


def get_historical_k_data_json(
    stock_code: str,
    start_date: str,
    end_date: str,
    frequency: str = "d",
    adjustflag: str = "2",
) -> str:
    """获取股票历史K线数据并返回 JSON。"""
    data_source = get_data_source(stock_code)
    data = data_source.get_historical_k_data(stock_code, start_date, end_date, frequency, adjustflag)
    return json.dumps(
        {
            "stock_code": stock_code,
            "start_date": start_date,
            "end_date": end_date,
            "frequency": frequency,
            "adjustflag": adjustflag,
            "items": data or [],
        },
        ensure_ascii=False,
    )


def get_stock_basic_info(stock_code: str) -> str:
    """获取股票基本信息。"""
    data_source = get_data_source(stock_code)
    info = data_source.get_stock_basic_info(stock_code)
    if not info:
        return f"未找到股票 {stock_code} 的基本信息"

    return f"""## {stock_code} 基本信息

| 项目 | 值 |
|------|-----|
| 股票代码 | {info.get('code', 'N/A')} |
| 股票名称 | {info.get('name', 'N/A')} |
| 上市日期 | {info.get('ipoDate', 'N/A')} |
| 退市日期 | {info.get('outDate', 'N/A')} |
| 股票类型 | {info.get('type', 'N/A')} |
| 状态 | {info.get('status', 'N/A')} |
| 交易所 | {info.get('exchange', 'N/A')} |
| 币种 | {info.get('currency', 'N/A')} |
| 市盈率(TTM) | {info.get('pe_ttm', 'N/A')} |
| 市净率 | {info.get('pb_mrq', 'N/A')} |
| 行业 | {info.get('industry', 'N/A')} |
"""


def get_dividend_data(stock_code: str, year: int) -> str:
    """获取股票分红数据。"""
    data_source = get_data_source(stock_code)
    data = data_source.get_dividend_data(stock_code, year)
    if not data:
        return f"未找到 {stock_code} {year} 年的分红数据"

    headers = ["年份", "每股分红", "除权除息日"]
    table = "| " + " | ".join(headers) + " |\n"
    table += "|" + "|".join([" --- " for _ in headers]) + "|\n"
    for item in data:
        table += (
            f"| {item.get('year', '')} | {item.get('dividend_per_share', '')} | "
            f"{item.get('ex_dividend_date', '')} |\n"
        )

    return f"## {stock_code} 分红数据 ({year}年)\n\n{table}"
