"""行动建议 Agent — 根据评分和根因输出可执行的行动计划。

使用 Claude Sonnet 4.6 模型，工具：get_asin_score, get_asin_metrics, search_knowledge, get_category_benchmark
"""

from __future__ import annotations

from strands import Agent
from strands.models import BedrockModel

from src.tools.score_tools import get_asin_score
from src.tools.metrics_tools import get_asin_metrics
from src.tools.benchmark_tools import get_category_benchmark
from src.tools.knowledge_tools import search_knowledge

SYSTEM_PROMPT = """你是 ASIN 运营行动建议专家。

## 规则
- **最多调用 3 次工具**，然后直接给建议
- **回复控制在 500 字以内**
- 只给最重要的 3-4 条行动，不要面面俱到

## 输出格式（严格遵守）
按优先级列出行动建议，每条包含：
- **优先级 + 行动名称**（一行）
- **具体做什么**（2-3 步，每步一句话）
- **预期效果 + 时间线**（一行）

优先级定义：
- P0 紧急（24h内）：阻止恶化
- P1 高优（本周）：改善核心指标
- P2 中优（两周）：提升整体健康度
- P3 低优（本月）：长期优化"""


def create_action_advisor_agent() -> Agent:
    """创建行动建议 Agent（Claude Sonnet 4.6）。"""
    model = BedrockModel(
        model_id="us.anthropic.claude-sonnet-4-6",
        max_tokens=2048,
        region_name="us-east-1",
    )
    return Agent(
        model=model,
        tools=[get_asin_score, get_asin_metrics, get_category_benchmark, search_knowledge],
        system_prompt=SYSTEM_PROMPT,
        name="action_advisor_agent",
        description="行动建议Agent，负责输出可执行的运营行动计划",
    )
