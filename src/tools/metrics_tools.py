"""原始指标查询工具 — 从 S3 读取每日指标，供 Agent 调用。"""

from __future__ import annotations

import json
import os
from typing import Any

import boto3
from strands import tool

S3_BUCKET = os.environ.get("S3_BUCKET", "asin-health-platform-data-959545103699")
REGION = os.environ.get("AWS_REGION", "us-east-1")

# S3 客户端（延迟初始化）
_s3 = None

# 缓存
_profiles_cache: dict[str, dict[str, Any]] | None = None
_metrics_cache: dict[str, list[dict[str, Any]]] = {}


def _get_s3():
    global _s3
    if _s3 is None:
        _s3 = boto3.client("s3", region_name=REGION)
    return _s3


def _load_s3_json(key: str) -> Any:
    """从 S3 加载 JSON 文件。"""
    resp = _get_s3().get_object(Bucket=S3_BUCKET, Key=key)
    return json.loads(resp["Body"].read())


def _load_profiles() -> dict[str, dict[str, Any]]:
    """从 S3 加载 ASIN 资料映射。"""
    global _profiles_cache
    if _profiles_cache is not None:
        return _profiles_cache
    profiles = _load_s3_json("raw/asin_profiles.json")
    _profiles_cache = {p["asin"]: p for p in profiles}
    return _profiles_cache


def _load_daily(asin: str) -> list[dict[str, Any]] | None:
    """从 S3 加载单个 ASIN 的每日指标。"""
    if asin in _metrics_cache:
        return _metrics_cache[asin]
    try:
        data = _load_s3_json(f"raw/{asin}_daily.json")
        _metrics_cache[asin] = data
        return data
    except Exception:
        return None


@tool
def get_asin_metrics(asin: str, days: int = 7) -> str:
    """查询 ASIN 最近 N 天指标的聚合摘要（均值/最新值/趋势）。

    返回 ASIN 基础资料和关键指标的汇总统计，不返回每日明细。

    Args:
        asin: ASIN 编码，例如 "B000000001"
        days: 统计天数，默认 7（最大 30）
    """
    profiles = _load_profiles()
    profile = profiles.get(asin)
    if profile is None:
        return json.dumps({"error": f"未找到 ASIN {asin}"}, ensure_ascii=False)

    daily = _load_daily(asin)
    if daily is None:
        return json.dumps({"error": f"未找到 ASIN {asin} 的每日指标"}, ensure_ascii=False)

    days = min(days, len(daily))
    recent = daily[-days:]

    # 聚合关键指标
    key_metrics = [
        "daily_orders", "daily_revenue", "cvr", "sessions",
        "cpc", "acos", "ad_spend", "return_rate", "avg_rating",
        "review_count", "gross_margin", "bsr", "fba_stock_days",
    ]
    summary = {}
    for metric in key_metrics:
        vals = [d.get(metric) for d in recent if d.get(metric) is not None]
        if vals:
            summary[metric] = {
                "latest": round(vals[-1], 4),
                "avg": round(sum(vals) / len(vals), 4),
                "min": round(min(vals), 4),
                "max": round(max(vals), 4),
            }

    result = {
        "asin": asin,
        "profile": {k: profile[k] for k in ["asin", "category", "sub_category", "price", "lifecycle"] if k in profile},
        "days": days,
        "metrics_summary": summary,
    }
    return json.dumps(result, ensure_ascii=False, indent=2)


@tool
def get_metrics_trend(asin: str, metric_name: str) -> str:
    """查询 ASIN 某个指标的 30 天趋势数据。

    返回指标的每日值、7 天均值、30 天均值、变化趋势等。

    Args:
        asin: ASIN 编码
        metric_name: 指标名称，如 "daily_orders", "cvr", "acos", "return_rate", "gross_margin" 等
    """
    daily = _load_daily(asin)
    if daily is None:
        return json.dumps({"error": f"未找到 ASIN {asin} 的指标数据"}, ensure_ascii=False)

    # 验证指标名
    if metric_name not in daily[0]:
        available = [k for k in daily[0].keys() if k != "date"]
        return json.dumps(
            {"error": f"无效指标 '{metric_name}'，可用指标: {', '.join(available)}"},
            ensure_ascii=False,
        )

    values = [d[metric_name] for d in daily]
    dates = [d["date"] for d in daily]

    # 计算统计
    recent_7 = values[-7:]
    avg_7d = sum(recent_7) / len(recent_7) if recent_7 else 0
    avg_30d = sum(values) / len(values) if values else 0

    # 趋势判断
    first_half = values[:15]
    second_half = values[15:]
    if first_half and second_half:
        avg_first = sum(first_half) / len(first_half)
        avg_second = sum(second_half) / len(second_half)
        if avg_first > 0:
            change_pct = (avg_second - avg_first) / avg_first
        else:
            change_pct = 0.0
        if change_pct > 0.1:
            trend = "上升"
        elif change_pct < -0.1:
            trend = "下降"
        else:
            trend = "稳定"
    else:
        change_pct = 0.0
        trend = "数据不足"

    result = {
        "asin": asin,
        "metric_name": metric_name,
        "avg_7d": round(avg_7d, 4),
        "avg_30d": round(avg_30d, 4),
        "min": round(min(values), 4) if values else None,
        "max": round(max(values), 4) if values else None,
        "latest": round(values[-1], 4) if values else None,
        "change_pct": round(change_pct, 4),
        "trend": trend,
    }
    return json.dumps(result, ensure_ascii=False, indent=2)
