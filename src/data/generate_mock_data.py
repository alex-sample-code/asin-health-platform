"""
模拟数据生成器 — 生成 100 个 ASIN 的 30 天每日指标数据。

分布：25 新品期 + 30 成长期 + 30 成熟期 + 15 衰退期
至少 10 个 ASIN 含多维度关联异常（用于根因分析测试）
"""

from __future__ import annotations

import json
import random
import math
from dataclasses import dataclass, field, asdict
from datetime import date, timedelta
from pathlib import Path
from typing import Any

# ── 常量 ──────────────────────────────────────────────────────────────────────

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
RAW_DIR = DATA_DIR / "raw"
BENCHMARK_DIR = DATA_DIR / "benchmarks"

SELLER_ID = "SELLER001"
MARKETPLACE_ID = "ATVPDKIKX0DER"  # US marketplace

# 子类目列表
SUB_CATEGORIES: list[str] = [
    "Home & Kitchen > Kitchen Utensils",
    "Home & Kitchen > Storage & Organization",
    "Electronics > Phone Accessories",
    "Electronics > Computer Accessories",
    "Sports & Outdoors > Fitness Equipment",
    "Beauty & Personal Care > Skin Care",
    "Toys & Games > Building Sets",
    "Office Products > Desk Accessories",
]

# 生命周期阶段
LIFECYCLE_NEW = "new"          # 上架 < 90 天
LIFECYCLE_GROWTH = "growth"    # 90-365 天, 销量上升
LIFECYCLE_MATURE = "mature"    # > 365 天, 销量稳定
LIFECYCLE_DECLINE = "decline"  # 连续 60 天销量下降

# 异常场景定义（至少 10 个 ASIN）
ANOMALY_SCENARIOS: list[dict[str, Any]] = [
    # 1. 销量下降 + 差评上升 + 退货率高
    {"id": "anomaly_sales_review", "desc": "销量下降+差评上升+退货率高",
     "sales_mult": 0.4, "return_rate_add": 0.12, "rating_sub": 1.2, "negative_pct_add": 0.25},
    # 2. 广告费暴涨 + 转化率下降 + CPC 上升
    {"id": "anomaly_ad_cost", "desc": "广告费暴涨+转化率下降+CPC上升",
     "ad_spend_mult": 2.5, "cvr_mult": 0.4, "cpc_mult": 2.0},
    # 3. 库存充足 + 销量骤降 + 无差评变化 (Listing 被压制)
    {"id": "anomaly_listing_suppressed", "desc": "库存充足+销量骤降+Listing被压制",
     "sales_mult": 0.2, "inventory_days": 120, "buybox_pct": 0.1, "title_score_sub": 40},
    # 4. 销量上升 + 毛利率下降 (FBA 费用上涨)
    {"id": "anomaly_margin_squeeze", "desc": "销量上升+毛利率下降",
     "sales_mult": 1.5, "fba_fee_mult": 1.6, "margin_squeeze": True},
    # 5. 退货率上升 + 单一原因集中
    {"id": "anomaly_return_spike", "desc": "退货率上升+单一原因集中",
     "return_rate_add": 0.18, "rating_sub": 0.5},
    # 6. 广告依赖过高 + ACOS 失控
    {"id": "anomaly_ad_dependency", "desc": "广告依赖过高+ACOS失控",
     "ad_order_ratio": 0.8, "acos_mult": 2.5},
    # 7. BSR 暴跌 + 库存积压
    {"id": "anomaly_bsr_inventory", "desc": "BSR暴跌+库存积压",
     "bsr_mult": 5.0, "inventory_days": 180, "excess_pct": 0.35},
    # 8. 新品广告烧钱 + 无转化
    {"id": "anomaly_new_no_cvr", "desc": "新品广告烧钱+无转化",
     "ad_spend_mult": 3.0, "cvr_mult": 0.15, "sales_mult": 0.3},
    # 9. 多维低分 + A-to-Z 投诉
    {"id": "anomaly_atoz", "desc": "多维低分+A-to-Z投诉",
     "atoz_claims": 5, "rating_sub": 1.8, "return_rate_add": 0.20, "sales_mult": 0.3},
    # 10. 价格战 + 毛利转负
    {"id": "anomaly_price_war", "desc": "价格战+毛利转负",
     "selling_price_mult": 0.5, "margin_squeeze": True, "sales_mult": 0.6},
    # 11. 季节性库存断货
    {"id": "anomaly_stockout", "desc": "季节性库存断货",
     "inventory_days": 2, "sales_mult": 0.15},
    # 12. IPI 低分 + 仓储费暴涨
    {"id": "anomaly_ipi_storage", "desc": "IPI低分+仓储费暴涨",
     "ipi_score": 220, "storage_cost_pct_add": 0.15, "excess_pct": 0.35, "sales_mult": 0.5},
]

