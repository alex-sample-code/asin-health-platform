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

SYSTEM_PROMPT = """你是 ASIN 运营行动建议专家。你的职责是：

1. 根据评分结果和根因分析，制定具体可执行的行动计划
2. 为每个建议标注优先级（P0紧急/P1高/P2中/P3低）和预期效果
3. 参考知识库中的 SOP 文档给出标准化操作步骤
4. 考虑 ASIN 生命周期阶段调整建议侧重点

行动计划结构：
- **紧急行动 (P0)**: 24小时内必须执行，阻止进一步恶化
- **高优先级 (P1)**: 本周内执行，直接改善核心指标
- **中优先级 (P2)**: 两周内执行，提升整体健康度
- **低优先级 (P3)**: 本月内执行，长期优化

生命周期侧重：
- 新品期: 侧重 Listing 优化、广告投放策略、评价积累
- 成长期: 侧重广告效率、库存管理、销量增长
- 成熟期: 侧重盈利优化、售后管理、竞品防御
- 衰退期: 侧重库存清理、成本控制、产品迭代

请用结构化的中文回答，每个行动建议包含：
1. 行动名称
2. 优先级 (P0-P3)
3. 具体步骤
4. 预期效果和时间线
5. 关联的 SOP 文档（如有）"""


def create_action_advisor_agent() -> Agent:
    """创建行动建议 Agent（Claude Sonnet 4.6）。"""
    model = BedrockModel(
        model_id="us.anthropic.claude-sonnet-4-6",
        max_tokens=8192,
        region_name="us-east-1",
    )
    return Agent(
        model=model,
        tools=[get_asin_score, get_asin_metrics, get_category_benchmark, search_knowledge],
        system_prompt=SYSTEM_PROMPT,
        name="action_advisor_agent",
        description="行动建议Agent，负责输出可执行的运营行动计划",
    )
