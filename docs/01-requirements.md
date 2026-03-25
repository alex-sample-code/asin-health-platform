# ASIN 智能健康度分析平台 — 需求规格文档

> 文档编号：REQ-001
> 版本：v1.0
> 日期：2026-03-25
> 状态：初稿

---

## 目录

1. [功能需求清单](#1-功能需求清单)
2. [数据需求](#2-数据需求)
3. [评分规则规格](#3-评分规则规格)
4. [Agent 需求](#4-agent-需求)
5. [模拟数据需求](#5-模拟数据需求)
6. [API 接口需求](#6-api-接口需求)
7. [非功能需求](#7-非功能需求)

---

## 1. 功能需求清单

### 1.1 模拟数据生成模块

| 编号 | 功能名称 | 详细描述 | 输入 | 输出 | 优先级 | 所属模块 |
|------|----------|----------|------|------|--------|----------|
| FR-001 | 生成 ASIN 模拟数据 | 按照生命周期分布和健康标签分布，生成 100 个 ASIN 的完整原始指标数据（含 7 天 + 30 天历史） | 生成配置（ASIN 数量、分布比例） | JSON 文件，每个 ASIN 包含 6 维度全部原始指标 | P0 | src/data |
| FR-002 | 生成类目基准数据 | 为每个类目生成行业基准指标（P25/P50/P75/P90 分位值） | 类目列表 | 类目基准 JSON 文件 | P0 | src/data |
| FR-003 | 生成竞品数据 | 为部分 ASIN 生成 3-5 个竞品的关键指标数据 | ASIN 列表 | 竞品指标 JSON 文件 | P1 | src/data |
| FR-004 | 生成关联异常数据 | 构造至少 10 个多维度关联异常场景的 ASIN 数据，用于根因分析测试 | 异常场景定义 | 带标注的异常 ASIN 数据 | P0 | src/data |

### 1.2 评分计算模块

| 编号 | 功能名称 | 详细描述 | 输入 | 输出 | 优先级 | 所属模块 |
|------|----------|----------|------|------|--------|----------|
| FR-005 | 生命周期阶段判定 | 根据上架天数和销量趋势判定 ASIN 所处生命周期阶段 | ASIN 的 listing_age、近 60 天日销量序列 | 生命周期阶段枚举值（新品期/成长期/成熟期/衰退期） | P0 | src/data |
| FR-006 | 单维度评分计算 | 对 6 个维度分别计算 0-100 分 | ASIN 原始指标 + 类目基准 | 6 个维度分数（float, 0-100） | P0 | src/data |
| FR-007 | 动态权重计算 | 根据生命周期阶段返回对应的六维度权重 | 生命周期阶段 | 权重字典 {维度: 权重} | P0 | src/data |
| FR-008 | 综合分计算 | 加权求和 + 短板一票否决 + 趋势修正 | 6 个维度分数 + 权重 + 趋势数据 | 综合健康分（float, 0-100）+ 健康标签 | P0 | src/data |
| FR-009 | 批量评分 | 对全部 100 个 ASIN 批量运行评分 | ASIN 数据集 | 评分结果集（含维度分、综合分、标签） | P0 | src/data |

### 1.3 数据存储模块

| 编号 | 功能名称 | 详细描述 | 输入 | 输出 | 优先级 | 所属模块 |
|------|----------|----------|------|------|--------|----------|
| FR-010 | 上传评分到 DynamoDB | 将评分结果写入 DynamoDB 表 | 评分结果 JSON | DynamoDB 写入确认 | P1 | src/data |
| FR-011 | 上传原始指标到 S3 | 将原始指标数据上传到 S3 | 原始指标 JSON | S3 上传确认 | P1 | src/data |
| FR-012 | 上传知识文档到 S3 | 将运营知识 Markdown 文档上传到 S3 供 Knowledge Base 索引 | Markdown 文件目录 | S3 上传确认 | P1 | src/data |

### 1.4 Agent 工具模块

| 编号 | 功能名称 | 详细描述 | 输入 | 输出 | 优先级 | 所属模块 |
|------|----------|----------|------|------|--------|----------|
| FR-013 | 查询单 ASIN 评分 | 从 DynamoDB 查询指定 ASIN 的综合分和维度分 | asin_id: str | ScoreResult（综合分、6 维度分、标签、生命周期） | P0 | src/tools |
| FR-014 | 查询批量 ASIN 评分 | 批量查询多个 ASIN 评分，支持按标签/阶段筛选 | asin_ids: list[str] 或 filter: dict | list[ScoreResult] | P0 | src/tools |
| FR-015 | 查询 ASIN 原始指标 | 从 S3 获取指定 ASIN 的原始指标详情 | asin_id: str, dimension: str(可选) | MetricsResult（全部或指定维度的原始指标） | P0 | src/tools |
| FR-016 | 查询类目基准 | 获取指定类目的行业基准数据 | category: str | BenchmarkResult（各指标的 P25/P50/P75/P90） | P0 | src/tools |
| FR-017 | 查询竞品对比 | 获取指定 ASIN 的竞品指标对比 | asin_id: str | CompetitorResult（竞品列表及关键指标对比） | P1 | src/tools |
| FR-018 | 知识库检索 | 通过 Bedrock Knowledge Base 检索运营知识 | query: str, top_k: int(默认 3) | list[KnowledgeChunk]（相关文档片段及来源） | P0 | src/tools |

### 1.5 Agent 模块

| 编号 | 功能名称 | 详细描述 | 输入 | 输出 | 优先级 | 所属模块 |
|------|----------|----------|------|------|--------|----------|
| FR-019 | 评分查询 Agent | 理解用户查询意图，调用评分/指标工具返回结构化数据 | 用户自然语言查询 | 结构化评分数据 + 简要说明 | P0 | src/agents |
| FR-020 | 根因分析 Agent | 分析低分维度之间的关联关系，找出根本原因 | ASIN 评分 + 原始指标 + 类目基准 | 根因分析报告（根因链、置信度、关联维度） | P0 | src/agents |
| FR-021 | 行动建议 Agent | 根据根因分析结果，输出优先级排序的可执行行动计划 | 根因分析结果 + ASIN 基础信息 | 行动计划列表（优先级、预期效果、实施步骤） | P0 | src/agents |
| FR-022 | 竞品分析 Agent | 对比 ASIN 与竞品、类目基准，找出差距和优势 | ASIN 指标 + 竞品数据 + 类目基准 | 竞品分析报告（优劣势、差距量化、建议） | P1 | src/agents |
| FR-023 | 知识检索 Agent | 根据当前分析上下文检索相关运营知识 | 查询上下文（异常模式/维度/关键词） | 相关知识片段 + 引用来源 | P1 | src/agents |
| FR-024 | Supervisor Agent | 协调所有 sub-agent 完成用户请求的完整分析流程 | 用户自然语言请求 | 完整分析报告（评分+根因+建议+竞品+知识） | P0 | src/agents |

### 1.6 知识库模块

| 编号 | 功能名称 | 详细描述 | 输入 | 输出 | 优先级 | 所属模块 |
|------|----------|----------|------|------|--------|----------|
| FR-025 | 配置 Bedrock Knowledge Base | 创建/配置 Bedrock Knowledge Base，绑定 S3 数据源，设置 Titan Embeddings V2 | S3 bucket/prefix, 分块配置 | Knowledge Base ID | P1 | src/knowledge_base |
| FR-026 | 知识文档管理 | 编写并维护 7 篇运营知识 Markdown 文档 | 无 | 7 篇 Markdown 文档 | P1 | data/knowledge_docs |

### 1.7 API 模块

| 编号 | 功能名称 | 详细描述 | 输入 | 输出 | 优先级 | 所属模块 |
|------|----------|----------|------|------|--------|----------|
| FR-027 | ASIN 健康查询 API | 查询单个 ASIN 综合健康分析 | asin_id | 完整分析报告 JSON | P0 | src/api |
| FR-028 | 批量健康概览 API | 批量查询 ASIN 列表的评分摘要 | asin_ids 或筛选条件 | 评分摘要列表 | P0 | src/api |
| FR-029 | 自然语言问答 API | 接收用户自然语言问题，返回 Supervisor Agent 的分析结果 | 用户问题文本 | Agent 分析结果 | P0 | src/api |
| FR-030 | 评分重算 API | 触发指定 ASIN 或全量评分重算 | asin_id(可选) | 重算结果 | P2 | src/api |

---

## 2. 数据需求

### 2.1 ASIN 基础信息

| 字段名 | 类型 | 取值范围 | 说明 | 数据来源 |
|--------|------|----------|------|----------|
| asin_id | str | 10 位字母数字 | Amazon 标准识别号 | 模拟生成 |
| title | str | 50-200 字符 | 商品标题 | 模拟生成 |
| category | str | 枚举（见 2.8） | 所属类目 | 模拟生成 |
| listing_age | int | 1-1800 天 | 上架天数 | 模拟生成 |
| lifecycle_stage | str | new/growth/mature/decline | 生命周期阶段 | 由 listing_age + 销量趋势计算 |
| price | float | 5.99-299.99 USD | 售价 | 模拟生成 |

### 2.2 销量维度指标

| 字段名 | 类型 | 取值范围 | 说明 | 更新频率 |
|--------|------|----------|------|----------|
| daily_orders | list[int] | 每天 0-500 单 | 日订单数（7 天 + 30 天序列） | 每日 |
| daily_sales_amount | list[float] | 每天 0-50000 USD | 日销售额（7 天 + 30 天序列） | 每日 |
| sessions | list[int] | 每天 10-50000 | 日会话数（7 天 + 30 天序列） | 每日 |
| cvr | float | 0.01-0.50 (1%-50%) | 转化率（近 7 天均值） | 每日 |
| bsr | int | 1-1000000 | Best Seller Rank | 每日 |
| bsr_category | str | 类目名称 | BSR 所属类目 | 静态 |

### 2.3 库存维度指标

| 字段名 | 类型 | 取值范围 | 说明 | 更新频率 |
|--------|------|----------|------|----------|
| fba_available | int | 0-10000 | FBA 可售库存数量 | 每日 |
| fba_inbound | int | 0-5000 | FBA 在途库存数量 | 每日 |
| days_of_supply | float | 0-365 天 | 可售天数（fba_available / 日均销量） | 每日 |
| ipi_score | int | 0-1000 | 库存绩效指标 | 每周 |
| excess_inventory_pct | float | 0-1.0 (0%-100%) | 冗余库存占比 | 每周 |
| storage_cost_pct | float | 0-0.5 (0%-50%) | 仓储成本占销售额比例 | 每月 |

### 2.4 广告维度指标

| 字段名 | 类型 | 取值范围 | 说明 | 更新频率 |
|--------|------|----------|------|----------|
| ad_spend | float | 0-5000 USD/天 | 日广告花费 | 每日 |
| ad_sales | float | 0-50000 USD/天 | 日广告销售额 | 每日 |
| acos | float | 0-2.0 (0%-200%) | 广告销售成本率（ad_spend/ad_sales） | 每日 |
| roas | float | 0-50 | 广告回报率（ad_sales/ad_spend） | 每日 |
| cpc | float | 0.1-10.0 USD | 每次点击成本 | 每日 |
| ctr | float | 0.001-0.20 (0.1%-20%) | 点击率 | 每日 |
| ad_orders | int | 0-200/天 | 广告订单数 | 每日 |
| total_orders | int | 0-500/天 | 总订单数（用于计算广告依赖度） | 每日 |

### 2.5 售后维度指标

| 字段名 | 类型 | 取值范围 | 说明 | 更新频率 |
|--------|------|----------|------|----------|
| return_rate | float | 0-0.50 (0%-50%) | 退货率 | 每周 |
| avg_rating | float | 1.0-5.0 | 平均评分 | 每日 |
| review_count | int | 0-50000 | 累计评论数 | 每日 |
| recent_negative_pct | float | 0-1.0 (0%-100%) | 近 30 天差评占比（1-2 星） | 每周 |
| atoz_claims | int | 0-20 | 近 30 天 A-to-Z 索赔数 | 每周 |
| policy_warnings | int | 0-10 | 近 90 天政策警告数 | 每月 |

### 2.6 盈利维度指标

| 字段名 | 类型 | 取值范围 | 说明 | 更新频率 |
|--------|------|----------|------|----------|
| selling_price | float | 5.99-299.99 USD | 当前售价 | 每日 |
| fba_fee | float | 2.0-30.0 USD | FBA 配送费 | 每月 |
| referral_fee | float | 0.5-45.0 USD | 佣金（通常售价 * 15%） | 每日 |
| ad_cost_per_unit | float | 0-20.0 USD | 单件广告成本（ad_spend/total_orders） | 每日 |
| cogs | float | 1.0-100.0 USD | 单件货物成本 | 静态 |
| shipping_cost | float | 0.5-15.0 USD | 头程物流单件成本 | 静态 |
| gross_margin | float | -0.5 到 0.8 (-50%到80%) | 毛利率 | 每日 |

### 2.7 Listing 质量维度指标

| 字段名 | 类型 | 取值范围 | 说明 | 更新频率 |
|--------|------|----------|------|----------|
| title_score | int | 0-100 | 标题质量评分（关键词覆盖、长度、可读性） | 每周 |
| image_count | int | 0-9 | 图片数量 | 每周 |
| has_aplus | bool | true/false | 是否有 A+ 页面 | 每周 |
| bullet_count | int | 0-5 | 五点描述数量 | 每周 |
| search_terms_filled | bool | true/false | 后台搜索词是否填写完整 | 每周 |
| buybox_pct | float | 0-1.0 (0%-100%) | 黄金购物车占有率 | 每日 |

### 2.8 类目枚举

模拟数据覆盖以下 5 个类目：

| 类目代码 | 类目名称 | ASIN 数量 |
|----------|----------|-----------|
| electronics | 电子产品 | 25 |
| home_kitchen | 家居厨房 | 25 |
| sports_outdoors | 运动户外 | 20 |
| beauty | 美妆个护 | 15 |
| toys_games | 玩具游戏 | 15 |

---

## 3. 评分规则规格

### 3.1 生命周期阶段判定

```
if listing_age < 90:
    stage = "new"
elif listing_age <= 365 and sales_trend_30d > 0:
    stage = "growth"
elif listing_age > 365 and abs(sales_trend_60d) <= threshold:
    stage = "mature"
elif sales_trend_60d < -threshold and consecutive_decline_days >= 60:
    stage = "decline"
```

其中：
- `sales_trend_30d` = (近 7 天日均销量 - 前 23 天日均销量) / 前 23 天日均销量
- `sales_trend_60d` = (近 30 天日均销量 - 前 30 天日均销量) / 前 30 天日均销量
- `threshold` = 0.10（10% 波动视为稳定）
- `consecutive_decline_days`：连续日销量低于 60 天前同期的天数

### 3.2 单维度评分公式

所有维度评分范围：0-100，保留 1 位小数。

#### 3.2.1 销量维度评分 (S_sales)

```
# 各子指标评分（0-100）
score_orders = clip(daily_orders_7d_avg / category_p50_orders * 60, 0, 100)
score_cvr = clip(cvr / category_p50_cvr * 70, 0, 100)
score_bsr = clip((1 - bsr / category_max_bsr) * 100, 0, 100)
score_trend = clip(50 + sales_trend_30d * 200, 0, 100)

# 加权
S_sales = score_orders * 0.35 + score_cvr * 0.25 + score_bsr * 0.25 + score_trend * 0.15
```

#### 3.2.2 库存维度评分 (S_inventory)

```
# 可售天数评分：30-90 天为满分区间
if 30 <= days_of_supply <= 90:
    score_dos = 100
elif days_of_supply < 30:
    score_dos = clip(days_of_supply / 30 * 100, 0, 100)
else:  # > 90
    score_dos = clip(100 - (days_of_supply - 90) / 90 * 60, 40, 100)

score_ipi = clip(ipi_score / 800 * 100, 0, 100)
score_excess = clip((1 - excess_inventory_pct / 0.30) * 100, 0, 100)
score_storage = clip((1 - storage_cost_pct / 0.15) * 100, 0, 100)

S_inventory = score_dos * 0.35 + score_ipi * 0.25 + score_excess * 0.20 + score_storage * 0.20
```

#### 3.2.3 广告维度评分 (S_advertising)

```
# ACOS 评分：越低越好，基准为类目 P50
score_acos = clip((1 - acos / (category_p50_acos * 2)) * 100, 0, 100)
score_roas = clip(roas / category_p50_roas * 50, 0, 100)
score_ctr = clip(ctr / category_p50_ctr * 70, 0, 100)

# 广告依赖度：ad_orders/total_orders，过高（>0.7）扣分
ad_dependency = ad_orders / max(total_orders, 1)
score_dependency = clip((1 - max(ad_dependency - 0.3, 0) / 0.5) * 100, 0, 100)

S_advertising = score_acos * 0.30 + score_roas * 0.25 + score_ctr * 0.20 + score_dependency * 0.25
```

#### 3.2.4 售后维度评分 (S_aftersales)

```
score_return = clip((1 - return_rate / 0.15) * 100, 0, 100)
score_rating = clip((avg_rating - 1) / 4 * 100, 0, 100)
score_negative = clip((1 - recent_negative_pct / 0.20) * 100, 0, 100)

# A-to-Z 和政策警告：0 为满分，每个扣 15 分
score_claims = clip(100 - atoz_claims * 15, 0, 100)
score_policy = clip(100 - policy_warnings * 20, 0, 100)

S_aftersales = score_return * 0.25 + score_rating * 0.30 + score_negative * 0.20 + score_claims * 0.15 + score_policy * 0.10
```

#### 3.2.5 盈利维度评分 (S_profitability)

```
# 毛利率评分
score_margin = clip(gross_margin / 0.40 * 100, 0, 100)

# 广告成本效率
ad_cost_ratio = ad_cost_per_unit / selling_price
score_ad_efficiency = clip((1 - ad_cost_ratio / 0.25) * 100, 0, 100)

# FBA 费用合理性
fba_ratio = fba_fee / selling_price
score_fba = clip((1 - fba_ratio / 0.30) * 100, 0, 100)

# 单件利润
unit_profit = selling_price - fba_fee - referral_fee - ad_cost_per_unit - cogs - shipping_cost
score_unit_profit = clip(unit_profit / (selling_price * 0.20) * 100, 0, 100)

S_profitability = score_margin * 0.35 + score_ad_efficiency * 0.25 + score_fba * 0.15 + score_unit_profit * 0.25
```

#### 3.2.6 Listing 质量维度评分 (S_listing)

```
score_title = title_score  # 已经是 0-100
score_images = clip(image_count / 7 * 100, 0, 100)
score_aplus = 100 if has_aplus else 30
score_bullets = clip(bullet_count / 5 * 100, 0, 100)
score_search = 100 if search_terms_filled else 20
score_buybox = buybox_pct * 100

S_listing = score_title * 0.25 + score_images * 0.15 + score_aplus * 0.15 + score_bullets * 0.10 + score_search * 0.10 + score_buybox * 0.25
```

### 3.3 动态权重规则

| 生命周期阶段 | 判定条件 | W_sales | W_inventory | W_advertising | W_aftersales | W_profitability | W_listing |
|---|---|---|---|---|---|---|---|
| 新品期 (new) | listing_age < 90 | 0.15 | 0.15 | 0.20 | 0.10 | 0.10 | 0.30 |
| 成长期 (growth) | 90 <= listing_age <= 365 且 sales_trend_30d > 0.10 | 0.25 | 0.20 | 0.20 | 0.10 | 0.15 | 0.10 |
| 成熟期 (mature) | listing_age > 365 且 abs(sales_trend_60d) <= 0.10 | 0.25 | 0.20 | 0.15 | 0.15 | 0.15 | 0.10 |
| 衰退期 (decline) | consecutive_decline_days >= 60 | 0.20 | 0.25 | 0.10 | 0.15 | 0.20 | 0.10 |

权重总和恒等于 1.0。

### 3.4 综合评分计算

```
# 第一步：加权求和
raw_score = (S_sales * W_sales + S_inventory * W_inventory + S_advertising * W_advertising
             + S_aftersales * W_aftersales + S_profitability * W_profitability + S_listing * W_listing)

# 第二步：趋势修正（±5 分）
trend_bonus = clip(sales_trend_30d * 25, -5, 5)
adjusted_score = clip(raw_score + trend_bonus, 0, 100)

# 第三步：短板一票否决
dimensions = [S_sales, S_inventory, S_advertising, S_aftersales, S_profitability, S_listing]
min_dim = min(dimensions)
dims_below_60 = sum(1 for d in dimensions if d < 60)

if min_dim < 20:
    final_score = min(adjusted_score, 30)
elif min_dim < 40:
    final_score = min(adjusted_score, 50)
elif dims_below_60 >= 2:
    final_score = min(adjusted_score, 55)
else:
    final_score = adjusted_score

# 保留 1 位小数
final_score = round(final_score, 1)
```

### 3.5 健康标签映射

| 标签 | 分数范围 | 含义 |
|------|----------|------|
| healthy | 80.0 - 100.0 | 健康 — 各维度表现良好 |
| warning | 60.0 - 79.9 | 预警 — 存在需关注的问题 |
| abnormal | 40.0 - 59.9 | 异常 — 存在明显短板 |
| critical | 0.0 - 39.9 | 危险 — 需要立即干预 |

---

## 4. Agent 需求

### 4.1 Supervisor Agent

| 属性 | 值 |
|------|-----|
| FM 模型 | Claude Sonnet 4.6 (`us.anthropic.claude-sonnet-4-6-v1`) |
| 角色 | 接收用户请求，分解任务，协调 sub-agent，汇总输出 |
| 注册工具 | 5 个 sub-agent（作为 @tool 注册） |
| 输入 | 用户自然语言请求（str） |
| 输出 | 完整分析报告（结构化 JSON + 自然语言摘要） |

**输出 Schema：**
```json
{
  "asin_id": "str",
  "overall_score": "float",
  "health_label": "str",
  "lifecycle_stage": "str",
  "dimension_scores": {
    "sales": "float",
    "inventory": "float",
    "advertising": "float",
    "aftersales": "float",
    "profitability": "float",
    "listing": "float"
  },
  "root_cause_analysis": {
    "primary_cause": "str",
    "contributing_factors": ["str"],
    "confidence": "float (0-1)",
    "affected_dimensions": ["str"]
  },
  "action_plan": [
    {
      "priority": "int (1-5)",
      "action": "str",
      "expected_impact": "str",
      "steps": ["str"],
      "timeline": "str"
    }
  ],
  "competitor_comparison": {
    "vs_category_avg": "str",
    "strengths": ["str"],
    "weaknesses": ["str"]
  },
  "knowledge_references": [
    {
      "title": "str",
      "snippet": "str",
      "source": "str"
    }
  ],
  "summary": "str"
}
```

### 4.2 评分查询 Agent

| 属性 | 值 |
|------|-----|
| FM 模型 | Nova Pro (`us.amazon.nova-pro-v1:0`) |
| 角色 | 理解评分查询意图，返回结构化评分数据 |
| 工具列表 | `query_asin_score`, `query_batch_scores`, `query_asin_metrics` |
| 输入 | 查询意图描述（str） |
| 输出 | 评分数据 + 简要数据说明（JSON） |

### 4.3 根因分析 Agent

| 属性 | 值 |
|------|-----|
| FM 模型 | Claude Sonnet 4.6 (`us.anthropic.claude-sonnet-4-6-v1`) |
| 角色 | 分析多维度关联异常，推理根本原因 |
| 工具列表 | `query_asin_metrics`, `query_category_benchmark`, `search_knowledge` |
| 输入 | ASIN 评分结果 + 原始指标 + 类目基准（JSON） |
| 输出 | 根因分析报告（JSON） |

**输出 Schema：**
```json
{
  "primary_cause": "str - 根本原因描述",
  "cause_chain": ["str - 因果链条，从根因到表象"],
  "contributing_factors": ["str - 次要因素"],
  "affected_dimensions": ["str - 受影响维度"],
  "confidence": "float - 置信度 0.0-1.0",
  "evidence": ["str - 支撑证据"],
  "risk_level": "str - high/medium/low"
}
```

### 4.4 行动建议 Agent

| 属性 | 值 |
|------|-----|
| FM 模型 | Claude Sonnet 4.6 (`us.anthropic.claude-sonnet-4-6-v1`) |
| 角色 | 根据根因分析输出可执行的行动计划 |
| 工具列表 | `search_knowledge` |
| 输入 | 根因分析结果 + ASIN 基础信息（JSON） |
| 输出 | 行动计划列表（JSON） |

**输出 Schema：**
```json
{
  "actions": [
    {
      "priority": "int 1-5（1 最高）",
      "title": "str - 行动标题",
      "description": "str - 详细描述",
      "steps": ["str - 具体实施步骤"],
      "expected_impact": "str - 预期改善效果",
      "timeline": "str - 建议时间线（如 1-3 天、1-2 周）",
      "affected_dimensions": ["str - 预期改善的维度"],
      "difficulty": "str - easy/medium/hard"
    }
  ]
}
```

### 4.5 竞品分析 Agent

| 属性 | 值 |
|------|-----|
| FM 模型 | Nova Pro (`us.amazon.nova-pro-v1:0`) |
| 角色 | 对比 ASIN 与竞品/类目基准 |
| 工具列表 | `query_asin_metrics`, `query_category_benchmark`, `query_competitors` |
| 输入 | ASIN ID（str） |
| 输出 | 竞品分析报告（JSON） |

### 4.6 知识检索 Agent

| 属性 | 值 |
|------|-----|
| FM 模型 | Nova Pro (`us.amazon.nova-pro-v1:0`) |
| 角色 | 根据上下文检索运营知识库 |
| 工具列表 | `search_knowledge` |
| 输入 | 查询文本（str） |
| 输出 | 知识片段列表（JSON） |

### 4.7 Agent 调用关系

```
用户请求
  └─→ Supervisor Agent (Sonnet 4.6)
        ├─→ 评分查询 Agent (Nova Pro)
        │     ├── query_asin_score
        │     ├── query_batch_scores
        │     └── query_asin_metrics
        ├─→ 根因分析 Agent (Sonnet 4.6)
        │     ├── query_asin_metrics
        │     ├── query_category_benchmark
        │     └── search_knowledge
        ├─→ 行动建议 Agent (Sonnet 4.6)
        │     └── search_knowledge
        ├─→ 竞品分析 Agent (Nova Pro)
        │     ├── query_asin_metrics
        │     ├── query_category_benchmark
        │     └── query_competitors
        └─→ 知识检索 Agent (Nova Pro)
              └── search_knowledge
```

典型调用流程（以"分析 ASIN B001 的健康状况"为例）：
1. Supervisor 调用**评分查询 Agent** → 获取 B001 的评分和原始指标
2. Supervisor 调用**根因分析 Agent** → 传入评分+指标，获取根因报告
3. Supervisor 调用**行动建议 Agent** → 传入根因结果，获取行动计划
4. Supervisor 调用**竞品分析 Agent** → 获取竞品对比（可与步骤 2 并行）
5. Supervisor 调用**知识检索 Agent** → 补充相关运营知识（可与步骤 2 并行）
6. Supervisor 汇总全部结果，生成最终报告

---

## 5. 模拟数据需求

### 5.1 ASIN 分布要求

| 生命周期阶段 | 数量 | 占比 |
|---|---|---|
| 新品期 (new) | 25 | 25% |
| 成长期 (growth) | 30 | 30% |
| 成熟期 (mature) | 30 | 30% |
| 衰退期 (decline) | 15 | 15% |
| **合计** | **100** | **100%** |

| 健康标签 | 数量 | 占比 |
|---|---|---|
| healthy | ~30 | ~30% |
| warning | ~30 | ~30% |
| abnormal | ~25 | ~25% |
| critical | ~15 | ~15% |
| **合计** | **100** | **100%** |

### 5.2 关联异常场景设计（10 个）

| 编号 | 场景名称 | 异常字段 | 异常方向 | 预期根因 | 影响维度 |
|---|---|---|---|---|---|
| ANO-01 | 差评引发销量下滑 | avg_rating↓, recent_negative_pct↑, daily_orders↓, cvr↓ | rating 跌到 3.2, negative_pct 达 40%, 订单降 50% | 产品质量问题导致差评爆发，CVR 下降拖累销量 | 售后、销量 |
| ANO-02 | 广告成本失控 | acos↑, cpc↑, ad_spend↑, gross_margin↓ | ACOS 达 80%, CPC 翻倍, 毛利率转负 | 竞争加剧推高 CPC，广告 ROI 崩坏侵蚀利润 | 广告、盈利 |
| ANO-03 | 断货后遗症 | fba_available=0→恢复, bsr↓, daily_orders↓, sessions↓ | 断货 7 天后补货，BSR 从 500 跌到 5000 | FBA 断货导致排名暴跌，流量和销量难以恢复 | 库存、销量 |
| ANO-04 | Listing 被篡改 | title_score↓, buybox_pct↓, sessions↓, cvr↓ | title_score 从 85 跌到 30, buybox 降到 60% | Listing 被跟卖/篡改，搜索排名和转化率受损 | Listing、销量 |
| ANO-05 | 退货率飙升 | return_rate↑, avg_rating↓, gross_margin↓ | 退货率从 3% 涨到 25%, 毛利率降 15pp | 产品批次质量缺陷，退货增加同时影响评价和利润 | 售后、盈利 |
| ANO-06 | 季节性需求消退 | daily_orders↓, sessions↓, excess_inventory_pct↑, storage_cost_pct↑ | 订单降 70%, 冗余库存达 40% | 季节性品类旺季结束，库存积压产生高额仓储费 | 销量、库存、盈利 |
| ANO-07 | 价格战挤压 | selling_price↓, gross_margin↓, cvr↓, bsr↓ | 售价被迫降 30%, 毛利率跌至 5% | 竞品发起价格战，被迫降价但仍然流失市场份额 | 盈利、销量 |
| ANO-08 | 广告依赖症 | ad_orders/total_orders>0.8, organic_rank↓, acos↑ | 广告订单占比 85%, 自然排名持续下降 | 过度依赖广告获客，自然流量萎缩，一旦停广告销量断崖 | 广告、销量 |
| ANO-09 | 多维度全面恶化 | 5 个维度同时 < 50 | 销量、库存、广告、售后、盈利均异常 | 产品进入生命周期末期，多个问题叠加形成恶性循环 | 全部维度 |
| ANO-10 | A-to-Z 索赔危机 | atoz_claims=5, policy_warnings=3, return_rate↑, daily_orders↓ | 索赔密集爆发，账号面临风险 | 物流/产品问题引发集中客诉，影响账号健康 | 售后、销量 |

### 5.3 类目基准数据规格

每个类目需要以下基准指标（分位值）：

| 指标 | P25 | P50 | P75 | P90 | 单位 |
|------|-----|-----|-----|-----|------|
| daily_orders | 3 | 10 | 30 | 80 | 单/天 |
| cvr | 0.05 | 0.10 | 0.18 | 0.25 | 比率 |
| acos | 0.40 | 0.25 | 0.15 | 0.08 | 比率（越低越好） |
| roas | 2.5 | 4.0 | 6.5 | 12.0 | 倍数 |
| cpc | 0.5 | 0.8 | 1.5 | 3.0 | USD |
| ctr | 0.002 | 0.004 | 0.008 | 0.015 | 比率 |
| return_rate | 0.08 | 0.05 | 0.03 | 0.01 | 比率（越低越好） |
| avg_rating | 3.5 | 4.0 | 4.4 | 4.7 | 星 |
| gross_margin | 0.10 | 0.20 | 0.30 | 0.45 | 比率 |

注：不同类目的基准值应有合理差异（如电子产品退货率高于美妆）。

### 5.4 竞品数据规格

为约 30 个 ASIN（成长期+成熟期优先）生成竞品数据，每个 ASIN 配 3-5 个竞品：

| 字段 | 类型 | 说明 |
|------|------|------|
| competitor_asin | str | 竞品 ASIN |
| competitor_price | float | 竞品售价 |
| competitor_rating | float | 竞品评分 |
| competitor_review_count | int | 竞品评论数 |
| competitor_bsr | int | 竞品 BSR |
| competitor_monthly_sales_est | int | 竞品月销量估算 |

---

## 6. API 接口需求

### 6.1 接口列表

#### 6.1.1 GET /api/v1/asin/{asin_id}/health

**描述**：查询单个 ASIN 的完整健康分析报告

**请求参数**：
| 参数 | 位置 | 类型 | 必填 | 说明 |
|------|------|------|------|------|
| asin_id | path | str | 是 | ASIN 编号 |

**响应 Schema (200)**：
```json
{
  "asin_id": "string",
  "overall_score": 72.5,
  "health_label": "warning",
  "lifecycle_stage": "growth",
  "dimension_scores": {
    "sales": 78.3,
    "inventory": 85.0,
    "advertising": 60.2,
    "aftersales": 72.1,
    "profitability": 55.8,
    "listing": 90.0
  },
  "weights": {
    "sales": 0.25,
    "inventory": 0.20,
    "advertising": 0.20,
    "aftersales": 0.10,
    "profitability": 0.15,
    "listing": 0.10
  },
  "veto_applied": false,
  "trend_bonus": 1.2,
  "updated_at": "2026-03-25T10:00:00Z"
}
```

#### 6.1.2 POST /api/v1/asin/batch-health

**描述**：批量查询 ASIN 评分摘要

**请求 Body**：
```json
{
  "asin_ids": ["string"],
  "filter": {
    "health_label": "warning",
    "lifecycle_stage": "growth",
    "min_score": 0,
    "max_score": 100
  },
  "sort_by": "overall_score",
  "sort_order": "asc",
  "page": 1,
  "page_size": 20
}
```

**响应 Schema (200)**：
```json
{
  "total": 100,
  "page": 1,
  "page_size": 20,
  "items": [
    {
      "asin_id": "string",
      "overall_score": 72.5,
      "health_label": "warning",
      "lifecycle_stage": "growth",
      "dimension_scores": { ... }
    }
  ]
}
```

#### 6.1.3 POST /api/v1/asin/{asin_id}/analyze

**描述**：触发 AI Agent 对单个 ASIN 进行深度分析（根因+建议+竞品）

**请求参数**：
| 参数 | 位置 | 类型 | 必填 | 说明 |
|------|------|------|------|------|
| asin_id | path | str | 是 | ASIN 编号 |

**请求 Body**：
```json
{
  "analysis_type": ["root_cause", "action_plan", "competitor", "knowledge"],
  "language": "zh"
}
```

**响应 Schema (200)**：
```json
{
  "asin_id": "string",
  "score_summary": { ... },
  "root_cause_analysis": {
    "primary_cause": "string",
    "cause_chain": ["string"],
    "contributing_factors": ["string"],
    "affected_dimensions": ["string"],
    "confidence": 0.85,
    "evidence": ["string"],
    "risk_level": "high"
  },
  "action_plan": [
    {
      "priority": 1,
      "title": "string",
      "description": "string",
      "steps": ["string"],
      "expected_impact": "string",
      "timeline": "string",
      "difficulty": "medium"
    }
  ],
  "competitor_comparison": { ... },
  "knowledge_references": [ ... ],
  "summary": "string",
  "processing_time_ms": 3500
}
```

#### 6.1.4 POST /api/v1/chat

**描述**：自然语言问答接口，由 Supervisor Agent 处理

**请求 Body**：
```json
{
  "message": "string",
  "session_id": "string (可选，用于多轮对话)",
  "context": {
    "asin_id": "string (可选，指定上下文 ASIN)"
  }
}
```

**响应 Schema (200)**：
```json
{
  "response": "string",
  "structured_data": { ... },
  "session_id": "string",
  "processing_time_ms": 2000
}
```

#### 6.1.5 POST /api/v1/scores/recalculate

**描述**：触发评分重算

**请求 Body**：
```json
{
  "asin_ids": ["string (可选，为空则全量重算)"]
}
```

**响应 Schema (200)**：
```json
{
  "recalculated_count": 100,
  "status": "completed",
  "duration_ms": 5000
}
```

#### 6.1.6 GET /api/v1/health

**描述**：服务健康检查

**响应 Schema (200)**：
```json
{
  "status": "ok",
  "version": "string",
  "timestamp": "string"
}
```

### 6.2 错误码定义

| HTTP 状态码 | 错误码 | 说明 |
|---|---|---|
| 400 | INVALID_ASIN | ASIN 格式无效（非 10 位字母数字） |
| 400 | INVALID_FILTER | 筛选条件参数错误 |
| 400 | INVALID_ANALYSIS_TYPE | 不支持的分析类型 |
| 404 | ASIN_NOT_FOUND | 指定 ASIN 不存在 |
| 422 | BATCH_TOO_LARGE | 批量查询超过上限（最大 50） |
| 429 | RATE_LIMIT_EXCEEDED | 请求频率超限 |
| 500 | SCORING_ENGINE_ERROR | 评分引擎内部错误 |
| 500 | AGENT_ERROR | Agent 调用失败 |
| 502 | BEDROCK_UNAVAILABLE | Bedrock FM 服务不可用 |
| 504 | AGENT_TIMEOUT | Agent 处理超时 |

**错误响应格式**：
```json
{
  "error": {
    "code": "ASIN_NOT_FOUND",
    "message": "ASIN B0000XXXXX not found in database",
    "request_id": "uuid"
  }
}
```

---

## 7. 非功能需求

### 7.1 性能要求

| 指标 | 要求 |
|------|------|
| 单 ASIN 评分查询延迟 | < 200ms (P99) |
| 批量评分查询延迟（50 ASIN） | < 500ms (P99) |
| AI Agent 深度分析延迟 | < 30s (P95)，< 60s (P99) |
| 自然语言问答延迟 | < 15s (P95) |
| 全量评分重算（100 ASIN） | < 30s |
| 并发支持 | 10 个同时 Agent 分析请求 |

### 7.2 成本约束

| 资源 | 预算上限 | 说明 |
|------|----------|------|
| Bedrock FM 调用 | 100 USD/月 | 开发测试阶段 |
| DynamoDB | 按需模式 | 免费额度内 |
| S3 存储 | < 1 GB | 模拟数据 + 知识文档 |
| Bedrock Knowledge Base | 标准配置 | 含向量索引费用 |

### 7.3 安全要求

| 类别 | 要求 |
|------|------|
| AWS 认证 | 使用 IAM Role，不硬编码 Access Key |
| API 认证 | API Key 或 AWS IAM Signature V4 |
| 数据加密 | S3 启用 SSE-S3，DynamoDB 启用静态加密 |
| 网络 | VPC 内部署，Bedrock 通过 VPC Endpoint 访问 |
| 日志 | 不记录完整请求体中的敏感字段 |
| 输入校验 | 所有 API 输入经 Pydantic 模型验证 |

### 7.4 可维护性要求

| 类别 | 要求 |
|------|------|
| 代码规范 | Python 3.12，完整类型注解，中文注释 |
| 数据模型 | Pydantic v2 定义所有输入/输出 Schema |
| 错误处理 | 所有外部调用（Bedrock、DynamoDB、S3）有重试和超时 |
| 测试 | 评分引擎 100% 单元测试覆盖 |
| 可观测性 | 结构化日志（JSON 格式），含 request_id 链路追踪 |
