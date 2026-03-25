"""Agent 执行日志 — 记录每次 Agent 调用的完整 trajectory。"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any

import boto3

logger = logging.getLogger(__name__)

TABLE_NAME = os.environ.get("AGENT_LOG_TABLE", "asin-health-agent-logs")
REGION = os.environ.get("AWS_REGION", "us-east-1")
ENABLE_LOGGING = os.environ.get("AGENT_LOG_ENABLED", "true").lower() == "true"

_table = None


def _get_table():
    global _table
    if _table is None:
        dynamodb = boto3.resource("dynamodb", region_name=REGION)
        _table = dynamodb.Table(TABLE_NAME)
    return _table


class AgentTracer:
    """跟踪 Agent 执行的 context manager。"""

    def __init__(self, agent_name: str, asin_id: str, trigger: str = "diagnosis"):
        self.agent_name = agent_name
        self.asin_id = asin_id
        self.trigger = trigger
        self.start_time = 0.0
        self.end_time = 0.0
        self.tool_calls: list[str] = []
        self.success = False
        self.error_msg = ""
        self.output_length = 0

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        if exc_type is not None:
            self.success = False
            self.error_msg = str(exc_val)[:500]
        self._save_log()
        return False  # don't suppress exceptions

    def record_tool_call(self, tool_name: str):
        self.tool_calls.append(tool_name)

    def record_output(self, output: str):
        self.output_length = len(output)
        self.success = True

    def _save_log(self):
        if not ENABLE_LOGGING:
            return
        try:
            now = datetime.now(timezone.utc)
            log_entry = {
                "pk": f"AGENT#{self.agent_name}",
                "sk": f"TS#{now.strftime('%Y%m%d%H%M%S')}#{self.asin_id}",
                "agent_name": self.agent_name,
                "asin_id": self.asin_id,
                "trigger": self.trigger,
                "timestamp": now.isoformat(),
                "duration_sec": round(self.end_time - self.start_time, 2),
                "tool_calls": self.tool_calls,
                "tool_call_count": len(self.tool_calls),
                "output_chars": self.output_length,
                "success": self.success,
                "error": self.error_msg,
            }
            _get_table().put_item(Item=log_entry)
        except Exception:
            # 日志写入失败不影响主流程
            logger.warning("Failed to save agent log", exc_info=True)


def log_diagnosis_result(asin_id: str, duration_sec: float, agents_used: list[str],
                         root_causes_count: int, actions_count: int, success: bool):
    """记录一次完整诊断的汇总日志。"""
    if not ENABLE_LOGGING:
        return
    try:
        now = datetime.now(timezone.utc)
        _get_table().put_item(Item={
            "pk": "DIAGNOSIS",
            "sk": f"TS#{now.strftime('%Y%m%d%H%M%S')}#{asin_id}",
            "asin_id": asin_id,
            "timestamp": now.isoformat(),
            "duration_sec": round(duration_sec, 2),
            "agents_used": agents_used,
            "root_causes_count": root_causes_count,
            "actions_count": actions_count,
            "success": success,
        })
    except Exception:
        logger.warning("Failed to save diagnosis log", exc_info=True)
