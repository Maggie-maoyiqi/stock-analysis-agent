# 📊 Financial MCP Agent

基于 `LangGraph + FastAPI + React + MCP` 的股票分析与个人投资跟踪系统。  
当前版本包含两条主线：

- 单只股票多 Agent 分析：基本面、技术面、估值、新闻、走势预测、综合报告
- OpenClaw Daily Brief：用户档案、自选股跟踪、持仓体检、早报/晚报、稳健风格推荐

## ✨ 当前功能

### 多 Agent 分析

- 基本面分析：盈利能力、成长性、偿债能力、现金流、分红
- 技术面分析：K 线趋势、均线结构、量价关系、支撑/压力
- 估值分析：PE / PB / 分红 / 行业对比
- 新闻分析：舆情、风险、情绪摘要
- 走势预测：下一交易日方向和参考涨跌幅
- 综合报告：生成 Markdown 报告

### Daily Brief

- 用户档案：风险偏好、自选股、持仓、早晚报时间
- 自选股观察：近期涨幅、20 日波动率、综合分、建议动作
- 持仓体检：继续持有 / 减仓 / 清仓建议
- 主动推荐：稳健风格下推荐 5 只 A 股候选
- 早报 / 晚报：同时导出 Markdown，环境完整时可导出 Word
- 前端闭环：推荐股票可直接加入自选或录入持仓

## 🏗️ 项目结构

```text
stock_mock/
├── Financial-MCP-Agent/
│   ├── backend/                 # FastAPI 后端
│   ├── frontend/                # React 前端
│   ├── data/                    # 用户档案
│   ├── reports/briefs/          # 简报输出
│   ├── src/
│   │   ├── agents/              # 多 Agent 分析
│   │   ├── services/            # 分析、档案、简报、推荐服务
│   │   └── tools/               # MCP 客户端与配置
│   ├── main.py                  # CLI 入口
│   └── README.md
└── a-share-mcp-is-just-i-need/
    ├── mcp_server.py            # MCP 服务端
    └── src/tools/               # 数据/预测/简报工具
```

## 🌍 市场支持

- A 股：主战场，工具最完整，推荐和简报以 A 股为主
- 港股 / H 股：弱化分析，主要用于联动参考与用户主动跟踪
- 美股：弱化分析，主要用于隔夜情绪、指数和龙头联动参考

## 🧩 技术架构

### 分析链路

```text
用户输入
  ↓
提取股票代码
  ↓
5 个 Agent 并行
  ↓
汇总 Agent
  ↓
Markdown 报告
```

### Daily Brief 链路

```text
用户档案
  ↓
市场环境 + 自选股快照 + 持仓体检 + 稳健推荐
  ↓
早报 / 晚报
  ↓
Markdown / Word
```

## 📋 环境要求

- Python 3.10+
- Node.js 18+
- 建议全新虚拟环境
- 模型 API Key

## 🚀 启动方式

### 1. 创建虚拟环境

```bash
cd /Users/maoyiqi/stock_mock
python -m venv .venv
source .venv/bin/activate
```

### 2. 安装 MCP 服务端依赖

```bash
cd /Users/maoyiqi/stock_mock/a-share-mcp-is-just-i-need
pip install -U pip
pip install -r requirements.txt
```

### 3. 安装 Agent 后端依赖

```bash
cd /Users/maoyiqi/stock_mock/Financial-MCP-Agent
pip install -r requirements.txt
```

### 4. 安装前端依赖

```bash
cd /Users/maoyiqi/stock_mock/Financial-MCP-Agent/frontend
npm install
```

### 5. 配置 `.env`

```bash
cd /Users/maoyiqi/stock_mock/Financial-MCP-Agent
cp .env.example .env
```

DeepSeek 示例：

```bash
OPENAI_COMPATIBLE_API_KEY=你的key
OPENAI_COMPATIBLE_BASE_URL=https://api.deepseek.com
MODEL_NAME=deepseek-chat
A_SHARE_MCP_PATH=../a-share-mcp-is-just-i-need
FRONTEND_ORIGIN=http://localhost:5173
```

### 6. 启动后端

推荐方式：

```bash
cd /Users/maoyiqi/stock_mock/Financial-MCP-Agent
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

现在也支持：

```bash
cd /Users/maoyiqi/stock_mock/Financial-MCP-Agent/backend
python main.py
```

### 7. 启动前端

```bash
cd /Users/maoyiqi/stock_mock/Financial-MCP-Agent/frontend
npm run dev
```

### 8. 访问地址

- 前端：[http://localhost:5173](http://localhost:5173)
- 后端健康检查：[http://localhost:8000/api/health](http://localhost:8000/api/health)

## 🖥️ CLI 模式

```bash
cd /Users/maoyiqi/stock_mock/Financial-MCP-Agent
python main.py --command "帮我分析贵州茅台"
python main.py --interactive
```

## 📡 API

### 分析接口

- `GET /api/health`
- `POST /api/analysis`
- `GET /api/analysis/{task_id}`

### 用户档案接口

- `GET /api/profile`
- `PUT /api/profile`
- `POST /api/profile/watchlist`
- `DELETE /api/profile/watchlist/{stock_code}`
- `POST /api/profile/positions`
- `DELETE /api/profile/positions/{stock_code}`

### 简报接口

- `POST /api/briefs/generate`

## 📄 输出文件

- 单票分析报告：`Financial-MCP-Agent/reports/*.md`
- 每日简报 Markdown：`Financial-MCP-Agent/reports/briefs/*.md`
- 每日简报 Word：`Financial-MCP-Agent/reports/briefs/*.docx`

## ⚠️ 运行说明

- 推荐和简报的完整效果依赖真实联网数据
- 当前实现中 A 股推荐最完整；港股、美股主要作辅助参考
- Word 导出依赖 `python-docx`
- 预测模块优先尝试 TCN 风格预测；在某些环境下可回退到轻量逻辑

## ⚠️ 你刚才看到的 `torch/cuda` Warning 是什么

如果你执行 `python main.py` 或运行某些环境里的 Python，看到类似：

```text
FutureWarning: The pynvml package is deprecated...
```

这通常表示：

- 你的 Python 环境里额外装了 `torch` 或相关 GPU 监控包
- 这不是本项目核心依赖
- 这是警告，不是本项目启动失败的根因

真正要注意的是：

- 后端应从 `Financial-MCP-Agent` 目录启动
- 推荐用 `uvicorn backend.main:app --reload`
- 如果你在 `backend/` 子目录直接跑 `python3 main.py`，现在也能启动，但不如标准方式稳定

## ✅ GitHub 发布前建议

请在推送前至少完成一次：

1. 后端健康检查通过
2. 前端页面能打开
3. 创建一次单票分析任务
4. 生成一次早报
5. 从推荐里加入一只自选股
6. 录入一笔持仓

详细步骤见：

- [GITHUB_RELEASE_CHECKLIST.md](/Users/maoyiqi/stock_mock/Financial-MCP-Agent/GITHUB_RELEASE_CHECKLIST.md)

## ⚠️ 免责声明

本系统输出仅供研究和决策辅助，不构成投资建议。股市有风险，投资需谨慎。
