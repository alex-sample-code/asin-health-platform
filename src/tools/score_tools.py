"""评分查询工具 — 从 DynamoDB 读取评分数据，供 Agent 调用。"""

from __future__ import annotations

import json
import os
from decimal import Decimal
from typing import Any

import boto3
from strands import tool

TABLE_NAME = os.environ.get("DYNAMODB_TABLE", "asin-health-scores")
REGION = os.environ.get("AWS_REGION", "us-east-1")

# DynamoDB 客户端（延迟初始化）
_table = None

# 缓存
_scores_cache: list[dict[str, Any]] | None = None
_scores_by_asin: dict[str, dict[str, Any]] | None = None


def _get_table():
    """获取 DynamoDB Table resource。"""
    global _table
    if _table is None:
        dynamodb = boto3.resource("dynamodb", region_name=REGION)
        _table = dynamodb.Table(TABLE_NAME)
    return _table


def _decimal_to_float(obj: Any) -> Any:
    """递归将 Decimal 转为 float。"""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, dict):
        return {k: _decimal_to_float(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_decimal_to_float(i) for i in obj]
    return obj


def _load_scores() -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """从 DynamoDB 加载并缓存全部评分数据。"""
    global _scores_cache, _scores_by_asin
    if _scores_cache is not None and _scores_by_asin is not None:
        return _scores_cache, _scores_by_asin

    table = _get_table()
    items = []
    response = table.scan()
    items.extend(response.get("Items", []))
    while "LastEvaluatedKey" in response:
        response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
        items.extend(response.get("Items", []))

    # Decimal → float，去掉 DynamoDB key 字段
    cleaned = []
    for item in items:
        item = _decimal_to_float(item)
        item.pop("pk", None)
        item.pop("sk", None)
        cleaned.append(item)

    _scores_cache = cleaned
    _scores_by_asin = {s["asin"]: s for s in cleaned}
    return _scores_cache, _scores_by_asin


@tool
def get_asin_score(asin: str) -> str:
    """查询单个 ASIN 的健康度评分详情。

    返回该 ASIN 的综合分、六维度分数、健康标签、否决信息等完整评分结果。

    Args:
        asin: ASIN 编码，例如 "B000000001"
    """
    _, by_asin = _load_scores()
    score = by_asin.get(asin)
    if score is None:
        return json.dumps({"error": f"未找到 ASIN {asin} 的评分数据"}, ensure_ascii=False)
    return json.dumps(score, ensure_ascii=False, indent=2)


@tool
def get_score_summary() -> str:
    """获取所有 ASIN 的评分摘要统计。

    返回总数、健康标签分布、均分、最低分、最高分、生命周期统计等。
    """
    all_scores, _ = _load_scores()

    label_counts: dict[str, int] = {"healthy": 0, "warning": 0, "abnormal": 0, "danger": 0}
    lifecycle_stats: dict[str, list[float]] = {}

    for s in all_scores:
        label_counts[s["health_label"]] = label_counts.get(s["health_label"], 0) + 1
        lc = s["lifecycle"]
        lifecycle_stats.setdefault(lc, []).append(s["trend_adjusted_score"])

    scores_list = [s["trend_adjusted_score"] for s in all_scores]
    summary = {
        "total_asins": len(all_scores),
        "label_distribution": label_counts,
        "avg_score": round(sum(scores_list) / len(scores_list), 2),
        "min_score": min(scores_list),
        "max_score": max(scores_list),
        "veto_count": sum(1 for s in all_scores if s["veto_applied"]),
        "lifecycle_stats": {
            lc: {
                "count": len(vals),
                "avg": round(sum(vals) / len(vals), 2),
            }
            for lc, vals in lifecycle_stats.items()
        },
    }
    return json.dumps(summary, ensure_ascii=False, indent=2)


@tool
def list_asins_by_health(health_label: str, limit: int = 10) -> str:
    """按健康标签筛选 ASIN 列表。

    Args:
        health_label: 健康标签，可选值: "healthy", "warning", "abnormal", "danger"
        limit: 最多返回数量，默认 10
    """
    all_scores, _ = _load_scores()
    valid_labels = {"healthy", "warning", "abnormal", "danger"}
    if health_label not in valid_labels:
        return json.dumps(
            {"error": f"无效标签 '{health_label}'，可选: {', '.join(valid_labels)}"},
            ensure_ascii=False,
        )

    filtered = [
        {
            "asin": s["asin"],
            "lifecycle": s["lifecycle"],
            "sub_category": s["sub_category"],
            "final_score": s["trend_adjusted_score"],
            "health_label": s["health_label"],
            "veto_applied": s["veto_applied"],
        }
        for s in all_scores
        if s["health_label"] == health_label
    ]
    filtered.sort(key=lambda x: x["final_score"])
    result = {
        "health_label": health_label,
        "total": len(filtered),
        "showing": min(limit, len(filtered)),
        "asins": filtered[:limit],
    }
    return json.dumps(result, ensure_ascii=False, indent=2)
