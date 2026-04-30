"""市场概览工具函数。"""
from datetime import datetime, timedelta
import logging

import baostock as bs

from ..utils import baostock_login_context

logger = logging.getLogger(__name__)


def get_trade_dates(start_date: str = None, end_date: str = None) -> str:
    """获取指定范围内的交易日信息。"""
    if not end_date:
        end_date = datetime.now().strftime("%Y-%m-%d")
    if not start_date:
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

    with baostock_login_context():
        rs = bs.query_trade_dates(start_date=start_date, end_date=end_date)
        dates = []
        while rs.error_code == "0" and rs.next():
            dates.append(dict(zip(rs.fields, rs.get_row_data())))

    if not dates:
        return f"未获取到 {start_date} 至 {end_date} 的交易日数据"

    table = f"## 交易日历 ({start_date} 至 {end_date})\n\n"
    table += "| 日期 | 是否交易日 |\n"
    table += "|------|------------|\n"
    for item in dates[-30:]:
        trade_date = item.get("calendar_date", item.get("tradeDate", ""))
        is_trade_day = item.get("is_trading_day", item.get("isTradeDay", ""))
        table += f"| {trade_date} | {is_trade_day} |\n"
    return table


def get_all_stock(date: str = None) -> str:
    """获取指定日期的所有股票列表。"""
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")

    with baostock_login_context():
        rs = bs.query_all_stock(date)
        stocks = []
        while rs.error_code == "0" and rs.next():
            stocks.append(dict(zip(rs.fields, rs.get_row_data())))

    if not stocks:
        return f"未获取到 {date} 的股票列表"

    table = f"## 全市场股票列表 ({date})\n\n"
    table += "| 序号 | 股票代码 | 股票名称 | 交易状态 |\n"
    table += "|------|----------|----------|----------|\n"
    for i, stock in enumerate(stocks[:100], 1):
        table += (
            f"| {i} | {stock.get('code', '')} | {stock.get('code_name', '')} | "
            f"{stock.get('tradeStatus', stock.get('trade_status', ''))} |\n"
        )
    return table
