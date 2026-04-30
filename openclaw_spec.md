# OpenClaw Daily Brief 扩展规格

## 目标

在现有 `Financial-MCP-Agent` 基础上新增一套面向个人投资跟踪的日报系统，核心能力包括：

1. 用户档案管理：风险偏好、自选股、持仓、推送时间。
2. 早报 / 晚报生成：输出 Word 简报。
3. 自选股跟踪：展示近期涨幅、波动率、估值、情绪和建议动作。
4. 持仓体检：输出继续持有 / 减仓 / 清仓建议。
5. 主动推荐：基于稳健风格，从 A 股候选池中推荐 5 只股票。
6. 非 A 股弱化分析：美股和港股作为宏观与联动参考，不主动做大规模挖掘。

## 风险偏好固定值

- 风格：`稳健`
- 推荐数量：`5`
- 主战场：`A股`
- 海外市场用途：情绪和联动参考

## 用户档案结构

文件：`Financial-MCP-Agent/data/user_profile.json`

```json
{
  "risk_preference": "稳健",
  "recommendation_count": 5,
  "primary_market": "cn",
  "active_markets": ["cn", "hk", "us"],
  "delivery_schedule": {
    "morning": "09:00",
    "evening": "21:00"
  },
  "watchlist": [],
  "positions": []
}
```

### watchlist item

```json
{
  "stock_code": "sh.600519",
  "stock_name": "贵州茅台",
  "market": "cn",
  "notes": "白马消费"
}
```

### position item

```json
{
  "stock_code": "sh.600519",
  "stock_name": "贵州茅台",
  "buy_price": 1688.0,
  "quantity": 100,
  "buy_date": "2026-04-20",
  "stop_loss_pct": 8.0,
  "take_profit_drawdown_pct": 15.0,
  "notes": "中线持有"
}
```

## 评分模型

### 自选股吸引力分

总分 `0-100`，权重固定：

- 基本面：40%
- 估值：20%
- 技术面：20%
- 消息/资金代理项：20%

### 稳健风格硬过滤

- ST / *ST 剔除
- 连续亏损剔除
- 上市不足 1 年剔除
- 小市值、纯题材炒作股不进入推荐池

### 推荐标签

- `>= 80`：买入
- `65 - 79`：继续观察
- `50 - 64`：中性
- `< 50`：回避

## 持仓决策树

- 浮亏小于 `-8%`：清仓
- 从阶段高点回撤超过 `15%`：减仓或止盈
- 技术破位且量能放大：减仓
- 基本面显著恶化：清仓
- 其余情况：继续持有

## 报告结构

### 早报

1. 日期与市场状态
2. 隔夜海外速览
3. A 股大盘预判
4. 自选股观察
5. 持仓体检
6. 今日推荐买入 5 只
7. 风险提示

### 晚报

1. 今日市场复盘
2. 自选股表现
3. 持仓盈亏变化
4. 热点题材总结
5. 明日策略
6. 前日推荐复盘

## 输出文件

- Markdown：`Financial-MCP-Agent/reports/briefs/*.md`
- Word：`Financial-MCP-Agent/reports/briefs/*.docx`

## 接口

- `GET /api/profile`
- `PUT /api/profile`
- `POST /api/profile/watchlist`
- `DELETE /api/profile/watchlist/{stock_code}`
- `POST /api/profile/positions`
- `DELETE /api/profile/positions/{stock_code}`
- `POST /api/briefs/generate`

## 备注

第一版以“可稳定生成简报”为目标，不一次性做全市场扫描。主动发现能力先从稳健候选池开始，后续再扩展到板块联动、龙虎榜、机构动向等模块。