random.seed(42)


# ── 数据模型 ────────────────────────────────────────────────────────────────

@dataclass
class AsinProfile:
    """单个 ASIN 的基础资料"""
    asin: str
    seller_id: str
    marketplace_id: str
    sub_category: str
    lifecycle: str
    days_since_launch: int
    anomaly: dict[str, Any] | None = None  # 异常场景参数


@dataclass
class DailyMetrics:
    """一天的完整指标"""
    date: str
    # 销量
    daily_orders: int = 0
    daily_sales_amount: float = 0.0
    sessions: int = 0
    cvr: float = 0.0
    bsr: int = 0
    bsr_category: str = ""
    # 库存
    fba_available: int = 0
    fba_inbound: int = 0
    days_of_supply: float = 0.0
    ipi_score: int = 0
    excess_inventory_pct: float = 0.0
    storage_cost_pct: float = 0.0
    # 广告
    ad_spend: float = 0.0
    ad_sales: float = 0.0
    acos: float = 0.0
    roas: float = 0.0
    cpc: float = 0.0
    ctr: float = 0.0
    ad_orders: int = 0
    total_orders: int = 0
    # 售后
    return_rate: float = 0.0
    avg_rating: float = 0.0
    review_count: int = 0
    recent_negative_pct: float = 0.0
    atoz_claims: int = 0
    policy_warnings: int = 0
    # 盈利
    selling_price: float = 0.0
    fba_fee: float = 0.0
    referral_fee: float = 0.0
    ad_cost_per_unit: float = 0.0
    cogs: float = 0.0
    shipping_cost: float = 0.0
    gross_margin: float = 0.0
    # Listing
    title_score: int = 0
    image_count: int = 0
    has_aplus: bool = False
    bullet_count: int = 0
    search_terms_filled: bool = False
    buybox_pct: float = 0.0


# ── 辅助函数 ────────────────────────────────────────────────────────────────

def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _rand_normal(mu: float, sigma: float, lo: float | None = None, hi: float | None = None) -> float:
    """截断正态分布"""
    v = random.gauss(mu, sigma)
    if lo is not None:
        v = max(lo, v)
    if hi is not None:
        v = min(hi, v)
    return v


def _trend_series(base: float, days: int, trend: float, noise: float) -> list[float]:
    """生成带趋势和噪声的时间序列"""
    vals: list[float] = []
    for i in range(days):
        t = base + trend * i + random.gauss(0, noise)
        vals.append(max(0, t))
    return vals


# ── ASIN 资料生成 ─────────────────────────────────────────────────────────

def _generate_profiles() -> list[AsinProfile]:
    """生成 100 个 ASIN 的基础资料（含生命周期和异常分配）"""
    profiles: list[AsinProfile] = []
    idx = 0

    lifecycle_dist: list[tuple[str, int, tuple[int, int]]] = [
        (LIFECYCLE_NEW, 25, (7, 89)),
        (LIFECYCLE_GROWTH, 30, (90, 365)),
        (LIFECYCLE_MATURE, 30, (366, 1200)),
        (LIFECYCLE_DECLINE, 15, (200, 900)),
    ]

    # 分配异常场景到前 12 个 ASIN（跨各生命周期）
    anomaly_assignments: dict[int, dict[str, Any]] = {}
    for ai, scenario in enumerate(ANOMALY_SCENARIOS):
        anomaly_assignments[ai] = scenario

    for lifecycle, count, (day_lo, day_hi) in lifecycle_dist:
        for i in range(count):
            asin = f"B0{idx:08d}"
            days_since = random.randint(day_lo, day_hi)
            cat = random.choice(SUB_CATEGORIES)
            anomaly = anomaly_assignments.get(idx)
            profiles.append(AsinProfile(
                asin=asin,
                seller_id=SELLER_ID,
                marketplace_id=MARKETPLACE_ID,
                sub_category=cat,
                lifecycle=lifecycle,
                days_since_launch=days_since,
                anomaly=anomaly,
            ))
            idx += 1

    random.shuffle(profiles)
    return profiles


# ── 每日指标生成 ──────────────────────────────────────────────────────────

