"""数据源工厂。"""
from .baostock_data_source import BaostockDataSource
from .market_utils import detect_market
from .yfinance_data_source import YFinanceDataSource

_baostock_source = BaostockDataSource()
_yfinance_source = YFinanceDataSource()


def get_data_source(stock_code: str):
    """根据股票代码路由到对应数据源。"""
    market = detect_market(stock_code)
    if market == "cn":
        return _baostock_source
    return _yfinance_source
