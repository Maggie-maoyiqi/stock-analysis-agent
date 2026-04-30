# GitHub 发布前联调清单

这份清单的目标很简单：保证你把项目推到 GitHub 后，别人按 README 能把它跑起来。

## 一、环境准备

### 1. 确认目录结构

项目默认假设这两个目录并列存在：

```text
/Users/maoyiqi/stock_mock/
├── Financial-MCP-Agent
└── a-share-mcp-is-just-i-need
```

### 2. 创建全新虚拟环境

```bash
cd /Users/maoyiqi/stock_mock
python -m venv .venv
source .venv/bin/activate
```

### 3. 安装依赖

```bash
cd /Users/maoyiqi/stock_mock/a-share-mcp-is-just-i-need
pip install -U pip
pip install -r requirements.txt

cd /Users/maoyiqi/stock_mock/Financial-MCP-Agent
pip install -r requirements.txt

cd /Users/maoyiqi/stock_mock/Financial-MCP-Agent/frontend
npm install
```

### 4. 配置模型密钥

```bash
cd /Users/maoyiqi/stock_mock/Financial-MCP-Agent
cp .env.example .env
```

至少检查这些值：

```bash
OPENAI_COMPATIBLE_API_KEY=你的key
OPENAI_COMPATIBLE_BASE_URL=https://api.deepseek.com
MODEL_NAME=deepseek-chat
A_SHARE_MCP_PATH=../a-share-mcp-is-just-i-need
FRONTEND_ORIGIN=http://localhost:5173
```

## 二、静态检查

### 1. Python 语法检查

```bash
python -m compileall /Users/maoyiqi/stock_mock/Financial-MCP-Agent /Users/maoyiqi/stock_mock/a-share-mcp-is-just-i-need
```

预期：无报错。

### 2. 前端打包检查

```bash
cd /Users/maoyiqi/stock_mock/Financial-MCP-Agent/frontend
npm run build
```

预期：`built in ...`。

## 三、启动检查

### 1. 启动后端

推荐：

```bash
cd /Users/maoyiqi/stock_mock/Financial-MCP-Agent
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. 启动前端

另开一个终端：

```bash
source /Users/maoyiqi/stock_mock/.venv/bin/activate
cd /Users/maoyiqi/stock_mock/Financial-MCP-Agent/frontend
npm run dev
```

### 3. 健康检查

浏览器打开：

- [http://localhost:8000/api/health](http://localhost:8000/api/health)

预期返回：

```json
{"status":"ok"}
```

## 四、真实联网联调

这一步最重要，因为推荐、简报和市场快照都依赖真实数据。

### 1. 单票分析

在前端输入：

- `帮我分析贵州茅台`

预期：

- 成功创建任务
- 进度条推进
- 最终生成综合报告

### 2. 用户档案

在“用户档案”里：

- 新增一只自选股，例如 `sh.600519`
- 新增一笔持仓，例如：
  - 股票代码：`sh.600519`
  - 成本价：`1688`
  - 数量：`100`
  - 买入日期：当天或历史日期

预期：

- 自选股列表立即刷新
- 持仓列表立即刷新

### 3. 早报生成

点击“生成早报”。

预期：

- 返回 `watchlist_reviews`
- 返回 `position_reviews`
- 返回 `recommendations`
- 生成 Markdown 文件到 `reports/briefs/`
- 如果 `python-docx` 安装正常，同时生成 `.docx`

### 4. 晚报生成

点击“生成晚报”。

预期：

- 同样生成一份独立的简报文件

### 5. 推荐闭环

在“推荐买入 5 只”区域：

- 点击“加入自选”
- 再选一只点击“录入持仓”

预期：

- 档案面板里的自选股新增对应股票
- 档案面板里的持仓新增对应股票
- 下一次生成简报时，这些股票进入观察/体检区域

## 五、日志与输出检查

### 1. 报告目录

检查：

```bash
ls /Users/maoyiqi/stock_mock/Financial-MCP-Agent/reports/briefs
```

预期：

- 有 `.md`
- 环境完整时有 `.docx`

### 2. 用户档案文件

检查：

```bash
cat /Users/maoyiqi/stock_mock/Financial-MCP-Agent/data/user_profile.json
```

预期：

- 自选股和持仓已持久化

## 六、推 GitHub 前最后确认

### 必须确认

- `.env` 没有提交
- `.venv` 没有提交
- `node_modules` 没有提交
- README 与当前启动方式一致
- 至少保留一份本机生成成功的早报或晚报作为验收依据

### 推荐执行

```bash
git status
```

确保：

- 没有不该提交的本地密钥
- 没有误提交大文件或缓存目录

## 七、如果出问题，优先排查这几类

### 1. 后端启动了但页面请求失败

优先检查：

- `FRONTEND_ORIGIN`
- 后端是否跑在 `8000`
- 前端是否跑在 `5173`

### 2. 简报能生成但没有推荐

优先检查：

- 当前机器能否访问外网
- `yfinance` 是否能取数
- `baostock` 是否能登录

### 3. 只有 Markdown 没有 Word

优先检查：

```bash
pip show python-docx
```

如果没装：

```bash
cd /Users/maoyiqi/stock_mock/Financial-MCP-Agent
pip install -r requirements.txt
```

### 4. 出现 `torch/cuda` 或 `pynvml` warning

这通常不是本项目本身的问题，而是你当前 Python 环境里混入了额外的深度学习包。  
如果功能正常，可以先忽略；如果想更干净，建议重新建虚拟环境再安装。
