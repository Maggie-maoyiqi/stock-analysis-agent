"""宏观经济工具函数。"""
import logging

logger = logging.getLogger(__name__)


def get_deposit_rate_data(start_date: str, end_date: str) -> str:
    """获取存款利率数据。"""
    return """## 基准存款利率

| 期限 | 利率 |
|------|------|
| 活期 | 0.35% |
| 3个月 | 1.10% |
| 6个月 | 1.30% |
| 1年 | 1.50% |
| 2年 | 2.10% |
| 3年 | 2.75% |

*数据仅供参考，实际利率以央行公布为准*
"""


def get_loan_rate_data(start_date: str, end_date: str) -> str:
    """获取贷款利率数据。"""
    return """## 基准贷款利率

| 期限 | 利率 |
|------|------|
| 1年以内 | 4.35% |
| 1-5年 | 4.75% |
| 5年以上 | 4.90% |

*数据仅供参考*
"""


def get_money_supply_data_month(start_date: str, end_date: str) -> str:
    """获取月度货币供应量数据（M0、M1、M2）。"""
    return """## 货币供应量数据

| 指标 | 含义 | 当前趋势 |
|------|------|----------|
| M0 | 流通中现金 | 平稳增长 |
| M1 | M0 + 企业活期存款 | 反映经济活跃度 |
| M2 | M1 + 准货币 | 广义货币供应量 |

*M2增速是观察货币政策松紧的重要指标*
"""


def get_required_reserve_ratio_data(start_date: str, end_date: str) -> str:
    """获取存款准备金率数据。"""
    return """## 存款准备金率

大型金融机构: 10.0%
中小型金融机构: 8.0%

*降准意味着市场资金变多，利好股市*
"""
