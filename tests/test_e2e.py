"""端到端集成测试 — 验证 @tool 函数直接调用的完整流程。

这些测试不依赖 LLM，直接调用 tool 函数验证数据流。
"""

from __future__ import annotations

import json
import pytest


class TestEndToEndDataFlow:
    """验证从数据到工具的完整数据流。"""

    def test_score_to_metrics_flow(self) -> None:
        """评分 → 指标联动：评分异常的 ASIN 可以查到原始指标。"""
        from src.tools.score_tools import list_asins_by_health
        from src.tools.metrics_tools import get_asin_metrics

        # 找到危险状态的 ASIN
        danger_list = json.loads(list_asins_by_health(health_label="danger", limit=3))
        assert danger_list["total"] > 0

        # 查询第一个危险 ASIN 的指标
        first_asin = danger_list["asins"][0]["asin"]
        metrics = json.loads(get_asin_metrics(asin=first_asin, days=7))
        assert metrics["asin"] == first_asin
        assert len(metrics["metrics"]) == 7

    def test_score_to_benchmark_flow(self) -> None:
        """评分 → 基准联动：任意 ASIN 都能查到类目基准。"""
        from src.tools.score_tools import get_asin_score
        from src.tools.benchmark_tools import get_category_benchmark

        score = json.loads(get_asin_score(asin="B000000071"))
        category = score["sub_category"]

        benchmark = json.loads(get_category_benchmark(asin="B000000071"))
        assert benchmark["category"] == category
        assert "benchmarks" in benchmark

    def test_anomaly_asin_analysis_flow(self) -> None:
        """异常 ASIN 完整分析流：评分 → 趋势 → 知识库。"""
        from src.tools.score_tools import get_asin_score
        from src.tools.metrics_tools import get_metrics_trend
        from src.tools.knowledge_tools import search_knowledge

        # B000000008 有异常标注（多维低分+A-to-Z投诉）
        score = json.loads(get_asin_score(asin="B000000008"))
        assert score["asin"] == "B000000008"

        # 找出最低维度
        dims = score["dimension_scores"]
        worst_dim = min(dims, key=dims.get)  # type: ignore[arg-type]

        # 查看该维度相关指标的趋势
        dim_metric_map = {
            "sales": "daily_orders",
            "inventory": "days_of_supply",
            "advertising": "acos",
            "after_sales": "return_rate",
            "profitability": "gross_margin",
            "listing": "buybox_pct",
        }
        metric_name = dim_metric_map[worst_dim]
        trend = json.loads(get_metrics_trend(asin="B000000008", metric_name=metric_name))
        assert trend["asin"] == "B000000008"

        # 搜索相关知识
        knowledge = json.loads(search_knowledge(query=f"{worst_dim} 异常"))
        assert knowledge["total_docs_searched"] > 0

    def test_all_100_asins_have_scores(self) -> None:
        """所有 100 个 ASIN 都应该有评分数据。"""
        from src.tools.score_tools import get_score_summary, get_asin_score

        summary = json.loads(get_score_summary())
        assert summary["total_asins"] == 100

        # 抽查几个 ASIN
        for asin_id in [0, 25, 50, 75, 99]:
            asin = f"B0{asin_id:08d}"
            result = json.loads(get_asin_score(asin=asin))
            assert "asin" in result, f"ASIN {asin} 未找到"

    def test_score_consistency(self) -> None:
        """评分一致性：final_score 应在 0-100 范围内。"""
        from src.tools.score_tools import _load_scores

        all_scores, _ = _load_scores()
        for s in all_scores:
            assert 0 <= s["trend_adjusted_score"] <= 100, (
                f"ASIN {s['asin']} 分数越界: {s['trend_adjusted_score']}"
            )
            for dim, val in s["dimension_scores"].items():
                assert 0 <= val <= 100, (
                    f"ASIN {s['asin']} 维度 {dim} 分数越界: {val}"
                )
