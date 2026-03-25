"""类目基准和竞品对比工具 — 从 S3 读取，供 Agent 调用。"""

from __future__ import annotations

import json
import os
from typing import Any

import boto3
from strands import tool

S3_BUCKET = os.environ.get("S3_BUCKET", "asin-health-platform-data-959545103699")
REGION = os.environ.get("AWS_REGION", "us-east-1")

_s3 = None

# 缓存
_benchmarks_cache: dict[str, Any] | None = None
_competitors_cache: dict[str, list[dict[str, Any]]] | None = None
_profiles_by_asin: dict[str, dict[str, Any]] | None = None


def _get_s3():
    global _s3
    if _s3 is None:
        _s3 = boto3.client("s3", region_name=REGION)
    return _s3


def _load_s3_json(key: str) -> Any:
    resp = _get_s3().get_object(Bucket=S3_BUCKET, Key=key)
    return json.loads(resp["Body"].read())


def _load_benchmarks() -> dict[str, Any]:
    global _benchmarks_cache
    if _benchmarks_cache is not None:
        return _benchmarks_cache
    _benchmarks_cache = _load_s3_json("benchmarks/category_benchmarks.json")
    return _benchmarks_cache


def _load_competitors() -> dict[str, list[dict[str, Any]]]:
    global _competitors_cache
    if _competitors_cache is not None:
        return _competitors_cache
    _competitors_cache = _load_s3_json("benchmarks/competitor_asins.json")
    return _competitors_cache


def _load_profiles() -> dict[str, dict[str, Any]]:
    global _profiles_by_asin
    if _profiles_by_asin is not None:
        return _profiles_by_asin
    profiles = _load_s3_json("raw/asin_profiles.json")
    _profiles_by_asin = {p["asin"]: p for p in profiles}
    return _profiles_by_asin


@tool
def get_category_benchmark(asin: str) -> str:
    """获取 ASIN 所在类目的基准数据（P25/中位数/P75）。

    Args:
        asin: ASIN 编码，用于确定所属类目
    """
    profiles = _load_profiles()
    profile = profiles.get(asin)
    if profile is None:
        return json.dumps({"error": f"未找到 ASIN {asin}"}, ensure_ascii=False)

    category = profile["sub_category"]
    benchmarks = _load_benchmarks()
    bench = benchmarks.get(category)
    if bench is None:
        return json.dumps(
            {"error": f"未找到类目 '{category}' 的基准数据"},
            ensure_ascii=False,
        )

    result = {
        "asin": asin,
        "category": category,
        "asin_count_in_category": bench["asin_count"],
        "benchmarks": bench["metrics"],
    }
    return json.dumps(result, ensure_ascii=False, indent=2)


@tool
def get_competitor_list(asin: str) -> str:
    """获取 ASIN 所在类目的竞品列表。

    Args:
        asin: ASIN 编码，用于确定所属类目
    """
    profiles = _load_profiles()
    profile = profiles.get(asin)
    if profile is None:
        return json.dumps({"error": f"未找到 ASIN {asin}"}, ensure_ascii=False)

    category = profile["sub_category"]
    competitors = _load_competitors()
    comp_list = competitors.get(category, [])

    benchmarks = _load_benchmarks()
    bench = benchmarks.get(category)
    own_asins = bench["competitor_asins"] if bench else []

    result = {
        "asin": asin,
        "category": category,
        "own_asins_in_category": own_asins,
        "external_competitors": comp_list,
    }
    return json.dumps(result, ensure_ascii=False, indent=2)
