"""基于Baostock的数据源实现。"""
from datetime import datetime
import logging
from typing import Any, Dict, List, Optional

import baostock as bs

from .data_source_interface import DataSourceError, FinancialDataSource
from .utils import baostock_login_context

logger = logging.getLogger(__name__)

DEFAULT_K_FIELDS = [
    "date",
    "code",
    "open",
    "high",
    "low",
    "close",
    "preclose",
    "volume",
    "amount",
    "adjustflag",
    "turn",
    "tradestatus",
    "pctChg",
    "peTTM",
    "pbMRQ",
]


def _row_to_dict(result_set) -> Dict[str, Any]:
    """将 Baostock 当前行转换为字典。"""
    return dict(zip(result_set.fields, result_set.get_row_data()))


def _to_float(value: Any, default: float = 0.0) -> float:
    """安全转换浮点数。"""
    try:
        if value in ("", None):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


class BaostockDataSource(FinancialDataSource):
    """Baostock数据源实现。"""

    def __init__(self):
        self._logged_in = False

    def _ensure_login(self):
        """确保已登录。"""
        if not self._logged_in:
            lg = bs.login()
            if lg.error_code != "0":
                raise DataSourceError(f"Baostock登录失败: {lg.error_msg}")
            self._logged_in = True

    def get_historical_k_data(
        self,
        stock_code: str,
        start_date: str,
        end_date: str,
        frequency: str = "d",
        adjustflag: str = "2",
    ) -> List[Dict[str, Any]]:
        """获取历史K线数据。"""
        with baostock_login_context():
            rs = bs.query_history_k_data_plus(
                code=stock_code,
                fields=",".join(DEFAULT_K_FIELDS),
                start_date=start_date,
                end_date=end_date,
                frequency=frequency,
                adjustflag=adjustflag,
            )
            if rs.error_code != "0":
                raise DataSourceError(f"K线数据查询失败: {rs.error_msg}")

            data = []
            while rs.next():
                data.append(_row_to_dict(rs))
            return data

    def get_stock_basic_info(self, stock_code: str, fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """获取股票基本信息。"""
        with baostock_login_context():
            rs = bs.query_stock_basic(code=stock_code)
            if rs.error_code != "0":
                raise DataSourceError(f"股票基本信息查询失败: {rs.error_msg}")

            if rs.next():
                row = _row_to_dict(rs)
                base_row = {
                    "code": row.get("code", ""),
                    "name": row.get("code_name", ""),
                    "ipoDate": row.get("ipoDate", ""),
                    "outDate": row.get("outDate", ""),
                    "type": row.get("type", ""),
                    "status": row.get("status", ""),
                }
                if fields:
                    return {key: base_row.get(key, row.get(key, "")) for key in fields}
                return base_row
            return {}

    def get_profit_data(self, stock_code: str, year: int, quarter: int) -> Dict[str, Any]:
        """获取盈利能力数据。"""
        with baostock_login_context():
            rs = bs.query_profit_data(code=stock_code, year=year, quarter=quarter)
            if rs.error_code != "0" or not rs.next():
                return {}

            row = _row_to_dict(rs)
            return {
                "roe": row.get("roeAvg", ""),
                "net_profit_rate": row.get("netProfitRate", ""),
                "gross_profit_rate": row.get("grossProfitRate", ""),
                "eps": row.get("eps", ""),
                "year": year,
                "quarter": quarter,
            }

    def get_growth_data(self, stock_code: str, year: int, quarter: int) -> Dict[str, Any]:
        """获取成长能力数据。"""
        with baostock_login_context():
            rs = bs.query_growth_data(code=stock_code, year=year, quarter=quarter)
            if rs.error_code != "0" or not rs.next():
                return {}

            row = _row_to_dict(rs)
            return {
                "yoy_net_profit": row.get("YOYNetProfit", ""),
                "yoy_revenue": row.get("YOYRevenue", ""),
                "yoy_eps": row.get("YOYEPSBasic", row.get("YOYEPS", "")),
                "year": year,
                "quarter": quarter,
            }

    def get_balance_data(self, stock_code: str, year: int, quarter: int) -> Dict[str, Any]:
        """获取资产负债表数据。"""
        with baostock_login_context():
            rs = bs.query_balance_data(code=stock_code, year=year, quarter=quarter)
            if rs.error_code != "0" or not rs.next():
                return {}

            row = _row_to_dict(rs)
            total_assets = _to_float(row.get("totalAssets"))
            total_liab = _to_float(row.get("totalLiab"))
            return {
                "asset_debt_ratio": total_liab / total_assets if total_assets > 0 else 0,
                "total_assets": total_assets,
                "total_liabilities": total_liab,
                "current_ratio": _to_float(row.get("currentRatio")),
                "year": year,
                "quarter": quarter,
            }

    def get_cash_flow_data(self, stock_code: str, year: int, quarter: int) -> Dict[str, Any]:
        """获取现金流量数据。"""
        with baostock_login_context():
            rs = bs.query_cash_flow_data(code=stock_code, year=year, quarter=quarter)
            if rs.error_code != "0" or not rs.next():
                return {}

            row = _row_to_dict(rs)
            return {
                "operating_cash_flow": row.get("netOperateCashFlow", row.get("operatingCashFlow", "")),
                "free_cash_flow": row.get("freeCashFlow", ""),
                "year": year,
                "quarter": quarter,
            }

    def get_dividend_data(self, stock_code: str, year: int) -> List[Dict[str, Any]]:
        """获取分红数据。"""
        with baostock_login_context():
            rs = bs.query_dividend_data(code=stock_code, year=year)
            if rs.error_code != "0":
                return []

            data = []
            while rs.next():
                row = _row_to_dict(rs)
                data.append(
                    {
                        "year": row.get("year", ""),
                        "dividend_per_share": row.get("dividOperateDate", row.get("dividendPerShare", "")),
                        "ex_dividend_date": row.get("dividPayDate", row.get("exDividendDate", "")),
                    }
                )
            return data

    def get_hs300_stocks(self, date: Optional[str] = None) -> List[str]:
        """获取沪深300成分股。"""
        with baostock_login_context():
            rs = bs.query_hs300_stocks(date or datetime.now().strftime("%Y-%m-%d"))
            codes = []
            while rs.error_code == "0" and rs.next():
                codes.append(_row_to_dict(rs).get("code", ""))
            return codes

    def get_zz500_stocks(self, date: Optional[str] = None) -> List[str]:
        """获取中证500成分股。"""
        with baostock_login_context():
            rs = bs.query_zz500_stocks(date or datetime.now().strftime("%Y-%m-%d"))
            codes = []
            while rs.error_code == "0" and rs.next():
                codes.append(_row_to_dict(rs).get("code", ""))
            return codes

    def get_sz50_stocks(self, date: Optional[str] = None) -> List[str]:
        """获取上证50成分股。"""
        with baostock_login_context():
            rs = bs.query_sz50_stocks(date or datetime.now().strftime("%Y-%m-%d"))
            codes = []
            while rs.error_code == "0" and rs.next():
                codes.append(_row_to_dict(rs).get("code", ""))
            return codes
