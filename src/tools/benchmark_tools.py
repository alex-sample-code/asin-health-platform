"""类目基准和竞品对比工具 — 从 data/benchmarks/ 读取，供 Agent 调用。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from strands import tool

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
BENCHMARK_DIR = DATA_DIR / "benchmarks"
PROFILES_PATH = DATA_DIR / "raw" / "asin_profiles.json"

# 缓存
_benchmarks_cache: dict[str, Any] | None = None
_competitors_cache: dict[str, list[dict[str, Any]]] | None = None
_profiles_by_asin: dict[str, dict[str, Any]] | None = None


def _load_benchmarks() -> dict[str, Any]:
    global _benchmarks_cache
    if _benchmarks_cache is not None:
        return _benchmarks_cache
    path = BENCHMARK_DIR / "category_benchmarks.json"
    with open(path, "r", encoding="utf-8") as f:
        _benchmarks_cache = json.load(f)
    return _benchmarks_cache


def _load_competitors() -> dict[str, list[dict[str, Any]]]:
    global _competitors_cache
    if _competitors_cache is not None:
        return _competitors_cache
    path = BENCHMARK_DIR / "competitor_asins.json"
    with open(path, "r", encoding="utf-8") as f:
        _competitors_cache = json.load(f)
    return _competitors_cache


def _load_profiles() -> dict[str, dict[str, Any]]:
    global _profiles_by_asin
    if _profiles_by_asin is not None:
        return _profiles_by_asin
    with open(PROFILES_PATH, "r", encoding="utf-8") as f:
        profiles = json.load(f)
    _profiles_by_asin = {p["asin"]: p for p in profiles}
    return _profiles_by_asin


@tool
def get_category_benchmark(asin: str) -> str:
    """获取 ASIN 所在类目的基准数据（P25/中位数/P75）。

    返回该类目下各核心指标的分位数基准，便于判断 ASIN 在类目中的位置。

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

    返回同类目下的竞品 ASIN 列表，包含价格、评分、销量排名等信息。

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

    # 同类目自有 ASIN
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
