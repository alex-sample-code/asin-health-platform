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
- **回复控制在 500 字以内**，只输出关键信息
- 不要重复罗列原始数据，直接给分析结论

## 输出格式（严格遵守）
1. **异常维度**：列出 <60 分的维度和分数（一行）
2. **根因假设**（最多 3 个）：每个一句话 + 置信度（高/中/低）
3. **验证方向**：一句话

常见关联模式：
- 销量↓ + 差评↑ + 退货率↑ → 产品质量问题
- 广告费↑ + CVR↓ + CPC↑ → 竞争加剧
- 库存充足 + 销量骤降 → Listing 被压制/Buy Box 丢失
- 销量↑ + 毛利↓ → FBA 费用上涨/价格战"""


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