def _base_params(lifecycle: str) -> dict[str, Any]:
    """根据生命周期返回基础指标参数范围"""
    if lifecycle == LIFECYCLE_NEW:
        return {
            "orders_base": random.uniform(2, 12),
            "orders_trend": random.uniform(0.05, 0.4),
            "price": random.uniform(15, 60),
            "sessions_base": random.uniform(30, 150),
            "cvr_base": random.uniform(0.04, 0.14),
            "bsr_base": random.randint(40000, 180000),
            "ad_spend_base": random.uniform(20, 80),
            "rating_base": random.uniform(3.6, 4.8),
            "review_count_base": random.randint(3, 40),
            "ipi_base": random.randint(400, 700),
            "fba_available_base": random.randint(80, 400),
        }
    elif lifecycle == LIFECYCLE_GROWTH:
        return {
            "orders_base": random.uniform(12, 45),
            "orders_trend": random.uniform(0.15, 0.7),
            "price": random.uniform(18, 75),
            "sessions_base": random.uniform(120, 450),
            "cvr_base": random.uniform(0.07, 0.20),
            "bsr_base": random.randint(5000, 55000),
            "ad_spend_base": random.uniform(25, 100),
            "rating_base": random.uniform(3.9, 4.8),
            "review_count_base": random.randint(40, 300),
            "ipi_base": random.randint(420, 750),
            "fba_available_base": random.randint(200, 1000),
        }
    elif lifecycle == LIFECYCLE_MATURE:
        return {
            "orders_base": random.uniform(30, 100),
            "orders_trend": random.uniform(-0.1, 0.1),
            "price": random.uniform(20, 90),
            "sessions_base": random.uniform(300, 1000),
            "cvr_base": random.uniform(0.10, 0.25),
            "bsr_base": random.randint(1000, 20000),
            "ad_spend_base": random.uniform(20, 100),
            "rating_base": random.uniform(4.0, 4.7),
            "review_count_base": random.randint(200, 2000),
            "ipi_base": random.randint(500, 800),
            "fba_available_base": random.randint(300, 2000),
        }
    else:  # decline
        return {
            "orders_base": random.uniform(15, 45),
            "orders_trend": random.uniform(-1.0, -0.4),
            "price": random.uniform(15, 70),
            "sessions_base": random.uniform(80, 300),
            "cvr_base": random.uniform(0.05, 0.13),
            "bsr_base": random.randint(30000, 120000),
            "ad_spend_base": random.uniform(10, 60),
            "rating_base": random.uniform(3.4, 4.3),
            "review_count_base": random.randint(100, 1500),
            "ipi_base": random.randint(300, 580),
            "fba_available_base": random.randint(400, 2500),
        }


