# CLAUDE.md - ASIN Health Platform

## Project Overview
ASIN 智能健康度分析平台 — 基于 Strands Agents SDK 的 Multi-Agent 系统。

### 核心设计原则
- **确定性评分 + AI 解读**：评分用公式计算（可重复、可审计），LLM 负责根因分析和行动建议
- **Multi-Agent 架构**：Strands Agents SDK，Agents as Tools 模式
- **模拟数据驱动**：先用构造数据验证 Agent 协作，不需要真实 SP-API

## Tech Stack
- **Python 3.12** (uv 管理)
- **Strands Agents SDK** (`strands-agents`, `strands-agents-tools`)
- **AWS Bedrock FM**: Claude Sonnet 4.6 (推理), Nova Pro (简单查询)
- **存储**: DynamoDB (评分), S3 (原始指标/知识库), Bedrock Knowledge Base (RAG)
- **运行**: `uv run python ...`

## 项目结构
```
asin-health-platform/
├── src/
│   ├── data/              # 模拟数据生成和评分计算
│   │   ├── generate_mock_data.py    # 生成 100 ASIN 模拟数据
│   │   ├── scoring_engine.py        # 确定性评分公式
│   │   └── upload_data.py           # 上传到 DynamoDB/S3
│   ├── tools/             # Strands @tool 函数（Agent 可调用的工具）
│   │   ├── score_tools.py           # 评分查询工具
│   │   ├── metrics_tools.py         # 原始指标查询工具
│   │   ├── benchmark_tools.py       # 类目基准/竞品工具
│   │   └── knowledge_tools.py       # 知识库检索工具
│   ├── agents/            # Agent 定义
│   │   ├── score_query_agent.py     # 评分查询 Agent (Nova Pro)
│   │   ├── root_cause_agent.py      # 根因分析 Agent (Sonnet 4.6)
│   │   ├── action_advisor_agent.py  # 行动建议 Agent (Sonnet 4.6)
│   │   ├── competitor_agent.py      # 竞品分析 Agent (Nova Pro)
│   │   ├── knowledge_agent.py       # 知识检索 Agent (Nova Pro)
│   │   └── supervisor_agent.py      # Supervisor Agent (Sonnet 4.6)
│   ├── api/               # API 接口
│   │   └── main.py
│   └── knowledge_base/    # KB 配置
│       └── setup_kb.py
├── data/                  # 本地数据文件
│   ├── raw/               # 原始模拟指标
│   ├── processed/         # 处理后的指标
│   ├── scores/            # 评分结果
│   ├── benchmarks/        # 类目基准
│   └── knowledge_docs/    # 运营知识文档
├── tests/
├── scripts/               # 工具脚本
├── CLAUDE.md
└── pyproject.toml
```

## 评分体系（方案文档核心）

### 六维度加权评分
综合健康度 = 销量(25%) + 库存(20%) + 广告(15%) + 售后(15%) + 盈利性(15%) + Listing质量(10%)

### 生命周期动态权重
| 阶段 | 判断标准 | 销量 | 库存 | 广告 | 售后 | 盈利 | Listing |
|---|---|---|---|---|---|---|---|
| 新品期 | 上架<90天 | 15% | 15% | 20% | 10% | 10% | 30% |
| 成长期 | 90-365天,销量上升 | 25% | 20% | 20% | 10% | 15% | 10% |
| 成熟期 | >365天,销量稳定 | 25% | 20% | 15% | 15% | 15% | 10% |
| 衰退期 | 连续60天销量下降 | 20% | 25% | 10% | 15% | 20% | 10% |

### 短板一票否决
- 任一维度 < 20：综合分 = min(综合分, 30) → 强制「危险」
- 任一维度 < 40：综合分 = min(综合分, 50) → 最多「预警」
- 两个及以上维度 < 60：综合分 = min(综合分, 55) → 最多「预警」

### 健康标签
- 🟢 健康: 80-100
- 🟡 预警: 60-79
- 🟠 异常: 40-59
- 🔴 危险: 0-39

## Agent 架构（Strands Agents as Tools 模式）

### Supervisor Agent (Claude Sonnet 4.6)
- 接收用户请求，分解任务，协调 sub-agent
- 将 5 个 sub-agent 注册为 @tool

### Sub-Agents
1. **评分查询 Agent** (Nova Pro) — 查 DynamoDB 评分数据
2. **根因分析 Agent** (Sonnet 4.6) — 多因素关联推理
3. **行动建议 Agent** (Sonnet 4.6) — 输出可执行行动计划
4. **竞品分析 Agent** (Nova Pro) — 类目基准和竞品对比
5. **知识检索 Agent** (Nova Pro) — RAG 运营知识库

### FM 模型 ID
- Claude Sonnet 4.6: `us.anthropic.claude-sonnet-4-6-v1`（Cross-Region）
- Nova Pro: `us.amazon.nova-pro-v1:0`
- Titan Embeddings V2: `amazon.titan-embed-text-v2:0`

## 模拟数据规格

### 100 个 ASIN 分布
- 25 个新品期 + 30 个成长期 + 30 个成熟期 + 15 个衰退期
- 健康标签分布: ~30% 健康, ~30% 预警, ~25% 异常, ~15% 危险
- 至少 10 个 ASIN 有"多维度关联异常"（用于测试根因分析）

### 数据字段
每个 ASIN 需要以下原始指标（7 天 + 30 天历史）：
- **销量**: daily_orders, daily_sales_amount, sessions, cvr, bsr, bsr_category
- **库存**: fba_available, fba_inbound, days_of_supply, ipi_score, excess_inventory_pct, storage_cost_pct
- **广告**: ad_spend, ad_sales, acos, roas, cpc, ctr, ad_orders, total_orders
- **售后**: return_rate, avg_rating, review_count, recent_negative_pct, atoz_claims, policy_warnings
- **盈利**: selling_price, fba_fee, referral_fee, ad_cost_per_unit, cogs, shipping_cost, gross_margin
- **Listing**: title_score, image_count, has_aplus, bullet_count, search_terms_filled, buybox_pct

### 知识库文档（data/knowledge_docs/）
需要准备 5-10 个 Markdown 文档：
- 季节性规律.md（大促前后正常波动模式）
- 常见异常模式.md（销量+差评关联、广告+CPC 关联等）
- 库存管理SOP.md
- 广告优化SOP.md
- Listing优化SOP.md
- 退货处理SOP.md
- Amazon政策更新.md

## 开发规范
- 所有代码用 Python 3.12
- 运行命令: `uv run python src/xxx.py`
- 类型注解完整
- 中文注释
- JSON 输出用 pydantic model 定义
- 错误处理完善
- AWS region: us-east-1
