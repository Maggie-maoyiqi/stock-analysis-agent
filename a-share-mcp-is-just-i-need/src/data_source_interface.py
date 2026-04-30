"""金融数据源抽象接口。"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class DataSourceError(Exception):
    """数据源异常。"""


class FinancialDataSource(ABC):
    """金融数据源抽象基类。"""

    @abstractmethod
    def get_historical_k_data(
        self,
        stock_code: str,
        start_date: str,
        end_date: str,
        frequency: str = "d",
        adjustflag: str = "2",
    ) -> List[Dict[str, Any]]:
        """获取历史K线数据。"""

    @abstractmethod
    def get_stock_basic_info(self, stock_code: str, fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """获取股票基本信息。"""

    @abstractmethod
    def get_profit_data(self, stock_code: str, year: int, quarter: int) -> Dict[str, Any]:
        """获取盈利能力数据。"""

    @abstractmethod
    def get_growth_data(self, stock_code: str, year: int, quarter: int) -> Dict[str, Any]:
        """获取成长能力数据。"""

    @abstractmethod
    def get_balance_data(self, stock_code: str, year: int, quarter: int) -> Dict[str, Any]:
        """获取资产负债表数据。"""

    @abstractmethod
    def get_cash_flow_data(self, stock_code: str, year: int, quarter: int) -> Dict[str, Any]:
        """获取现金流量数据。"""

    @abstractmethod
    def get_dividend_data(self, stock_code: str, year: int) -> List[Dict[str, Any]]:
        """获取分红数据。"""

    @abstractmethod
    def get_hs300_stocks(self, date: Optional[str] = None) -> List[str]:
        """获取沪深300成分股。"""

    @abstractmethod
    def get_zz500_stocks(self, date: Optional[str] = None) -> List[str]:
        """获取中证500成分股。"""

    @abstractmethod
    def get_sz50_stocks(self, date: Optional[str] = None) -> List[str]:
        """获取上证50成分股。"""
