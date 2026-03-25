"""Strands @tool 函数 — Agent 可调用的工具集合。"""

from src.tools.score_tools import get_asin_score, get_score_summary, list_asins_by_health
from src.tools.metrics_tools import get_asin_metrics, get_metrics_trend
from src.tools.benchmark_tools import get_category_benchmark, get_competitor_list
from src.tools.knowledge_tools import search_knowledge

__all__ = [
    "get_asin_score",
    "get_score_summary",
    "list_asins_by_health",
    "get_asin_metrics",
    "get_metrics_trend",
    "get_category_benchmark",
    "get_competitor_list",
    "search_knowledge",
]
