# Stock Analysis Agent

一个面向个人投资研究的多 Agent 股票分析系统。

这个项目把股票分析、用户档案、自选股跟踪、持仓体检、每日简报和预测能力整合在同一套工作流里，适合作为：

- 个人投资研究助手
- 多 Agent 金融分析项目
- 更上层个人 AI 系统的底层股票引擎

## 核心功能

### 多 Agent 个股分析

系统围绕一只股票并行运行多个分析 Agent：

- 基本面 Agent
- 技术面 Agent
- 估值 Agent
- 新闻 Agent
- 预测 Agent
- 汇总 Agent

输出维度包括：

- 盈利能力、成长性、偿债能力、现金流
- K 线趋势、量价关系、关键价位
- PE / PB / 分红等估值线索
- 新闻情绪与风险摘要
- 短期走势预测
- 最终综合投资报告

### 用户档案与持仓管理

系统支持维护个人投资档案：

- 风险偏好
- 自选股列表
- 持仓信息
- 止损 / 止盈参数
- 早报 / 晚报时间

### 每日简报

支持生成：

- 早报
- 晚报

简报内容包括：

- 海外与宏观速览
- 自选股观察
- 持仓体检
- 稳健风格推荐股票
- 风险提示

### 推荐闭环

推荐结果不仅能展示，还能直接形成动作：

- 一键加入自选
- 快速录入持仓

### 可视化进度

前端会显示：

- 总体进度条
- 每个 Agent 的独立进度条
- 当前运行阶段说明

例如：

- 查询财务与分红数据
- 查询历史 K 线
- 生成估值分析
- 生成综合报告

## 技术栈

### 后端

- Python
- FastAPI
- LangGraph
- MCP

### 前端

- React
- Vite

### 数据与工具层

- Baostock
- yfinance

## 适用市场

- A 股：主战场，支持最完整
- 港股 / H 股：弱化分析，更多作为联动参考
- 美股：弱化分析，更多作为情绪与宏观参考

## 项目结构

```text
stock-analysis-agent/
├── Financial-MCP-Agent/            # 主应用：前后端 + Agent 工作流
│   ├── backend/
│   ├── frontend/
│   ├── data/
│   ├── reports/
│   └── src/
├── a-share-mcp-is-just-i-need/     # MCP 数据服务层
│   ├── mcp_server.py
│   └── src/
├── outputs/
├── openclaw_spec.md
└── README.md
```

## 环境要求

- Python 3.10+
- Node.js 18+
- 可访问 Baostock / yfinance 数据源的网络环境
- OpenAI 兼容模型 API Key（用于生成分析报告）

## 启动方式

以下命令均从仓库根目录执行。请先克隆项目并进入目录：

```bash
git clone <your-repository-url> stock-analysis-agent
cd stock-analysis-agent
```

### 1. 创建虚拟环境

```bash
python -m venv .venv
source .venv/bin/activate
```

Windows PowerShell 使用：

```bash
.venv\Scripts\Activate.ps1
```

### 2. 安装 Python 依赖

```bash
python -m pip install -U pip
pip install -r requirements.txt
```

根目录的 `requirements.txt` 会自动聚合安装：

- `Financial-MCP-Agent/requirements.txt`
- `a-share-mcp-is-just-i-need/requirements.txt`

不需要、也不应该把 README 写成某个开发者本机的绝对路径。

TensorFlow 仅用于 TCN 预测，在 Python 3.13 环境中会自动跳过并使用轻量回归预测，不影响其余功能。

### 3. 安装前端依赖

```bash
npm --prefix Financial-MCP-Agent/frontend install
```

### 4. 配置环境变量

```bash
cp Financial-MCP-Agent/.env.example Financial-MCP-Agent/.env
```

至少需要配置：

```bash
OPENAI_COMPATIBLE_API_KEY=你的key
OPENAI_COMPATIBLE_BASE_URL=https://api.deepseek.com
MODEL_NAME=deepseek-chat
A_SHARE_MCP_PATH=../a-share-mcp-is-just-i-need
FRONTEND_ORIGIN=http://localhost:5173
```

配置完成后，可先执行自检：

```bash
python scripts/smoke_test.py
```

### 5. 启动后端

```bash
cd Financial-MCP-Agent
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### 6. 启动前端

另开一个终端，在仓库根目录执行：

```bash
npm --prefix Financial-MCP-Agent/frontend run dev
```

### 7. 访问地址

- 前端：[http://localhost:5173](http://localhost:5173)
- 后端健康检查：[http://localhost:8000/api/health](http://localhost:8000/api/health)
- 分析任务 SSE 状态流：`GET /api/analysis/{task_id}/stream`

## 命令行模式

如果你只想用 CLI：

```bash
cd Financial-MCP-Agent
python main.py --command "帮我分析贵州茅台"
python main.py --interactive
```

## 推荐使用场景

- 每天自动生成投资早报和晚报
- 跟踪自选股和持仓变化
- 对单只股票做多维度分析
- 把底层股票能力接入更大的个人 AI 系统

## 项目定位

这个项目不是券商交易系统，也不是高频量化交易系统。  
它更适合被理解成：

> 一个面向个人投资研究的多 Agent 决策辅助系统。

## 免责声明

本项目输出仅供研究、学习和决策辅助，不构成任何投资建议。投资有风险，入市需谨慎。
