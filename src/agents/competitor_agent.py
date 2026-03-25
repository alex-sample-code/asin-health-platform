"""竞品分析 Agent — 类目基准对比和竞品分析。

使用 Claude Sonnet 4.6 模型，工具：get_category_benchmark, get_competitor_list, get_asin_score, get_asin_metrics
"""

from __future__ import annotations

from strands import Agent
from strands.models import BedrockModel

from src.tools.score_tools import get_asin_score
from src.tools.metrics_tools import get_asin_metrics
from src.tools.benchmark_tools import get_category_benchmark, get_competitor_list

SYSTEM_PROMPT = """你是 ASIN 竞品分析专家。

## 规则
- **最多调用 2 次工具**，然后直接给结论
- **回复控制在 400 字以内**
- 重点对比弱于基准的维度，不要罗列所有正常的指标

## 输出格式（严格遵守）
1. **竞争力定位**：领先/中等/落后（一句话说明）
2. **弱于基准的维度**（最多 3 个）：维度名 + 当前值 vs 基准值
3. **竞争策略建议**：2-3 句话"""


def create_competitor_agent() -> Agent:
    """创建竞品分析 Agent（Amazon Nova Pro — 查数据对比，不需要深度推理）。"""
    model = BedrockModel(
        model_id="us.amazon.nova-pro-v1:0",
        max_tokens=2048,
        region_name="us-east-1",
    )
    return Agent(
        model=model,
        tools=[get_asin_score, get_asin_metrics, get_category_benchmark, get_competitor_list],
        system_prompt=SYSTEM_PROMPT,
        name="competitor_agent",
        description="竞品分析Agent，负责类目基准对比和竞品分析",
    )
