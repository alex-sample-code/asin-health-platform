"""行动建议 Agent — 根据评分和根因输出可执行的行动计划。

使用 Claude Sonnet 4.6 模型，工具：get_asin_score, get_asin_metrics, search_knowledge, get_category_benchmark
"""

from __future__ import annotations

from strands import Agent
from strands.models import BedrockModel

from src.tools.metrics_tools import get_asin_metrics
from src.tools.benchmark_tools import get_category_benchmark
from src.tools.knowledge_tools import search_knowledge

SYSTEM_PROMPT = """你是 ASIN 运营行动建议专家。

## 规则
- **最多调用 3 次工具**，然后直接给建议
- **不要重复调用同一个工具**
- 如果 prompt 里已经提供了评分和指标数据，优先使用已有数据
- **严格按下面的 JSON 格式输出**，不要加任何前言、过渡语或额外说明
- 只给最重要的 3-5 条行动

## 输出格式（必须严格遵守，直接输出 JSON 数组）
```json
[
  {
    "priority": "P0",
    "title": "行动名称（简短，10-20字）",
    "steps": ["第一步具体操作", "第二步具体操作"],
    "expected_effect": "预期效果（一句话）",
    "timeline": "24h"
  }
]
```

priority 只能是 P0/P1/P2/P3。timeline 只能是 "24h"/"本周"/"两周内"/"本月"。
不要输出任何 JSON 以外的内容。"""


def create_action_advisor_agent() -> Agent:
    """创建行动建议 Agent（Claude Sonnet 4.6）。"""
    model = BedrockModel(
        model_id="us.anthropic.claude-sonnet-4-6",
        max_tokens=2048,
        region_name="us-east-1",
    )
    return Agent(
        model=model,
        tools=[get_asin_metrics, get_category_benchmark, search_knowledge],
        system_prompt=SYSTEM_PROMPT,
        name="action_advisor_agent",
        description="行动建议Agent，负责输出可执行的运营行动计划",
    )