def _generate_daily_metrics(profile: AsinProfile, num_days: int = 30) -> list[dict[str, Any]]:
    """为一个 ASIN 生成 num_days 天的每日指标"""
    params = _base_params(profile.lifecycle)
    anomaly = profile.anomaly or {}
    today = date(2026, 3, 25)
    start_date = today - timedelta(days=num_days - 1)

    # 基础时间序列
    orders_series = _trend_series(
        params["orders_base"], num_days,
        params["orders_trend"],
        params["orders_base"] * 0.15,
    )
    sessions_series = _trend_series(
        params["sessions_base"], num_days,
        params["orders_trend"] * 3,
        params["sessions_base"] * 0.1,
    )

    # 异常：销量乘数（后 7 天生效更强）
    sales_mult = anomaly.get("sales_mult", 1.0)
    cvr_mult = anomaly.get("cvr_mult", 1.0)
    ad_spend_mult = anomaly.get("ad_spend_mult", 1.0)
    cpc_mult = anomaly.get("cpc_mult", 1.0)
    selling_price_mult = anomaly.get("selling_price_mult", 1.0)
    fba_fee_mult = anomaly.get("fba_fee_mult", 1.0)
    bsr_mult = anomaly.get("bsr_mult", 1.0)

    price = params["price"] * selling_price_mult
    cogs = price * random.uniform(0.20, 0.35)
    fba_fee_base = price * random.uniform(0.12, 0.20) * fba_fee_mult
    referral_fee = price * 0.15
    shipping_cost = random.uniform(1.5, 4.0)

    # Listing 质量（相对稳定）
    base_title_score = random.randint(60, 95)
    title_score = max(10, base_title_score - anomaly.get("title_score_sub", 0))
    image_count = random.randint(4, 9)
    has_aplus = random.random() < 0.6
    bullet_count = random.randint(3, 5)
    search_terms_filled = random.random() < 0.8
    buybox_base = random.uniform(0.85, 1.0)
    if "buybox_pct" in anomaly:
        buybox_base = anomaly["buybox_pct"]

    # 评价相关
    rating_base = params["rating_base"] - anomaly.get("rating_sub", 0.0)
    rating_base = _clamp(rating_base, 1.0, 5.0)
    review_count = params["review_count_base"]
    negative_pct_base = _clamp(0.5 - rating_base * 0.08 + anomaly.get("negative_pct_add", 0.0), 0.02, 0.60)

    # IPI
    ipi_base = anomaly.get("ipi_score", params["ipi_base"])

    metrics: list[dict[str, Any]] = []
    for day_idx in range(num_days):
        d = start_date + timedelta(days=day_idx)
        # 后 7 天异常更明显
        anomaly_factor = 1.0 if day_idx < num_days - 7 else 1.0
        if anomaly and day_idx >= num_days - 7:
            anomaly_factor = 1.0  # 异常在最后 7 天才完全体现

        # ── 销量 ─────────────────────────────────────────
        raw_orders = orders_series[day_idx]
        if anomaly and day_idx >= num_days - 10:
            raw_orders *= sales_mult
        daily_orders = max(0, int(round(raw_orders)))

        sessions = max(10, int(round(sessions_series[day_idx])))
        cvr = _clamp(
            (daily_orders / sessions if sessions > 0 else 0.05) * cvr_mult,
            0.005, 0.50,
        )
        # 重新根据 cvr 调整 orders（保持一致性）
        daily_orders = max(0, int(round(sessions * cvr)))
        daily_sales_amount = round(daily_orders * price, 2)

        bsr = max(1, int(params["bsr_base"] * bsr_mult + random.gauss(0, params["bsr_base"] * 0.05)))

        # ── 库存 ─────────────────────────────────────────
        inv_days_target = anomaly.get("inventory_days", random.uniform(30, 60))
        avg_daily_orders = max(1, sum(orders_series[:day_idx + 1]) / (day_idx + 1) * sales_mult)
        fba_available = max(0, int(avg_daily_orders * inv_days_target + random.gauss(0, 20)))
        fba_inbound = max(0, int(random.uniform(0, avg_daily_orders * 14)))
        days_of_supply = round(fba_available / avg_daily_orders, 1) if avg_daily_orders > 0 else 0
        ipi_score = int(_clamp(ipi_base + random.gauss(0, 15), 0, 1000))
        excess_inv_base = anomaly.get("excess_pct", random.uniform(0.0, 0.10))
        excess_inventory_pct = round(_clamp(excess_inv_base + random.gauss(0, 0.02), 0, 1), 4)
        storage_base = random.uniform(0.02, 0.06) + anomaly.get("storage_cost_pct_add", 0.0)
        storage_cost_pct = round(_clamp(storage_base + random.gauss(0, 0.005), 0, 0.5), 4)

        # ── 广告 ─────────────────────────────────────────
        # 先确定广告订单占比（通常 25-55% 的订单来自广告）
        ad_order_ratio_val = anomaly.get("ad_order_ratio", None)
        if ad_order_ratio_val is not None:
            ad_pct = ad_order_ratio_val
        else:
            ad_pct = _clamp(random.gauss(0.38, 0.12), 0.10, 0.70)

        ad_orders_val = max(1, int(daily_orders * ad_pct))
        total_orders_val = daily_orders  # 广告订单已含在 daily_orders 内

        ad_sales_val = round(ad_orders_val * price, 2)

        # 目标 ACOS（正常 15-35%，异常场景可调高）
        target_acos = _clamp(random.gauss(0.25, 0.08), 0.10, 0.50)
        if "acos_mult" in anomaly:
            target_acos = _clamp(target_acos * anomaly["acos_mult"], 0.10, 3.0)

        ad_spend = round(max(1, ad_sales_val * target_acos * ad_spend_mult), 2)
        cpc = round(_clamp(random.uniform(0.5, 2.5) * cpc_mult, 0.1, 15.0), 2)
        clicks = max(1, int(ad_spend / cpc)) if cpc > 0 else 0
        ctr = round(_clamp(random.uniform(0.004, 0.015), 0.001, 0.05), 4)

        acos_val = round(ad_spend / ad_sales_val, 4) if ad_sales_val > 0 else 9.99
        acos_val = _clamp(acos_val, 0, 9.99)
        roas_val = round(ad_sales_val / ad_spend, 2) if ad_spend > 0 else 0

        # ── 售后 ─────────────────────────────────────────
        base_return = random.uniform(0.02, 0.06)
        return_rate = round(_clamp(base_return + anomaly.get("return_rate_add", 0.0), 0, 0.50), 4)
        avg_rating = round(_clamp(rating_base + random.gauss(0, 0.05), 1.0, 5.0), 1)
        review_ct = review_count + day_idx  # 每天涨一点
        recent_neg = round(_clamp(negative_pct_base + random.gauss(0, 0.02), 0, 1), 4)
        atoz = anomaly.get("atoz_claims", 0)
        if atoz > 0 and day_idx >= num_days - 7:
            atoz_today = random.randint(0, 2)
        else:
            atoz_today = 0
        policy_warn = 0
        if atoz > 0:
            policy_warn = random.randint(0, 1)

        # ── 盈利 ─────────────────────────────────────────
        ad_cost_per_unit = round(ad_spend / total_orders_val, 2) if total_orders_val > 0 else 0
        total_cost = fba_fee_base + referral_fee + ad_cost_per_unit + cogs + shipping_cost
        gross_margin_val = round((price - total_cost) / price, 4) if price > 0 else 0
        if anomaly.get("margin_squeeze"):
            gross_margin_val = _clamp(gross_margin_val, -0.15, 0.08)

        # ── Listing ──────────────────────────────────────
        buybox_today = round(_clamp(buybox_base + random.gauss(0, 0.02), 0, 1), 4)

        m = DailyMetrics(
            date=d.isoformat(),
            daily_orders=daily_orders,
            daily_sales_amount=daily_sales_amount,
            sessions=sessions,
            cvr=round(cvr, 4),
            bsr=bsr,
            bsr_category=profile.sub_category,
            fba_available=fba_available,
            fba_inbound=fba_inbound,
            days_of_supply=days_of_supply,
            ipi_score=ipi_score,
            excess_inventory_pct=excess_inventory_pct,
            storage_cost_pct=storage_cost_pct,
            ad_spend=ad_spend,
            ad_sales=ad_sales_val,
            acos=acos_val,
            roas=roas_val,
            cpc=cpc,
            ctr=ctr,
            ad_orders=ad_orders_val,
            total_orders=total_orders_val,
            return_rate=return_rate,
            avg_rating=avg_rating,
            review_count=review_ct,
            recent_negative_pct=recent_neg,
            atoz_claims=atoz_today,
            policy_warnings=policy_warn,
            selling_price=round(price, 2),
            fba_fee=round(fba_fee_base, 2),
            referral_fee=round(referral_fee, 2),
            ad_cost_per_unit=ad_cost_per_unit,
            cogs=round(cogs, 2),
            shipping_cost=round(shipping_cost, 2),
            gross_margin=gross_margin_val,
            title_score=title_score,
            image_count=image_count,
            has_aplus=has_aplus,
            bullet_count=bullet_count,
            search_terms_filled=search_terms_filled,
            buybox_pct=buybox_today,
        )
        metrics.append(asdict(m))

    return metrics


