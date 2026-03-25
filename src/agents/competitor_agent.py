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
- **最多调用 3 次工具**，然后直接给结论
- **严格按下面的 JSON 格式输出**，不要加任何前言或额外说明

## 输出格式（必须严格遵守，直接输出 JSON 对象）
```json
{
  "category_position": "领先/中等/落后",
  "weak_vs_benchmark": ["维度1: 当前值 vs 基准值", "维度2: 当前值 vs 基准值"],
  "competitor_insights": "2-3句话的竞争策略建议"
}
```

不要输出任何 JSON 以外的内容。"""


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
