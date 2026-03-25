"""根因分析 Agent — 多因素关联推理，找出评分异常的根本原因。

使用 Claude Sonnet 4.6 模型，工具：get_asin_metrics, get_metrics_trend, get_asin_score, search_knowledge
"""

from __future__ import annotations

from strands import Agent
from strands.models import BedrockModel

from src.tools.score_tools import get_asin_score
from src.tools.metrics_tools import get_asin_metrics, get_metrics_trend
from src.tools.knowledge_tools import search_knowledge

SYSTEM_PROMPT = """你是 ASIN 健康度根因分析专家。

## 规则
- **最多调用 3 次工具**，然后直接给结论
- **严格按下面的 JSON 格式输出**，不要加任何前言或额外说明

## 输出格式（必须严格遵守，直接输出 JSON 数组）
```json
[
  {
    "hypothesis": "根因假设（一句话描述）",
    "confidence": "high",
    "evidence": ["证据1", "证据2"]
  }
]
```

confidence 只能是 "high"/"medium"/"low"。最多 3 个根因。
不要输出任何 JSON 以外的内容。"""


def create_root_cause_agent() -> Agent:
    """创建根因分析 Agent（Claude Sonnet 4.6）。"""
    model = BedrockModel(
        model_id="us.anthropic.claude-sonnet-4-6",
        max_tokens=2048,
        region_name="us-east-1",
    )
    return Agent(
        model=model,
        tools=[get_asin_score, get_asin_metrics, get_metrics_trend, search_knowledge],
        system_prompt=SYSTEM_PROMPT,
        name="root_cause_agent",
        description="根因分析Agent，负责分析ASIN评分异常的根本原因",
    )
