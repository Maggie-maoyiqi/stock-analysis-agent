"""指数工具函数。"""
import logging
from datetime import datetime

from ..baostock_data_source import BaostockDataSource
from ..data_source_factory import get_data_source
from ..market_utils import detect_market

logger = logging.getLogger(__name__)
data_source = BaostockDataSource()


def _build_code_table(title: str, date: str, stocks: list[str], limit: int = 50) -> str:
    table = f"## {title} ({date})\n\n"
    table += "| 序号 | 股票代码 |\n"
    table += "|------|----------|\n"
    for i, code in enumerate(stocks[:limit], 1):
        table += f"| {i} | {code} |\n"
    if len(stocks) > limit:
        table += f"\n*共{len(stocks)}只股票，仅显示前{limit}只*"
    return table


def get_hs300_stocks(date: str = None) -> str:
    """获取沪深300指数成分股。"""
    date = date or datetime.now().strftime("%Y-%m-%d")
    stocks = data_source.get_hs300_stocks(date)
    if not stocks:
        return f"未获取到 {date} 的沪深300成分股数据"
    return _build_code_table("沪深300成分股", date, stocks)


def get_zz500_stocks(date: str = None) -> str:
    """获取中证500指数成分股。"""
    date = date or datetime.now().strftime("%Y-%m-%d")
    stocks = data_source.get_zz500_stocks(date)
    if not stocks:
        return f"未获取到 {date} 的中证500成分股数据"
    return _build_code_table("中证500成分股", date, stocks)


def get_sz50_stocks(date: str = None) -> str:
    """获取上证50成分股。"""
    date = date or datetime.now().strftime("%Y-%m-%d")
    stocks = data_source.get_sz50_stocks(date)
    if not stocks:
        return f"未获取到 {date} 的上证50成分股数据"
    return _build_code_table("上证50成分股", date, stocks)


def get_stock_industry(stock_code: str = None) -> str:
    """获取股票行业分类数据。"""
    if stock_code and detect_market(stock_code) != "cn":
        data_source = get_data_source(stock_code)
        info = data_source.get_stock_basic_info(stock_code)
        return f"""## 行业分类

| 项目 | 值 |
|------|------|
| 股票代码 | {info.get('code', stock_code)} |
| 股票名称 | {info.get('name', 'N/A')} |
| 行业 | {info.get('industry', 'N/A')} |
| 板块 | {info.get('sector', 'N/A')} |
| 交易所 | {info.get('exchange', 'N/A')} |
"""
    stock_hint = f"\n\n当前查询股票: {stock_code}" if stock_code else ""
    return f"""## 申万行业分类说明

A股行业主要分为：
- **食品饮料**：茅台、五粮液等
- **医药生物**：恒瑞医药、迈瑞医疗等
- **电子**：立讯精密、京东方等
- **计算机**：海康威视、科大讯飞等
- **银行**：工商银行、招商银行等
- **非银金融**：中信证券、中国平安等
- **新能源**：宁德时代、隆基绿能等{stock_hint}
"""