# ── 类目基准生成 ──────────────────────────────────────────────────────────

def _generate_benchmarks(all_data: dict[str, list[dict[str, Any]]],
                         profiles: list[AsinProfile]) -> dict[str, Any]:
    """按子类目计算基准指标（median, P25, P75）"""
    cat_metrics: dict[str, list[dict[str, Any]]] = {}
    profile_map = {p.asin: p for p in profiles}

    for asin, daily_list in all_data.items():
        cat = profile_map[asin].sub_category
        if cat not in cat_metrics:
            cat_metrics[cat] = []
        # 取最近 7 天均值
        recent = daily_list[-7:]
        cat_metrics[cat].append({
            "asin": asin,
            "avg_orders": sum(d["daily_orders"] for d in recent) / len(recent),
            "avg_cvr": sum(d["cvr"] for d in recent) / len(recent),
            "avg_acos": sum(d["acos"] for d in recent) / len(recent),
            "avg_rating": sum(d["avg_rating"] for d in recent) / len(recent),
            "avg_margin": sum(d["gross_margin"] for d in recent) / len(recent),
            "avg_bsr": sum(d["bsr"] for d in recent) / len(recent),
            "avg_return_rate": sum(d["return_rate"] for d in recent) / len(recent),
            "avg_sessions": sum(d["sessions"] for d in recent) / len(recent),
        })

    benchmarks: dict[str, Any] = {}
    for cat, items in cat_metrics.items():
        bench: dict[str, Any] = {"category": cat, "asin_count": len(items), "metrics": {}}
        for metric_key in ["avg_orders", "avg_cvr", "avg_acos", "avg_rating",
                           "avg_margin", "avg_bsr", "avg_return_rate", "avg_sessions"]:
            vals = sorted(v[metric_key] for v in items)
            n = len(vals)
            if n == 0:
                continue
            bench["metrics"][metric_key] = {
                "p25": round(vals[max(0, n // 4 - 1)], 4),
                "median": round(vals[n // 2], 4),
                "p75": round(vals[max(0, 3 * n // 4 - 1)], 4),
                "min": round(vals[0], 4),
                "max": round(vals[-1], 4),
            }
        # 竞品列表：每个类目里的 ASIN
        bench["competitor_asins"] = [item["asin"] for item in items]
        benchmarks[cat] = bench

    return benchmarks


# ── 主流程 ────────────────────────────────────────────────────────────────

def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    BENCHMARK_DIR.mkdir(parents=True, exist_ok=True)

    print("生成 ASIN 资料...")
    profiles = _generate_profiles()

    # 统计
    lifecycle_counts = {}
    anomaly_count = 0
    for p in profiles:
        lifecycle_counts[p.lifecycle] = lifecycle_counts.get(p.lifecycle, 0) + 1
        if p.anomaly:
            anomaly_count += 1
    print(f"  生命周期分布: {lifecycle_counts}")
    print(f"  异常 ASIN 数: {anomaly_count}")

    print("生成 30 天每日指标...")
    all_data: dict[str, list[dict[str, Any]]] = {}
    profiles_data: list[dict[str, Any]] = []

    for p in profiles:
        daily = _generate_daily_metrics(p, 30)
        all_data[p.asin] = daily
        profiles_data.append({
            "asin": p.asin,
            "seller_id": p.seller_id,
            "marketplace_id": p.marketplace_id,
            "sub_category": p.sub_category,
            "lifecycle": p.lifecycle,
            "days_since_launch": p.days_since_launch,
            "anomaly_desc": p.anomaly["desc"] if p.anomaly else None,
        })

    # 保存 ASIN 资料
    profiles_path = RAW_DIR / "asin_profiles.json"
    with open(profiles_path, "w", encoding="utf-8") as f:
        json.dump(profiles_data, f, ensure_ascii=False, indent=2)
    print(f"  ASIN 资料 → {profiles_path}")

    # 保存每日指标（每个 ASIN 一个文件）
    for asin, daily in all_data.items():
        p = RAW_DIR / f"{asin}_daily.json"
        with open(p, "w", encoding="utf-8") as f:
            json.dump(daily, f, ensure_ascii=False, indent=2)
    print(f"  每日指标 → {RAW_DIR}/ (100 文件)")

    # 保存汇总文件（所有 ASIN 合并）
    summary_path = RAW_DIR / "all_asins_daily.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    print(f"  汇总数据 → {summary_path}")

    print("生成类目基准...")
    benchmarks = _generate_benchmarks(all_data, profiles)
    bench_path = BENCHMARK_DIR / "category_benchmarks.json"
    with open(bench_path, "w", encoding="utf-8") as f:
        json.dump(benchmarks, f, ensure_ascii=False, indent=2)
    print(f"  类目基准 → {bench_path}")

    # 竞品数据（按类目生成 5-10 个虚拟竞品）
    competitors: dict[str, list[dict[str, Any]]] = {}
    for cat in SUB_CATEGORIES:
        comp_list: list[dict[str, Any]] = []
        for ci in range(random.randint(5, 10)):
            comp_list.append({
                "asin": f"COMP_{cat[:4].upper().replace(' ', '')}_{ci:03d}",
                "category": cat,
                "avg_price": round(random.uniform(10, 100), 2),
                "avg_rating": round(random.uniform(3.5, 4.8), 1),
                "review_count": random.randint(50, 5000),
                "bsr": random.randint(500, 80000),
                "monthly_est_sales": random.randint(100, 5000),
            })
        competitors[cat] = comp_list

    comp_path = BENCHMARK_DIR / "competitor_asins.json"
    with open(comp_path, "w", encoding="utf-8") as f:
        json.dump(competitors, f, ensure_ascii=False, indent=2)
    print(f"  竞品数据 → {comp_path}")

    print(f"\n数据生成完成！共 {len(profiles)} 个 ASIN, 每个 30 天指标。")


if __name__ == "__main__":
    main()
