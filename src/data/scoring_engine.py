"""
确定性评分引擎 — 六维度加权评分 + 生命周期动态权重 + 短板一票否决。

评分完全确定性（无 LLM），可重复、可审计。
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
RAW_DIR = DATA_DIR / "raw"
SCORES_DIR = DATA_DIR / "scores"

# ── 生命周期动态权重 ─────────────────────────────────────────────────────

LIFECYCLE_WEIGHTS: dict[str, dict[str, float]] = {
    "new": {
        "sales": 0.15, "inventory": 0.15, "advertising": 0.20,
        "after_sales": 0.10, "profitability": 0.10, "listing": 0.30,
    },
    "growth": {
        "sales": 0.25, "inventory": 0.20, "advertising": 0.20,
        "after_sales": 0.10, "profitability": 0.15, "listing": 0.10,
    },
    "mature": {
        "sales": 0.25, "inventory": 0.20, "advertising": 0.15,
        "after_sales": 0.15, "profitability": 0.15, "listing": 0.10,
    },
    "decline": {
        "sales": 0.20, "inventory": 0.25, "advertising": 0.10,
        "after_sales": 0.15, "profitability": 0.20, "listing": 0.10,
    },
}


# ── 工具函数 ──────────────────────────────────────────────────────────────

def _clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, v))


def _linear_score(value: float, worst: float, best: float) -> float:
    """线性映射到 0-100 分，worst→0, best→100"""
    if best == worst:
        return 50.0
    raw = (value - worst) / (best - worst) * 100
    return _clamp(raw)


def _inverse_score(value: float, best: float, worst: float) -> float:
    """反向映射：值越小越好（如 ACOS、退货率）"""
    return _linear_score(value, worst, best)


# ── 六维度评分函数 ────────────────────────────────────────────────────────

def score_sales(metrics_7d: list[dict[str, Any]], metrics_30d: list[dict[str, Any]]) -> float:
    """
    销量维度评分 (0-100)
    综合考虑：日均订单量、CVR、BSR 排名、销量趋势
    """
    if not metrics_7d:
        return 0.0

    avg_orders_7d = sum(m["daily_orders"] for m in metrics_7d) / len(metrics_7d)
    avg_cvr_7d = sum(m["cvr"] for m in metrics_7d) / len(metrics_7d)
    avg_bsr_7d = sum(m["bsr"] for m in metrics_7d) / len(metrics_7d)
    avg_sessions_7d = sum(m["sessions"] for m in metrics_7d) / len(metrics_7d)

    # 子分：订单量（0-100 映射，0 单→0 分，55+ 单→100 分）
    orders_score = _linear_score(avg_orders_7d, 0, 55)

    # 子分：CVR（0%→0, 22%→100）
    cvr_score = _linear_score(avg_cvr_7d, 0, 0.22)

    # 子分：BSR（越小越好，1→100, 100000→0）
    bsr_score = _inverse_score(avg_bsr_7d, 1, 100000)

    # 子分：流量（sessions）
    sessions_score = _linear_score(avg_sessions_7d, 0, 700)

    # 趋势：比较前 7 天 vs 后 7 天订单
    if len(metrics_30d) >= 14:
        first_7 = sum(m["daily_orders"] for m in metrics_30d[:7]) / 7
        last_7 = sum(m["daily_orders"] for m in metrics_30d[-7:]) / 7
        if first_7 > 0:
            trend_pct = (last_7 - first_7) / first_7
        else:
            trend_pct = 0.0
        trend_score = _clamp(50 + trend_pct * 100, 0, 100)
    else:
        trend_score = 50.0

    # 加权合成
    final = (
        orders_score * 0.30
        + cvr_score * 0.25
        + bsr_score * 0.15
        + sessions_score * 0.15
        + trend_score * 0.15
    )
    return round(_clamp(final), 2)


def score_inventory(metrics_7d: list[dict[str, Any]]) -> float:
    """
    库存维度评分 (0-100)
    综合考虑：库存天数、IPI 分数、超龄库存占比、仓储费占比
    """
    if not metrics_7d:
        return 0.0

    avg_dos = sum(m["days_of_supply"] for m in metrics_7d) / len(metrics_7d)
    avg_ipi = sum(m["ipi_score"] for m in metrics_7d) / len(metrics_7d)
    avg_excess = sum(m["excess_inventory_pct"] for m in metrics_7d) / len(metrics_7d)
    avg_storage = sum(m["storage_cost_pct"] for m in metrics_7d) / len(metrics_7d)

    # 库存天数：30-60 天最优(100分)，<7 或 >120 → 0 分
    if 30 <= avg_dos <= 60:
        dos_score = 100.0
    elif avg_dos < 30:
        dos_score = _linear_score(avg_dos, 0, 30)
    else:
        dos_score = _inverse_score(avg_dos, 60, 180)

    # IPI 分数（0-1000，>500 优秀）
    ipi_score = _linear_score(avg_ipi, 200, 700)

    # 超龄库存占比（越低越好）
    excess_score = _inverse_score(avg_excess, 0, 0.30)

    # 仓储费占比（越低越好）
    storage_score = _inverse_score(avg_storage, 0, 0.15)

    final = (
        dos_score * 0.35
        + ipi_score * 0.30
        + excess_score * 0.20
        + storage_score * 0.15
    )
    return round(_clamp(final), 2)


def score_advertising(metrics_7d: list[dict[str, Any]]) -> float:
    """
    广告维度评分 (0-100)
    综合考虑：ACOS、ROAS、CTR、广告订单占比
    """
    if not metrics_7d:
        return 0.0

    avg_acos = sum(m["acos"] for m in metrics_7d) / len(metrics_7d)
    avg_roas = sum(m["roas"] for m in metrics_7d) / len(metrics_7d)
    avg_ctr = sum(m["ctr"] for m in metrics_7d) / len(metrics_7d)

    # 广告订单占比
    total_ad = sum(m["ad_orders"] for m in metrics_7d)
    total_all = sum(m["total_orders"] for m in metrics_7d)
    ad_ratio = total_ad / total_all if total_all > 0 else 0.5

    # ACOS（越低越好，<10% 优秀，>80% 很差）
    acos_score = _inverse_score(avg_acos, 0.08, 1.0)

    # ROAS（越高越好）
    roas_score = _linear_score(avg_roas, 0, 6)

    # CTR（越高越好）
    ctr_score = _linear_score(avg_ctr, 0, 0.02)

    # 广告依赖度（20-60% 正常，>80% 过度依赖）
    if 0.15 <= ad_ratio <= 0.60:
        dep_score = 100.0
    elif ad_ratio < 0.15:
        dep_score = _linear_score(ad_ratio, 0, 0.15) * 0.7 + 30
    else:
        dep_score = _inverse_score(ad_ratio, 0.60, 1.0)

    final = (
        acos_score * 0.30
        + roas_score * 0.25
        + ctr_score * 0.20
        + dep_score * 0.25
    )
    return round(_clamp(final), 2)


def score_after_sales(metrics_7d: list[dict[str, Any]]) -> float:
    """
    售后维度评分 (0-100)
    综合考虑：退货率、评分、差评率、A-to-Z 投诉
    """
    if not metrics_7d:
        return 0.0

    avg_return = sum(m["return_rate"] for m in metrics_7d) / len(metrics_7d)
    avg_rating = sum(m["avg_rating"] for m in metrics_7d) / len(metrics_7d)
    avg_negative = sum(m["recent_negative_pct"] for m in metrics_7d) / len(metrics_7d)
    total_atoz = sum(m["atoz_claims"] for m in metrics_7d)
    total_policy = sum(m["policy_warnings"] for m in metrics_7d)

    # 退货率（越低越好，<2% 优秀，>25% 很差）
    return_score = _inverse_score(avg_return, 0.01, 0.30)

    # 评分（1-5，4.5+ 优秀）
    rating_score = _linear_score(avg_rating, 2.5, 4.7)

    # 差评占比
    negative_score = _inverse_score(avg_negative, 0.02, 0.40)

    # A-to-Z 投诉（0 最好，>3 很差）
    atoz_score = _inverse_score(total_atoz, 0, 5)

    # 政策警告
    policy_score = _inverse_score(total_policy, 0, 3)

    final = (
        return_score * 0.25
        + rating_score * 0.30
        + negative_score * 0.20
        + atoz_score * 0.15
        + policy_score * 0.10
    )
    return round(_clamp(final), 2)


def score_profitability(metrics_7d: list[dict[str, Any]]) -> float:
    """
    盈利性维度评分 (0-100)
    综合考虑：毛利率、广告成本占比、FBA 费用合理性
    """
    if not metrics_7d:
        return 0.0

    avg_margin = sum(m["gross_margin"] for m in metrics_7d) / len(metrics_7d)
    avg_price = sum(m["selling_price"] for m in metrics_7d) / len(metrics_7d)
    avg_fba = sum(m["fba_fee"] for m in metrics_7d) / len(metrics_7d)
    avg_ad_cost = sum(m["ad_cost_per_unit"] for m in metrics_7d) / len(metrics_7d)

    # 毛利率（-10%→0, 30%→100）
    margin_score = _linear_score(avg_margin, -0.10, 0.30)

    # FBA 费用占售价比（越低越好）
    fba_ratio = avg_fba / avg_price if avg_price > 0 else 0.3
    fba_score = _inverse_score(fba_ratio, 0.05, 0.40)

    # 广告成本/单（越低越好）
    ad_unit_score = _inverse_score(avg_ad_cost, 0, 15)

    final = (
        margin_score * 0.50
        + fba_score * 0.25
        + ad_unit_score * 0.25
    )
    return round(_clamp(final), 2)


def score_listing(metrics_7d: list[dict[str, Any]]) -> float:
    """
    Listing 质量维度评分 (0-100)
    综合考虑：标题评分、图片数、A+ 页面、五点描述、搜索词、Buy Box 占比
    """
    if not metrics_7d:
        return 0.0

    # Listing 指标取最新一天
    latest = metrics_7d[-1]

    title_score = _linear_score(latest["title_score"], 30, 95)
    image_score = _linear_score(latest["image_count"], 1, 9)
    aplus_score = 100.0 if latest["has_aplus"] else 30.0
    bullet_score = _linear_score(latest["bullet_count"], 0, 5)
    search_score = 100.0 if latest["search_terms_filled"] else 20.0
    buybox_score = _linear_score(latest["buybox_pct"], 0, 1.0)

    final = (
        title_score * 0.20
        + image_score * 0.15
        + aplus_score * 0.10
        + bullet_score * 0.10
        + search_score * 0.10
        + buybox_score * 0.35
    )
    return round(_clamp(final), 2)


# ── 综合评分 ──────────────────────────────────────────────────────────────

@dataclass
class AsinScore:
    """单个 ASIN 的评分结果"""
    asin: str
    seller_id: str
    marketplace_id: str
    lifecycle: str
    sub_category: str
    date: str
    # 六维度分数
    sales_score: float
    inventory_score: float
    advertising_score: float
    after_sales_score: float
    profitability_score: float
    listing_score: float
    # 加权综合分
    weighted_score: float
    # 短板否决后综合分
    final_score: float
    # 趋势修正后
    trend_adjusted_score: float
    # 健康标签
    health_label: str
    # 否决信息
    veto_applied: str | None
    # 维度详情
    dimension_scores: dict[str, float]


def _apply_veto(score: float, dimensions: dict[str, float]) -> tuple[float, str | None]:
    """短板一票否决机制"""
    veto_msg: str | None = None
    scores = list(dimensions.values())

    # 任一维度 < 20 → 综合分 max 30
    dims_under_20 = [k for k, v in dimensions.items() if v < 20]
    if dims_under_20:
        score = min(score, 30.0)
        veto_msg = f"维度<20({', '.join(dims_under_20)})→强制危险"
        return score, veto_msg

    # 任一维度 < 40 → 综合分 max 50
    dims_under_40 = [k for k, v in dimensions.items() if v < 40]
    if dims_under_40:
        score = min(score, 50.0)
        veto_msg = f"维度<40({', '.join(dims_under_40)})→最多预警"
        return score, veto_msg

    # 两个及以上维度 < 60 → 综合分 max 55
    dims_under_60 = [k for k, v in dimensions.items() if v < 60]
    if len(dims_under_60) >= 2:
        score = min(score, 55.0)
        veto_msg = f"两个维度<60({', '.join(dims_under_60)})→最多预警"
        return score, veto_msg

    return score, veto_msg


def _health_label(score: float) -> str:
    """根据分数返回健康标签"""
    if score >= 80:
        return "healthy"
    elif score >= 60:
        return "warning"
    elif score >= 40:
        return "abnormal"
    else:
        return "danger"


def compute_asin_score(
    asin: str,
    profile: dict[str, Any],
    metrics_30d: list[dict[str, Any]],
    prev_7d_score: float | None = None,
) -> AsinScore:
    """计算单个 ASIN 的完整评分"""
    lifecycle = profile["lifecycle"]
    weights = LIFECYCLE_WEIGHTS[lifecycle]
    score_date = metrics_30d[-1]["date"] if metrics_30d else "unknown"

    metrics_7d = metrics_30d[-7:] if len(metrics_30d) >= 7 else metrics_30d

    # 计算六维度分数
    s_sales = score_sales(metrics_7d, metrics_30d)
    s_inventory = score_inventory(metrics_7d)
    s_advertising = score_advertising(metrics_7d)
    s_after_sales = score_after_sales(metrics_7d)
    s_profitability = score_profitability(metrics_7d)
    s_listing = score_listing(metrics_7d)

    dimensions = {
        "sales": s_sales,
        "inventory": s_inventory,
        "advertising": s_advertising,
        "after_sales": s_after_sales,
        "profitability": s_profitability,
        "listing": s_listing,
    }

    # 加权综合分
    weighted = (
        s_sales * weights["sales"]
        + s_inventory * weights["inventory"]
        + s_advertising * weights["advertising"]
        + s_after_sales * weights["after_sales"]
        + s_profitability * weights["profitability"]
        + s_listing * weights["listing"]
    )
    weighted = round(weighted, 2)

    # 短板否决
    final, veto_msg = _apply_veto(weighted, dimensions)
    final = round(final, 2)

    # 趋势修正：7 天综合分变化
    trend_adjusted = final
    if prev_7d_score is not None:
        delta = final - prev_7d_score
        if delta < -15:
            trend_adjusted = round(final - 10, 2)
        elif delta > 15:
            trend_adjusted = round(final + 5, 2)
    trend_adjusted = round(_clamp(trend_adjusted), 2)

    label = _health_label(trend_adjusted)

    return AsinScore(
        asin=asin,
        seller_id=profile["seller_id"],
        marketplace_id=profile["marketplace_id"],
        lifecycle=lifecycle,
        sub_category=profile["sub_category"],
        date=score_date,
        sales_score=s_sales,
        inventory_score=s_inventory,
        advertising_score=s_advertising,
        after_sales_score=s_after_sales,
        profitability_score=s_profitability,
        listing_score=s_listing,
        weighted_score=weighted,
        final_score=final,
        trend_adjusted_score=trend_adjusted,
        health_label=label,
        veto_applied=veto_msg,
        dimension_scores=dimensions,
    )


# ── 批量评分 + 7 日前分数计算 ─────────────────────────────────────────────

def _compute_prev_score(profile: dict[str, Any], metrics_30d: list[dict[str, Any]]) -> float | None:
    """用前 23 天数据计算 7 天前的综合分（用于趋势修正）"""
    if len(metrics_30d) < 23:
        return None
    prev_30d = metrics_30d[:23]
    prev_7d = prev_30d[-7:]
    lifecycle = profile["lifecycle"]
    weights = LIFECYCLE_WEIGHTS[lifecycle]

    s = {
        "sales": score_sales(prev_7d, prev_30d),
        "inventory": score_inventory(prev_7d),
        "advertising": score_advertising(prev_7d),
        "after_sales": score_after_sales(prev_7d),
        "profitability": score_profitability(prev_7d),
        "listing": score_listing(prev_7d),
    }
    weighted = sum(s[k] * weights[k] for k in weights)
    final, _ = _apply_veto(weighted, s)
    return round(final, 2)


def main() -> None:
    SCORES_DIR.mkdir(parents=True, exist_ok=True)

    # 加载 ASIN 资料
    profiles_path = RAW_DIR / "asin_profiles.json"
    with open(profiles_path, "r", encoding="utf-8") as f:
        profiles: list[dict[str, Any]] = json.load(f)

    print(f"加载 {len(profiles)} 个 ASIN 资料")

    all_scores: list[dict[str, Any]] = []
    label_counts: dict[str, int] = {"healthy": 0, "warning": 0, "abnormal": 0, "danger": 0}

    for profile in profiles:
        asin = profile["asin"]
        # 加载每日指标
        daily_path = RAW_DIR / f"{asin}_daily.json"
        with open(daily_path, "r", encoding="utf-8") as f:
            metrics_30d: list[dict[str, Any]] = json.load(f)

        # 计算 7 天前的分数（用于趋势修正）
        prev_score = _compute_prev_score(profile, metrics_30d)

        # 计算当前评分
        result = compute_asin_score(asin, profile, metrics_30d, prev_score)
        score_dict = asdict(result)
        all_scores.append(score_dict)
        label_counts[result.health_label] += 1

    # 保存全部评分
    scores_path = SCORES_DIR / "all_scores.json"
    with open(scores_path, "w", encoding="utf-8") as f:
        json.dump(all_scores, f, ensure_ascii=False, indent=2)
    print(f"评分结果 → {scores_path}")

    # 统计
    total = len(all_scores)
    print(f"\n{'='*50}")
    print(f"评分统计 (共 {total} 个 ASIN):")
    print(f"  🟢 健康 (80-100): {label_counts['healthy']} ({label_counts['healthy']/total*100:.1f}%)")
    print(f"  🟡 预警 (60-79):  {label_counts['warning']} ({label_counts['warning']/total*100:.1f}%)")
    print(f"  🟠 异常 (40-59):  {label_counts['abnormal']} ({label_counts['abnormal']/total*100:.1f}%)")
    print(f"  🔴 危险 (0-39):   {label_counts['danger']} ({label_counts['danger']/total*100:.1f}%)")
    print(f"{'='*50}")

    # 分数分布
    scores_list = [s["trend_adjusted_score"] for s in all_scores]
    avg_score = sum(scores_list) / len(scores_list)
    min_score = min(scores_list)
    max_score = max(scores_list)
    print(f"  均分: {avg_score:.1f}, 最低: {min_score}, 最高: {max_score}")

    # 否决统计
    veto_count = sum(1 for s in all_scores if s["veto_applied"])
    print(f"  短板否决: {veto_count} 个 ASIN")

    # 按生命周期统计
    for lc in ["new", "growth", "mature", "decline"]:
        lc_scores = [s for s in all_scores if s["lifecycle"] == lc]
        if lc_scores:
            avg = sum(s["trend_adjusted_score"] for s in lc_scores) / len(lc_scores)
            print(f"  {lc}: {len(lc_scores)} 个, 均分 {avg:.1f}")


if __name__ == "__main__":
    main()
