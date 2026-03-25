"""评分工具和指标工具的单元测试。"""

from __future__ import annotations

import json
import pytest

from src.tools.score_tools import get_asin_score, get_score_summary, list_asins_by_health
from src.tools.metrics_tools import get_asin_metrics, get_metrics_trend
from src.tools.benchmark_tools import get_category_benchmark, get_competitor_list
from src.tools.knowledge_tools import search_knowledge


# ── 评分工具测试 ─────────────────────────────────────────────────────────


class TestScoreTools:
    def test_get_asin_score_valid(self) -> None:
        """查询存在的 ASIN 应返回完整评分。"""
        result = json.loads(get_asin_score(asin="B000000071"))
        assert result["asin"] == "B000000071"
        assert "sales_score" in result
        assert "inventory_score" in result
        assert "advertising_score" in result
        assert "after_sales_score" in result
        assert "profitability_score" in result
        assert "listing_score" in result
        assert "health_label" in result
        assert result["health_label"] in {"healthy", "warning", "abnormal", "danger"}

    def test_get_asin_score_invalid(self) -> None:
        """查询不存在的 ASIN 应返回错误。"""
        result = json.loads(get_asin_score(asin="INVALID_ASIN"))
        assert "error" in result

    def test_get_score_summary(self) -> None:
        """评分摘要应包含统计信息。"""
        result = json.loads(get_score_summary())
        assert result["total_asins"] == 100
        assert "label_distribution" in result
        assert "avg_score" in result
        assert result["avg_score"] > 0
        # 标签分布总数应等于 100
        dist = result["label_distribution"]
        total = sum(dist.values())
        assert total == 100

    def test_list_asins_by_health(self) -> None:
        """按标签筛选应返回正确的结果。"""
        result = json.loads(list_asins_by_health(health_label="danger", limit=5))
        assert result["health_label"] == "danger"
        assert result["total"] > 0
        assert len(result["asins"]) <= 5
        for asin_info in result["asins"]:
            assert asin_info["health_label"] == "danger"

    def test_list_asins_by_health_invalid_label(self) -> None:
        """无效标签应返回错误。"""
        result = json.loads(list_asins_by_health(health_label="invalid"))
        assert "error" in result


# ── 指标工具测试 ─────────────────────────────────────────────────────────


class TestMetricsTools:
    def test_get_asin_metrics(self) -> None:
        """获取 ASIN 指标应返回每日数据。"""
        result = json.loads(get_asin_metrics(asin="B000000071", days=7))
        assert result["asin"] == "B000000071"
        assert len(result["metrics"]) == 7
        # 检查指标字段
        first_day = result["metrics"][0]
        assert "daily_orders" in first_day
        assert "cvr" in first_day
        assert "acos" in first_day

    def test_get_asin_metrics_invalid(self) -> None:
        """无效 ASIN 应返回错误。"""
        result = json.loads(get_asin_metrics(asin="INVALID"))
        assert "error" in result

    def test_get_metrics_trend(self) -> None:
        """指标趋势应包含统计信息。"""
        result = json.loads(get_metrics_trend(asin="B000000071", metric_name="daily_orders"))
        assert result["asin"] == "B000000071"
        assert result["metric_name"] == "daily_orders"
        assert len(result["daily_values"]) == 30
        assert result["trend"] in {"上升", "下降", "稳定", "数据不足"}
        assert result["avg_7d"] >= 0

    def test_get_metrics_trend_invalid_metric(self) -> None:
        """无效指标名应返回错误。"""
        result = json.loads(get_metrics_trend(asin="B000000071", metric_name="nonexistent"))
        assert "error" in result


# ── 基准工具测试 ─────────────────────────────────────────────────────────


class TestBenchmarkTools:
    def test_get_category_benchmark(self) -> None:
        """类目基准应返回分位数数据。"""
        result = json.loads(get_category_benchmark(asin="B000000071"))
        assert result["asin"] == "B000000071"
        assert "category" in result
        assert "benchmarks" in result
        benchmarks = result["benchmarks"]
        assert "avg_orders" in benchmarks
        assert "median" in benchmarks["avg_orders"]
        assert "p25" in benchmarks["avg_orders"]
        assert "p75" in benchmarks["avg_orders"]

    def test_get_competitor_list(self) -> None:
        """竞品列表应返回内外部竞品。"""
        result = json.loads(get_competitor_list(asin="B000000071"))
        assert result["asin"] == "B000000071"
        assert "own_asins_in_category" in result
        assert "external_competitors" in result
        assert len(result["external_competitors"]) >= 5


# ── 知识库工具测试 ────────────────────────────────────────────────────────


class TestKnowledgeTools:
    def test_search_knowledge_chinese(self) -> None:
        """中文关键词搜索应返回结果。"""
        result = json.loads(search_knowledge(query="退货率高怎么处理"))
        assert result["total_docs_searched"] == 7
        assert len(result["results"]) > 0

    def test_search_knowledge_english(self) -> None:
        """英文关键词搜索应返回结果。"""
        result = json.loads(search_knowledge(query="ACOS optimization"))
        assert len(result["results"]) > 0

    def test_search_knowledge_relevance(self) -> None:
        """搜索退货相关应优先返回退货处理文档。"""
        result = json.loads(search_knowledge(query="退货"))
        top_result = result["results"][0]
        assert "退货" in top_result["document"]
