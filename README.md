# ASIN 智能健康度分析平台

基于 **Strands Agents SDK** 的 Multi-Agent 系统，为 Amazon 卖家提供 ASIN 健康度评分、根因分析和行动建议。

## 核心设计

- **确定性评分 + AI 解读**：评分用公式计算（可重复、可审计），LLM 负责根因分析和行动建议
- **六维度加权评分**：销量、库存、广告、售后、盈利性、Listing 质量
- **生命周期动态权重**：新品期/成长期/成熟期/衰退期各有不同权重
- **短板一票否决**：任一维度极低时强制降级

## 架构

```
用户请求
  │
  ▼
┌─────────────────────────────────┐
│     FastAPI REST API            │
│   POST /chat  GET /scores/...   │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│   Supervisor Agent (Sonnet 4.6)  │
│   协调 5 个 Sub-Agent            │
└──┬──────┬──────┬──────┬──────┬──┘
   │      │      │      │      │
   ▼      ▼      ▼      ▼      ▼
┌─────┐┌─────┐┌─────┐┌─────┐┌─────┐
│评分  ││根因  ││行动  ││竞品  ││知识  │
│查询  ││分析  ││建议  ││分析  ││检索  │
│Agent ││Agent ││Agent ││Agent ││Agent │
│(Nova)││(Son.)││(Son.)││(Nova)││(Nova)│
└──┬───┘└──┬───┘└──┬───┘└──┬───┘└──┬───┘
   │       │       │       │       │
   ▼       ▼       ▼       ▼       ▼
┌─────────────────────────────────┐
│   @tool 函数层                   │
│  score_tools / metrics_tools /   │
│  benchmark_tools / knowledge_tools│
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│   数据层                         │
│  本地 JSON / DynamoDB / S3       │
└─────────────────────────────────┘
```

### Sub-Agent 职责

| Agent | 模型 | 职责 |
|-------|------|------|
| 评分查询 Agent | Nova Pro | 查询 ASIN 评分、统计摘要、按标签筛选 |
| 根因分析 Agent | Sonnet 4.6 | 多维度关联推理，找出评分异常根因 |
| 行动建议 Agent | Sonnet 4.6 | 输出可执行行动计划和 SOP |
| 竞品分析 Agent | Nova Pro | 类目基准对比、竞争力评估 |
| 知识检索 Agent | Nova Pro | 运营知识库 RAG 检索 |

## 评分体系

### 六维度加权
综合健康度 = 销量(25%) + 库存(20%) + 广告(15%) + 售后(15%) + 盈利性(15%) + Listing(10%)

### 健康标签
| 标签 | 分数范围 |
|------|----------|
| 健康 (healthy) | 80-100 |
| 预警 (warning) | 60-79 |
| 异常 (abnormal) | 40-59 |
| 危险 (danger) | 0-39 |

### 短板否决
- 任一维度 < 20 → 综合分上限 30（强制「危险」）
- 任一维度 < 40 → 综合分上限 50（最多「预警」）
- 两个维度 < 60 → 综合分上限 55（最多「预警」）

## 快速开始

### 前置条件
- Python 3.12+
- [uv](https://docs.astral.sh/uv/) 包管理器
- AWS 凭证（配置 Bedrock 访问权限，Region: us-east-1）

### 安装

```bash
git clone <repo-url>
cd asin-health-platform
uv sync
```

### 1. 生成模拟数据

```bash
uv run python -m src.data.generate_mock_data
```

生成 100 个 ASIN 的模拟指标数据到 `data/raw/`。

### 2. 计算评分

```bash
uv run python -m src.data.scoring_engine
```

对所有 ASIN 执行六维度评分，结果保存到 `data/scores/all_scores.json`。

### 3. 上传到 AWS（可选）

```bash
# 预览上传计划
uv run python -m src.data.upload_data --dry-run

# 执行上传
uv run python -m src.data.upload_data
```

### 4. 启动 API 服务

```bash
uv run uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

### 5. 命令行交互

```bash
uv run python main.py
```

## API 文档

启动服务后访问: `http://localhost:8000/docs`（自动生成 Swagger UI）

### 端点

#### GET /health
健康检查。

```bash
curl http://localhost:8000/health
```

#### POST /chat
与 Supervisor Agent 对话。

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "查询 B000000008 的健康度评分"}'
```

#### GET /scores/{asin_id}
查询单个 ASIN 评分。

```bash
curl http://localhost:8000/scores/B000000008
```

#### GET /scores
查询评分列表，支持过滤。

```bash
# 所有评分
curl http://localhost:8000/scores

# 按健康标签筛选
curl "http://localhost:8000/scores?health_label=danger"

# 按生命周期筛选
curl "http://localhost:8000/scores?lifecycle=new&limit=10"
```

## 项目结构

```
asin-health-platform/
├── src/
│   ├── api/               # FastAPI REST API
│   │   └── main.py
│   ├── data/              # 数据生成和评分
│   │   ├── generate_mock_data.py
│   │   ├── scoring_engine.py
│   │   └── upload_data.py
│   ├── tools/             # @tool 函数（Agent 可调用）
│   │   ├── score_tools.py
│   │   ├── metrics_tools.py
│   │   ├── benchmark_tools.py
│   │   └── knowledge_tools.py
│   └── agents/            # Agent 定义
│       ├── supervisor_agent.py
│       ├── score_query_agent.py
│       ├── root_cause_agent.py
│       ├── action_advisor_agent.py
│       ├── competitor_agent.py
│       └── knowledge_agent.py
├── data/                  # 本地数据文件
│   ├── raw/               # 原始模拟指标
│   ├── scores/            # 评分结果
│   ├── benchmarks/        # 类目基准
│   └── knowledge_docs/    # 运营知识文档
├── tests/
│   ├── test_tools.py      # 工具函数测试
│   ├── test_agents.py     # Agent 创建测试
│   ├── test_api.py        # API 端点测试
│   └── test_e2e.py        # 端到端集成测试
├── main.py                # 命令行交互入口
├── pyproject.toml
└── README.md
```

## 开发指南

### 运行测试

```bash
uv run pytest tests/ -v
```

### 代码规范
- Python 3.12，完整类型注解
- 中文注释
- JSON 输出用 Pydantic 模型定义

### Tech Stack
- **Strands Agents SDK** — Multi-Agent 框架
- **AWS Bedrock** — Claude Sonnet 4.6 + Nova Pro
- **FastAPI** — REST API
- **DynamoDB** — 评分存储
- **S3** — 原始数据和知识库
