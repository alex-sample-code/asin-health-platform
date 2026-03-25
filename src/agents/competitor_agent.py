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
  "position_reason": "一句话说明为什么是这个定位",
  "weak_vs_benchmark": [
    "维度名: 当前值 XX vs 类目中位数 YY（差距说明）"
  ],
  "strong_vs_benchmark": [
    "维度名: 当前值 XX vs 类目中位数 YY（优势说明）"
  ],
  "competitor_insights": "3-5句话的深度竞争策略建议，包含具体可执行的方向"
}
```

weak_vs_benchmark 和 strong_vs_benchmark 各列出 2-4 个维度。
competitor_insights 要有深度，结合具体数据给出差异化策略。
不要输出任何 JSON 以外的内容。"""


def create_competitor_agent() -> Agent:
    """创建竞品分析 Agent（Sonnet 4.6 — 需要深度分析能力）。"""
    model = BedrockModel(
        model_id="us.anthropic.claude-sonnet-4-6",
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
