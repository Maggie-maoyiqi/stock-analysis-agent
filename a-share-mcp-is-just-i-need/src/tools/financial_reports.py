"""财务报表工具函数。"""
import logging

from ..data_source_factory import get_data_source

logger = logging.getLogger(__name__)


def get_profit_data(stock_code: str, year: int, quarter: int) -> str:
    """获取盈利能力数据。"""
    data_source = get_data_source(stock_code)
    data = data_source.get_profit_data(stock_code, year, quarter)
    if not data:
        return f"未获取到 {stock_code} {year}年Q{quarter} 的盈利能力数据"

    return f"""## {stock_code} 盈利能力数据 ({year}年Q{quarter})

| 指标 | 值 | 说明 |
|------|-----|------|
| ROE(净资产收益率) | {data.get('roe', 'N/A')}% | 越高越好，反映赚钱效率 |
| 净利润率 | {data.get('net_profit_rate', 'N/A')}% | 每元收入赚多少净利润 |
| 毛利率 | {data.get('gross_profit_rate', 'N/A')}% | 每元收入扣除成本后剩多少 |
| 每股收益(EPS) | {data.get('eps', 'N/A')}元 | 每股赚多少钱 |
"""


def get_growth_data(stock_code: str, year: int, quarter: int) -> str:
    """获取成长能力数据。"""
    data_source = get_data_source(stock_code)
    data = data_source.get_growth_data(stock_code, year, quarter)
    if not data:
        return f"未获取到 {stock_code} {year}年Q{quarter} 的成长能力数据"

    return f"""## {stock_code} 成长能力数据 ({year}年Q{quarter})

| 指标 | 同比增速 | 说明 |
|------|----------|------|
| 净利润增长率 | {data.get('yoy_net_profit', 'N/A')}% | 赚钱能力的增长 |
| 营业收入增长率 | {data.get('yoy_revenue', 'N/A')}% | 规模扩张速度 |
| EPS增长率 | {data.get('yoy_eps', 'N/A')}% | 每股收益增长 |
"""


def get_balance_data(stock_code: str, year: int, quarter: int) -> str:
    """获取资产负债表/偿债能力数据。"""
    data_source = get_data_source(stock_code)
    data = data_source.get_balance_data(stock_code, year, quarter)
    if not data:
        return f"未获取到 {stock_code} {year}年Q{quarter} 的资产负债表数据"

    debt_ratio = data.get("asset_debt_ratio", 0)
    debt_level = "健康" if debt_ratio < 0.5 else "较高" if debt_ratio < 0.7 else "危险"

    return f"""## {stock_code} 偿债能力数据 ({year}年Q{quarter})

| 指标 | 值 | 评估 |
|------|-----|------|
| 资产负债率 | {debt_ratio:.2%} | {debt_level} |
| 总资产 | {data.get('total_assets', 0):.2f}万元 | - |
| 总负债 | {data.get('total_liabilities', 0):.2f}万元 | - |
| 流动比率 | {data.get('current_ratio', 0)} | >2较安全 |

**资产负债率说明：** <50%健康，50-70%较高，>70%风险较大
"""


def get_cash_flow_data(stock_code: str, year: int, quarter: int) -> str:
    """获取现金流量数据。"""
    data_source = get_data_source(stock_code)
    data = data_source.get_cash_flow_data(stock_code, year, quarter)
    if not data:
        return f"未获取到 {stock_code} {year}年Q{quarter} 的现金流量数据"

    return f"""## {stock_code} 现金流量数据 ({year}年Q{quarter})

| 指标 | 值 | 说明 |
|------|-----|------|
| 经营性现金流 | {data.get('operating_cash_flow', 'N/A')}万元 | 主营业务产生的现金 |
| 自由现金流 | {data.get('free_cash_flow', 'N/A')}万元 | 可自由支配的现金 |
"""


def get_dupont_data(stock_code: str, year: int, quarter: int) -> str:
    """获取杜邦分析数据（ROE分解）。"""
    data_source = get_data_source(stock_code)
    profit = data_source.get_profit_data(stock_code, year, quarter)
    if not profit:
        return f"未获取到 {stock_code} 的杜邦分析数据"

    try:
        roe = float(profit.get("roe", 0) or 0)
    except (TypeError, ValueError):
        roe = 0

    if roe < 0:
        evaluation = "公司亏损，ROE为负"
    elif roe < 10:
        evaluation = "ROE偏低，赚钱效率一般"
    elif roe < 20:
        evaluation = "ROE良好，赚钱效率不错"
    else:
        evaluation = "ROE优秀，赚钱效率很高"

    return f"""## {stock_code} 杜邦分析 (ROE分解) ({year}年Q{quarter})

**ROE = 净利润率 × 总资产周转率 × 权益乘数**

| 指标 | 当前值 | 评估 |
|------|--------|------|
| ROE | {roe}% | {evaluation} |

**ROE说明：** 衡量股东资金的赚钱效率，>15%为优秀
"""
