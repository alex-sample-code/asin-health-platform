"""诊断结果缓存 — DynamoDB 持久化 + 内存缓存。"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any

import boto3
from boto3.dynamodb.conditions import Key

logger = logging.getLogger(__name__)

TABLE_NAME = os.environ.get("DIAGNOSIS_CACHE_TABLE", "asin-health-diagnosis-cache")
REGION = os.environ.get("AWS_REGION", "us-east-1")
CACHE_TTL_HOURS = int(os.environ.get("DIAGNOSIS_CACHE_TTL_HOURS", "24"))

_table = None
_memory_cache: dict[str, dict] = {}  # asin_id -> {data, timestamp}


def _get_table():
    global _table
    if _table is None:
        dynamodb = boto3.resource("dynamodb", region_name=REGION)
        _table = dynamodb.Table(TABLE_NAME)
    return _table


def save_diagnosis(asin_id: str, result: dict) -> None:
    """保存诊断结果到 DynamoDB + 内存缓存。"""
    now = datetime.now(timezone.utc)
    ts = now.isoformat()
    ttl_epoch = int(now.timestamp()) + CACHE_TTL_HOURS * 3600

    item = {
        "asin_id": asin_id,
        "timestamp": ts,
        "ttl": ttl_epoch,
        "result": json.dumps(result, ensure_ascii=False, default=str),
    }

    try:
        _get_table().put_item(Item=item)
    except Exception:
        logger.warning(f"Failed to save diagnosis cache for {asin_id}", exc_info=True)

    # 内存缓存
    _memory_cache[asin_id] = {"data": result, "timestamp": time.time()}


def get_diagnosis(asin_id: str, max_age_hours: int | None = None) -> dict | None:
    """获取诊断缓存。优先内存 → DynamoDB。
    
    Args:
        asin_id: ASIN ID
        max_age_hours: 最大缓存年龄（小时），None 则用默认 TTL
    
    Returns:
        诊断结果 dict，或 None（无缓存/已过期）
    """
    max_age = (max_age_hours or CACHE_TTL_HOURS) * 3600

    # 1. 内存缓存
    mem = _memory_cache.get(asin_id)
    if mem and (time.time() - mem["timestamp"]) < max_age:
        logger.debug(f"Diagnosis cache hit (memory) for {asin_id}")
        return mem["data"]

    # 2. DynamoDB
    try:
        resp = _get_table().get_item(Key={"asin_id": asin_id})
        item = resp.get("Item")
        if item:
            ts_str = item.get("timestamp", "")
            cached_time = datetime.fromisoformat(ts_str)
            age_sec = (datetime.now(timezone.utc) - cached_time).total_seconds()
            if age_sec < max_age:
                result = json.loads(item["result"])
                # 回填内存缓存
                _memory_cache[asin_id] = {"data": result, "timestamp": time.time()}
                logger.debug(f"Diagnosis cache hit (DynamoDB) for {asin_id}, age={age_sec:.0f}s")
                return result
    except Exception:
        logger.warning(f"Failed to read diagnosis cache for {asin_id}", exc_info=True)

    return None


def get_diagnosis_summary(asin_id: str) -> str | None:
    """获取诊断结果的简要摘要文本，用于注入 chat context。"""
    result = get_diagnosis(asin_id)
    if not result:
        return None

    lines = []
    lines.append(f"## ASIN {asin_id} 最近诊断结果")
    lines.append(f"健康度: {result.get('final_score', '?')} 分 ({result.get('health_label', '?')})")
    lines.append(f"摘要: {result.get('summary', '')}")

    # 根因
    rcs = result.get("root_causes", [])
    if rcs:
        lines.append("根因假设:")
        for rc in rcs[:3]:
            lines.append(f"  - [{rc.get('confidence', '?')}] {rc.get('hypothesis', '')}")

    # 行动建议
    actions = result.get("action_plan", [])
    if actions:
        lines.append("行动建议:")
        for a in actions[:5]:
            lines.append(f"  - [{a.get('priority', '?')}] {a.get('title', '')}")

    # 竞品
    bm = result.get("benchmark")
    if bm:
        lines.append(f"类目位置: {bm.get('category_position', '?')}")
        weak = bm.get("weak_vs_benchmark", [])
        if weak:
            lines.append(f"弱项: {', '.join(weak[:3])}")

    return "\n".join(lines)


def invalidate(asin_id: str) -> None:
    """手动失效某个 ASIN 的缓存。"""
    _memory_cache.pop(asin_id, None)
    try:
        _get_table().delete_item(Key={"asin_id": asin_id})
    except Exception:
        logger.warning(f"Failed to invalidate cache for {asin_id}", exc_info=True)
