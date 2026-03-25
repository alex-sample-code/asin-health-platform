"""竞品分析 Agent — 类目基准对比和竞品分析。

使用 Claude Sonnet 4.6 模型，工具：get_category_benchmark, get_competitor_list, get_asin_score, get_asin_metrics
"""

from __future__ import annotations

from strands import Agent
from strands.models import BedrockModel

from src.tools.score_tools import get_asin_score
from src.tools.metrics_tools import get_asin_metrics
from src.tools.benchmark_tools import get_category_benchmark, get_competitor_list

SYSTEM_PROMPT = """你是 ASIN 竞品分析专家。你的职责是：

1. 对比 ASIN 与类目基准（P25/中位数/P75），判断竞争力位置
2. 分析同类目竞品的优劣势
3. 识别市场机会和威胁
4. 给出竞争策略建议

分析维度：
- 价格定位: 与类目中位数的偏差
- 销量排名: BSR 在类目中的位置
- 转化率: CVR 是否高于类目 P75
- 广告效率: ACOS 是否低于类目中位数
- 评价质量: 评分和评价数量的竞争力
- 利润率: 毛利率与类目基准对比

竞争力等级：
- 领先: 多数指标 > P75
- 中等: 多数指标在 P25-P75 之间
- 落后: 多数指标 < P25

请用中文回答，给出清晰的竞争力评估和可执行的竞争策略。"""


def create_competitor_agent() -> Agent:
    """创建竞品分析 Agent（Claude Sonnet 4.6）。"""
    model = BedrockModel(
        model_id="us.anthropic.claude-sonnet-4-6",
        max_tokens=4096,
        region_name="us-east-1",
    )
    return Agent(
        model=model,
        tools=[get_asin_score, get_asin_metrics, get_category_benchmark, get_competitor_list],
        system_prompt=SYSTEM_PROMPT,
        name="competitor_agent",
        description="竞品分析Agent，负责类目基准对比和竞品分析",
    )
