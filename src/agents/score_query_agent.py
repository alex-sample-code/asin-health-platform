"""评分查询 Agent — 负责查询和解读 ASIN 健康度评分。

使用 Claude Sonnet 4.6 模型，工具：get_asin_score, get_score_summary, list_asins_by_health
"""

from __future__ import annotations

from strands import Agent
from strands.models import BedrockModel

from src.tools.score_tools import get_asin_score, get_score_summary, list_asins_by_health

SYSTEM_PROMPT = """你是 ASIN 健康度评分查询专家。

## 规则
- **最多调用 3 次工具**，然后直接回答
- **回复控制在 300 字以内**，简洁明了
- 不要重复罗列原始数据表格

## 输出格式
1. 综合评分 + 健康标签（一行）
2. 六维度评分一览（表格或一行列出）
3. 如有否决规则触发，说明原因（一句话）

健康标签：healthy(80+) / warning(60-79) / abnormal(40-59) / danger(0-39)
否决规则：任一维度<20→最多30分，任一<40→最多50分"""


def create_score_query_agent() -> Agent:
    """创建评分查询 Agent（Amazon Nova Pro — 简单查询不需要 Sonnet）。"""
    model = BedrockModel(
        model_id="us.amazon.nova-pro-v1:0",
        max_tokens=1024,
        region_name="us-east-1",
    )
    return Agent(
        model=model,
        tools=[get_asin_score, get_score_summary, list_asins_by_health],
        system_prompt=SYSTEM_PROMPT,
        name="score_query_agent",
        description="评分查询Agent，负责查询和解读ASIN健康度评分",
    )
