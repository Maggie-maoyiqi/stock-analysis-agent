"""日期工具函数。"""
from datetime import datetime, timedelta
import logging

import baostock as bs

from ..utils import baostock_login_context

logger = logging.getLogger(__name__)


def get_latest_trading_date() -> str:
    """获取最近的交易日。"""
    today = datetime.now().strftime("%Y-%m-%d")
    with baostock_login_context():
        for days_ago in range(10):
            check_date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
            rs = bs.query_trade_dates(start_date=check_date, end_date=check_date)
            if rs.error_code == "0" and rs.next():
                row = dict(zip(rs.fields, rs.get_row_data()))
                if row.get("is_trading_day") == "1" or row.get("isTradeDay") == "1":
                    return check_date
    return today


def get_market_analysis_timeframe(time_range: str = "recent") -> str:
    """获取市场分析的时间范围。"""
    today = datetime.now()

    if time_range == "recent":
        start = today - timedelta(days=30)
        return f"分析时间范围: {start.strftime('%Y-%m-%d')} 至 {today.strftime('%Y-%m-%d')} (最近1个月)"
    if time_range == "quarter":
        start = today - timedelta(days=90)
        return f"分析时间范围: {start.strftime('%Y-%m-%d')} 至 {today.strftime('%Y-%m-%d')} (最近1季度)"
    if time_range == "half_year":
        start = today - timedelta(days=180)
        return f"分析时间范围: {start.strftime('%Y-%m-%d')} 至 {today.strftime('%Y-%m-%d')} (最近半年)"
    start = today - timedelta(days=365)
    return f"分析时间范围: {start.strftime('%Y-%m-%d')} 至 {today.strftime('%Y-%m-%d')} (最近1年)"
