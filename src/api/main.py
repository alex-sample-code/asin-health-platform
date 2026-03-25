"""ASIN 智能健康度分析平台 — FastAPI REST API。

运行: uv run uvicorn src.api.main:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src.api.diagnosis import DiagnosisResponse, run_diagnosis, run_diagnosis_stream
from src.tools.score_tools import _load_scores

logger = logging.getLogger(__name__)

# ── FastAPI 实例 ──────────────────────────────────────────────────────────

app = FastAPI(
    title="ASIN 智能健康度分析平台",
    description="基于 Strands Agents SDK 的 Multi-Agent 系统，提供 ASIN 健康度评分查询和智能分析。",
    version="0.1.0",
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Pydantic 模型 ─────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    """聊天请求"""
    message: str = Field(..., min_length=1, description="用户问题")


class ChatResponse(BaseModel):
    """聊天响应"""
    response: str
    status: str = "success"


class ScoreResponse(BaseModel):
    """单个 ASIN 评分响应"""
    asin: str
    seller_id: str
    marketplace_id: str
    lifecycle: str
    sub_category: str
    date: str
    sales_score: float
    inventory_score: float
    advertising_score: float
    after_sales_score: float
    profitability_score: float
    listing_score: float
    weighted_score: float
    final_score: float
    trend_adjusted_score: float
    health_label: str
    veto_applied: str | None
    dimension_scores: dict[str, float]


class ScoreListResponse(BaseModel):
    """评分列表响应"""
    total: int
    scores: list[dict[str, Any]]


class HealthCheckResponse(BaseModel):
    """健康检查响应"""
    status: str = "ok"
    service: str = "asin-health-platform"
    version: str = "0.1.0"


# ── Supervisor Agent 延迟初始化 ────────────────────────────────────────────

_supervisor = None


def _get_supervisor():
    """延迟初始化 Supervisor Agent（首次调用时创建）。"""
    global _supervisor
    if _supervisor is None:
        from src.agents.supervisor_agent import create_supervisor_agent
        _supervisor = create_supervisor_agent()
    return _supervisor


# ── API 端点 ──────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthCheckResponse, tags=["系统"])
def health_check() -> HealthCheckResponse:
    """健康检查端点。"""
    return HealthCheckResponse()


@app.post("/chat", response_model=ChatResponse, tags=["智能分析"])
def chat(request: ChatRequest) -> ChatResponse:
    """与 Supervisor Agent 对话，提交分析问题。

    示例问题:
    - 查询 B000000008 的健康度评分
    - 帮我全面分析 B000000000 的状态
    - 列出所有危险状态的 ASIN
    """
    try:
        supervisor = _get_supervisor()
        result = supervisor(request.message)
        return ChatResponse(response=str(result))
    except Exception as e:
        logger.exception("Supervisor Agent 调用失败")
        raise HTTPException(status_code=500, detail=f"Agent 调用失败: {e}")


@app.get("/scores/{asin_id}", response_model=ScoreResponse, tags=["评分查询"])
def get_score(asin_id: str) -> ScoreResponse:
    """查询单个 ASIN 的健康度评分。

    Args:
        asin_id: ASIN 编码，如 B000000001
    """
    _, by_asin = _load_scores()
    score = by_asin.get(asin_id)
    if score is None:
        raise HTTPException(status_code=404, detail=f"未找到 ASIN {asin_id} 的评分数据")
    return ScoreResponse(**score)


@app.post("/diagnosis/{asin_id}", tags=["智能诊断"])
def diagnose_asin(asin_id: str) -> StreamingResponse:
    """对指定 ASIN 执行 SSE 流式智能诊断，并行调用 Agent 逐步推送结果。

    SSE 事件顺序：problem_overview → root_cause / benchmark (并行) → action_plan → done
    失败的模块会推送 error 事件，其他模块正常展示。
    """
    # 预检 ASIN 是否存在
    from src.tools.score_tools import _load_scores as _check_scores
    _, by_asin = _check_scores()
    if asin_id not in by_asin:
        raise HTTPException(status_code=404, detail=f"未找到 ASIN {asin_id} 的评分数据")

    return StreamingResponse(
        run_diagnosis_stream(asin_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


VALID_LABELS = {"healthy", "warning", "abnormal", "danger"}


@app.get("/scores", response_model=ScoreListResponse, tags=["评分查询"])
def list_scores(
    health_label: str | None = Query(None, description="按健康标签筛选: healthy/warning/abnormal/danger"),
    lifecycle: str | None = Query(None, description="按生命周期筛选: new/growth/mature/decline"),
    limit: int = Query(100, ge=1, le=100, description="返回数量上限"),
) -> ScoreListResponse:
    """查询所有 ASIN 评分，支持按健康标签和生命周期筛选。"""
    if health_label is not None and health_label not in VALID_LABELS:
        raise HTTPException(
            status_code=400,
            detail=f"无效健康标签 '{health_label}'，可选: {', '.join(sorted(VALID_LABELS))}",
        )

    valid_lifecycles = {"new", "growth", "mature", "decline"}
    if lifecycle is not None and lifecycle not in valid_lifecycles:
        raise HTTPException(
            status_code=400,
            detail=f"无效生命周期 '{lifecycle}'，可选: {', '.join(sorted(valid_lifecycles))}",
        )

    all_scores, _ = _load_scores()
    filtered = all_scores

    if health_label is not None:
        filtered = [s for s in filtered if s["health_label"] == health_label]
    if lifecycle is not None:
        filtered = [s for s in filtered if s["lifecycle"] == lifecycle]

    # 按综合分排序
    filtered.sort(key=lambda x: x["trend_adjusted_score"])
    filtered = filtered[:limit]

    return ScoreListResponse(total=len(filtered), scores=filtered)


# ── 静态文件服务（前端 SPA）───────────────────────────────────────────────
# Docker 构建时前端 build 产物放在 /app/static/
# 本地开发时 frontend/dist/ 可能不存在，跳过即可
_static_dir = Path(__file__).resolve().parents[2] / "static"
if _static_dir.is_dir():
    from fastapi.responses import FileResponse

    # SPA fallback: 非 API 路径都返回 index.html
    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_spa(full_path: str):
        file_path = _static_dir / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(_static_dir / "index.html")
