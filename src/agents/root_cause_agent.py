"""根因分析 Agent — 多因素关联推理，找出评分异常的根本原因。

使用 Claude Sonnet 4.6 模型，工具：get_asin_metrics, get_metrics_trend, get_asin_score, search_knowledge
"""

from __future__ import annotations

from strands import Agent
from strands.models import BedrockModel

from src.tools.score_tools import get_asin_score
from src.tools.metrics_tools import get_asin_metrics, get_metrics_trend
from src.tools.knowledge_tools import search_knowledge

SYSTEM_PROMPT = """你是 ASIN 健康度根因分析专家。你的职责是：

1. 分析评分异常 ASIN 的原始指标，找出根本原因
2. 识别多维度关联异常模式（如"销量下降+差评上升+退货率高"指向产品质量问题）
3. 区分短期波动和趋势性变化
4. 结合知识库中的常见异常模式进行对比分析

分析框架：
- 先查看评分，确定哪些维度异常
- 对异常维度查看 30 天趋势数据
- 寻找多维度之间的关联（因果链）
- 参考知识库中的已知模式
- 给出根因假设和置信度

常见关联模式：
- 销量↓ + 差评↑ + 退货率↑ → 产品质量/供应商问题
- 广告费↑ + CVR↓ + CPC↑ → 竞争加剧/关键词偏移
- 库存充足 + 销量骤降 → Listing 被压制/Buy Box 丢失
- 销量↑ + 毛利↓ → FBA 费用上涨/价格战
- BSR↓ + 库存积压 → 需求下降

请用结构化的中文回答，明确标注：
1. 异常维度和程度
2. 关联模式
3. 根因假设（标注置信度：高/中/低）
4. 建议的验证方向"""


def create_root_cause_agent() -> Agent:
    """创建根因分析 Agent（Claude Sonnet 4.6）。"""
    model = BedrockModel(
        model_id="us.anthropic.claude-sonnet-4-6",
        max_tokens=4096,
        region_name="us-east-1",
    )
    return Agent(
        model=model,
        tools=[get_asin_score, get_asin_metrics, get_metrics_trend, search_knowledge],
        system_prompt=SYSTEM_PROMPT,
        name="root_cause_agent",
        description="根因分析Agent，负责分析ASIN评分异常的根本原因",
    )
