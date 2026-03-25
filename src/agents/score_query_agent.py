"""评分查询 Agent — 负责查询和解读 ASIN 健康度评分。

使用 Nova Pro 模型，工具：get_asin_score, get_score_summary, list_asins_by_health
"""

from __future__ import annotations

from strands import Agent
from strands.models import BedrockModel

from src.tools.score_tools import get_asin_score, get_score_summary, list_asins_by_health

SYSTEM_PROMPT = """你是 ASIN 健康度评分查询专家。你的职责是：

1. 查询单个或多个 ASIN 的健康度评分
2. 解读六维度评分（销量、库存、广告、售后、盈利、Listing质量）
3. 说明健康标签含义和短板否决机制
4. 提供评分摘要统计和筛选

健康标签说明：
- healthy (80-100): 健康，各维度表现良好
- warning (60-79): 预警，需关注薄弱维度
- abnormal (40-59): 异常，需及时处理
- danger (0-39): 危险，需紧急干预

短板否决规则：
- 任一维度 < 20 → 综合分最多 30（强制危险）
- 任一维度 < 40 → 综合分最多 50（最多预警）
- 两个及以上维度 < 60 → 综合分最多 55（最多预警）

请用简洁的中文回答，结合数据给出清晰的评分解读。"""


def create_score_query_agent() -> Agent:
    """创建评分查询 Agent（Nova Pro）。"""
    model = BedrockModel(
        model_config={
            "model_id": "us.amazon.nova-pro-v1:0",
            "max_tokens": 2048,
        },
        region_name="us-east-1",
    )
    return Agent(
        model=model,
        tools=[get_asin_score, get_score_summary, list_asins_by_health],
        system_prompt=SYSTEM_PROMPT,
        name="score_query_agent",
        description="评分查询Agent，负责查询和解读ASIN健康度评分",
    )
