"""FastAPI 端点测试 — 使用 TestClient，不依赖 LLM。"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.api.main import app


client = TestClient(app)


# ── 健康检查 ──────────────────────────────────────────────────────────────


class TestHealthCheck:
    def test_health_check(self) -> None:
        """健康检查应返回 200。"""
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["service"] == "asin-health-platform"
        assert data["version"] == "0.1.0"


# ── 单个 ASIN 评分查询 ───────────────────────────────────────────────────


class TestGetScore:
    def test_get_valid_asin(self) -> None:
        """查询存在的 ASIN 应返回完整评分。"""
        resp = client.get("/scores/B000000071")
        assert resp.status_code == 200
        data = resp.json()
        assert data["asin"] == "B000000071"
        assert "sales_score" in data
        assert "inventory_score" in data
        assert "health_label" in data
        assert data["health_label"] in {"healthy", "warning", "abnormal", "danger"}

    def test_get_invalid_asin(self) -> None:
        """查询不存在的 ASIN 应返回 404。"""
        resp = client.get("/scores/INVALID_ASIN")
        assert resp.status_code == 404
        assert "未找到" in resp.json()["detail"]

    def test_score_fields_complete(self) -> None:
        """返回的评分应包含所有六维度分数。"""
        resp = client.get("/scores/B000000008")
        assert resp.status_code == 200
        data = resp.json()
        required_fields = [
            "asin", "seller_id", "marketplace_id", "lifecycle",
            "sub_category", "date", "sales_score", "inventory_score",
            "advertising_score", "after_sales_score", "profitability_score",
            "listing_score", "weighted_score", "final_score",
            "trend_adjusted_score", "health_label", "dimension_scores",
        ]
        for field in required_fields:
            assert field in data, f"缺少字段: {field}"


# ── 评分列表查询 ──────────────────────────────────────────────────────────


class TestListScores:
    def test_list_all_scores(self) -> None:
        """不带过滤应返回全部 100 个 ASIN。"""
        resp = client.get("/scores")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 100

    def test_filter_by_health_label(self) -> None:
        """按健康标签过滤应只返回匹配结果。"""
        resp = client.get("/scores?health_label=danger")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] > 0
        for score in data["scores"]:
            assert score["health_label"] == "danger"

    def test_filter_by_lifecycle(self) -> None:
        """按生命周期过滤应只返回匹配结果。"""
        resp = client.get("/scores?lifecycle=new")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] > 0
        for score in data["scores"]:
            assert score["lifecycle"] == "new"

    def test_filter_combined(self) -> None:
        """同时按标签和生命周期过滤。"""
        resp = client.get("/scores?health_label=healthy&lifecycle=mature")
        assert resp.status_code == 200
        data = resp.json()
        for score in data["scores"]:
            assert score["health_label"] == "healthy"
            assert score["lifecycle"] == "mature"

    def test_limit_parameter(self) -> None:
        """limit 参数应限制返回数量。"""
        resp = client.get("/scores?limit=5")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["scores"]) <= 5

    def test_invalid_health_label(self) -> None:
        """无效标签应返回 400。"""
        resp = client.get("/scores?health_label=invalid")
        assert resp.status_code == 400
        assert "无效健康标签" in resp.json()["detail"]

    def test_invalid_lifecycle(self) -> None:
        """无效生命周期应返回 400。"""
        resp = client.get("/scores?lifecycle=invalid")
        assert resp.status_code == 400
        assert "无效生命周期" in resp.json()["detail"]

    def test_scores_sorted_by_score(self) -> None:
        """返回结果应按分数升序排列。"""
        resp = client.get("/scores?health_label=danger")
        assert resp.status_code == 200
        scores = resp.json()["scores"]
        if len(scores) >= 2:
            for i in range(len(scores) - 1):
                assert scores[i]["trend_adjusted_score"] <= scores[i + 1]["trend_adjusted_score"]


# ── Chat 端点（不实际调用 LLM）────────────────────────────────────────────


class TestChat:
    def test_chat_empty_message(self) -> None:
        """空消息应返回 422 验证错误。"""
        resp = client.post("/chat", json={"message": ""})
        assert resp.status_code == 422

    def test_chat_missing_message(self) -> None:
        """缺少 message 字段应返回 422。"""
        resp = client.post("/chat", json={})
        assert resp.status_code == 422


# ── CORS ──────────────────────────────────────────────────────────────────


class TestCORS:
    def test_cors_headers(self) -> None:
        """OPTIONS 请求应返回 CORS 头。"""
        resp = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert resp.headers.get("access-control-allow-origin") is not None
