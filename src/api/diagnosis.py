"""ASIN 智能诊断模块 — 串行编排 3 个 Agent 生成结构化诊断报告。

流程：
1. 从本地 JSON 取评分数据
2. 识别异常维度 (score < 60)
3. 调 root_cause Agent 分析根因
4. 调 action_advisor Agent 给行动建议
5. 调 competitor Agent 对标竞品
6. 汇总成 DiagnosisResponse
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from pydantic import BaseModel

from src.tools.score_tools import _load_scores

logger = logging.getLogger(__name__)

# ── 维度名称映射 ───────────────────────────────────────────────────────────

DIMENSION_CN = {
    "sales": "销量",
    "inventory": "库存",
    "advertising": "广告",
    "after_sales": "售后",
    "profitability": "盈利性",
    "listing": "Listing质量",
}

# ── 响应模型 ───────────────────────────────────────────────────────────────


class ProblemDimension(BaseModel):
    dimension: str
    dimension_cn: str
    score: float
    severity: str  # critical(<20) / warning(<40) / attention(<60)
    description: str


class RootCause(BaseModel):
    hypothesis: str
    confidence: str  # high / medium / low
    evidence: list[str]


class ActionItem(BaseModel):
    priority: str  # P0 / P1 / P2 / P3
    title: str
    steps: list[str]
    expected_effect: str
    timeline: str  # "24h" / "本周" / "两周内" / "本月"


class BenchmarkComparison(BaseModel):
    category_position: str
    weak_vs_benchmark: list[str]
    competitor_insights: str


class DiagnosisResponse(BaseModel):
    asin: str
    health_label: str
    final_score: float
    summary: str
    problem_dimensions: list[ProblemDimension]
    root_causes: list[RootCause]
    action_plan: list[ActionItem]
    benchmark: BenchmarkComparison


# ── Agent 单例缓存 ─────────────────────────────────────────────────────────

_root_cause_agent = None
_action_advisor_agent = None
_competitor_agent = None


def _get_root_cause_agent():
    global _root_cause_agent
    if _root_cause_agent is None:
        from src.agents.root_cause_agent import create_root_cause_agent
        _root_cause_agent = create_root_cause_agent()
    return _root_cause_agent


def _get_action_advisor_agent():
    global _action_advisor_agent
    if _action_advisor_agent is None:
        from src.agents.action_advisor_agent import create_action_advisor_agent
        _action_advisor_agent = create_action_advisor_agent()
    return _action_advisor_agent


def _get_competitor_agent():
    global _competitor_agent
    if _competitor_agent is None:
        from src.agents.competitor_agent import create_competitor_agent
        _competitor_agent = create_competitor_agent()
    return _competitor_agent


# ── 辅助函数 ───────────────────────────────────────────────────────────────


def _identify_problems(score_data: dict[str, Any]) -> list[ProblemDimension]:
    """识别 score < 60 的异常维度。"""
    problems = []
    dims = score_data.get("dimension_scores", {})
    for dim_key, dim_cn in DIMENSION_CN.items():
        val = dims.get(dim_key, 0)
        if val >= 60:
            continue
        if val < 20:
            severity = "critical"
            desc = f"{dim_cn}评分仅 {val:.1f}，处于极度危险水平"
        elif val < 40:
            severity = "warning"
            desc = f"{dim_cn}评分 {val:.1f}，明显低于健康阈值"
        else:
            severity = "attention"
            desc = f"{dim_cn}评分 {val:.1f}，低于及格线，需要关注"
        problems.append(ProblemDimension(
            dimension=dim_key,
            dimension_cn=dim_cn,
            score=round(val, 1),
            severity=severity,
            description=desc,
        ))
    # 按分数升序
    problems.sort(key=lambda p: p.score)
    return problems


def _parse_root_causes(text: str) -> list[RootCause]:
    """从 Agent 返回文本中解析根因列表。降级时把整段放 hypothesis。"""
    causes: list[RootCause] = []

    # 尝试按编号分段
    sections = re.split(r"\n(?=\d+[\.\、])", text.strip())
    for section in sections:
        if not section.strip():
            continue
        # 提取置信度
        confidence = "medium"
        if re.search(r"高|high", section, re.IGNORECASE):
            confidence = "high"
        elif re.search(r"低|low", section, re.IGNORECASE):
            confidence = "low"

        # 提取 bullet 证据
        evidence = []
        for line in section.split("\n"):
            line = line.strip()
            if line.startswith(("-", "•", "*", "·")) and len(line) > 3:
                evidence.append(line.lstrip("-•*· "))

        # 提取假设（第一行去掉序号）
        first_line = section.strip().split("\n")[0]
        hypothesis = re.sub(r"^\d+[\.\、]\s*", "", first_line).strip()
        if not hypothesis:
            hypothesis = section.strip()[:200]

        if hypothesis:
            causes.append(RootCause(
                hypothesis=hypothesis,
                confidence=confidence,
                evidence=evidence if evidence else [section.strip()[:200]],
            ))

    # 降级：如果解析不出任何内容
    if not causes and text.strip():
        causes.append(RootCause(
            hypothesis=text.strip()[:300],
            confidence="medium",
            evidence=["AI 原始分析结果，未能结构化解析"],
        ))
    return causes


def _parse_action_items(text: str) -> list[ActionItem]:
    """从 Agent 返回文本中解析行动建议列表。"""
    items: list[ActionItem] = []

    # 按 P0-P3 标记或编号分段
    sections = re.split(r"\n(?=(?:#{1,3}\s*)?(?:\*\*)?(?:P[0-3]|紧急|高优|中优|低优))", text.strip())
    if len(sections) <= 1:
        sections = re.split(r"\n(?=\d+[\.\、])", text.strip())

    for section in sections:
        if not section.strip():
            continue

        # 提取优先级
        priority = "P2"
        if re.search(r"P0|紧急", section):
            priority = "P0"
        elif re.search(r"P1|高优", section):
            priority = "P1"
        elif re.search(r"P3|低优", section):
            priority = "P3"
        elif re.search(r"P2|中优", section):
            priority = "P2"

        # 提取标题（第一行）
        first_line = section.strip().split("\n")[0]
        title = re.sub(r"^[\d\.\、#*\s]*(?:P[0-3]|紧急|高优|中优|低优)[^:：]*[:：]\s*", "", first_line).strip()
        title = re.sub(r"^\d+[\.\、]\s*", "", title).strip()
        title = re.sub(r"\*\*", "", title).strip()
        if not title:
            title = first_line.strip()[:100]

        # 提取步骤
        steps = []
        for line in section.split("\n"):
            line = line.strip()
            if line.startswith(("-", "•", "*", "·")) and len(line) > 3:
                steps.append(line.lstrip("-•*· "))
            elif re.match(r"^\d+[\.\)]\s", line):
                steps.append(re.sub(r"^\d+[\.\)]\s*", "", line))

        # 提取时间线
        timeline = "本周"
        if re.search(r"24[小h时]|立即|马上", section):
            timeline = "24h"
        elif re.search(r"两周|2周|14天", section):
            timeline = "两周内"
        elif re.search(r"本月|一个月|30天", section):
            timeline = "本月"

        # 提取预期效果
        expected = ""
        for line in section.split("\n"):
            if re.search(r"预期|效果|expect|提升|改善|降低", line, re.IGNORECASE):
                expected = line.strip().lstrip("-•*· ")
                break
        if not expected:
            expected = f"执行后预计改善相关维度评分"

        if title:
            items.append(ActionItem(
                priority=priority,
                title=title,
                steps=steps if steps else ["参考 AI 分析结果执行"],
                expected_effect=expected,
                timeline=timeline,
            ))

    # 降级
    if not items and text.strip():
        items.append(ActionItem(
            priority="P1",
            title="AI 行动建议",
            steps=[text.strip()[:500]],
            expected_effect="参考 AI 分析结果",
            timeline="本周",
        ))

    # 按优先级排序
    priority_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    items.sort(key=lambda x: priority_order.get(x.priority, 9))
    return items


def _parse_benchmark(text: str) -> BenchmarkComparison:
    """从 Agent 返回文本中解析竞品对标信息。"""
    # 提取类目位置
    position = "中等"
    if re.search(r"领先|优秀|top|头部", text, re.IGNORECASE):
        position = "领先"
    elif re.search(r"落后|较差|底部|末位", text, re.IGNORECASE):
        position = "落后"
    elif re.search(r"中等|中游|一般", text):
        position = "中等"

    # 提取弱于基准的维度
    weak_dims = []
    for line in text.split("\n"):
        if re.search(r"低于|弱于|不及|落后|below|under", line, re.IGNORECASE):
            weak_dims.append(line.strip().lstrip("-•*· ")[:100])
    if not weak_dims:
        weak_dims = ["参考 AI 详细分析"]

    return BenchmarkComparison(
        category_position=position,
        weak_vs_benchmark=weak_dims[:5],
        competitor_insights=text.strip()[:500] if text.strip() else "暂无竞品洞察",
    )


# ── 主诊断函数 ─────────────────────────────────────────────────────────────


def run_diagnosis(asin_id: str) -> DiagnosisResponse:
    """执行完整诊断流程，串行调用 3 个 Agent。"""

    # 1. 加载评分数据
    _, by_asin = _load_scores()
    score_data = by_asin.get(asin_id)
    if score_data is None:
        raise ValueError(f"未找到 ASIN {asin_id} 的评分数据")

    health_label = score_data["health_label"]
    final_score = score_data["final_score"]

    # 2. 识别异常维度
    problems = _identify_problems(score_data)
    if not problems:
        # 没有低于 60 的维度，找最低的两个作为关注点
        dims = score_data.get("dimension_scores", {})
        sorted_dims = sorted(dims.items(), key=lambda x: x[1])
        for dim_key, val in sorted_dims[:2]:
            problems.append(ProblemDimension(
                dimension=dim_key,
                dimension_cn=DIMENSION_CN.get(dim_key, dim_key),
                score=round(val, 1),
                severity="attention",
                description=f"{DIMENSION_CN.get(dim_key, dim_key)}评分 {val:.1f}，相对最弱",
            ))

    problem_summary = "、".join(f"{p.dimension_cn}({p.score}分)" for p in problems)

    # 3. 调 root_cause Agent
    root_cause_text = ""
    try:
        agent = _get_root_cause_agent()
        prompt = (
            f"分析 ASIN {asin_id} 的健康度异常。"
            f"综合评分 {final_score:.1f}（{health_label}），"
            f"异常维度：{problem_summary}。"
            f"请给出根因假设和置信度（高/中/低），每个假设附上支撑证据。"
        )
        result = agent(prompt)
        root_cause_text = str(result)
    except Exception as e:
        logger.exception("Root cause agent 调用失败")
        root_cause_text = f"根因分析调用失败: {e}"

    root_causes = _parse_root_causes(root_cause_text)

    # 4. 调 action_advisor Agent
    action_text = ""
    try:
        agent = _get_action_advisor_agent()
        root_cause_summary = "; ".join(rc.hypothesis for rc in root_causes[:3])
        prompt = (
            f"为 ASIN {asin_id} 制定行动计划。"
            f"当前问题：综合评分 {final_score:.1f}，异常维度 {problem_summary}。"
            f"根因分析：{root_cause_summary}。"
            f"请按 P0-P3 优先级给出建议，每条包含具体步骤、预期效果和时间线。"
        )
        result = agent(prompt)
        action_text = str(result)
    except Exception as e:
        logger.exception("Action advisor agent 调用失败")
        action_text = f"行动建议调用失败: {e}"

    action_plan = _parse_action_items(action_text)

    # 5. 调 competitor Agent
    benchmark_text = ""
    try:
        agent = _get_competitor_agent()
        prompt = (
            f"分析 ASIN {asin_id} 在类目中的竞争力位置，对比行业基准。"
            f"重点关注弱于基准的维度。"
        )
        result = agent(prompt)
        benchmark_text = str(result)
    except Exception as e:
        logger.exception("Competitor agent 调用失败")
        benchmark_text = f"竞品分析调用失败: {e}"

    benchmark = _parse_benchmark(benchmark_text)

    # 6. 汇总
    summary = (
        f"ASIN {asin_id} 综合健康度 {final_score:.1f} 分（{health_label}），"
        f"主要问题维度：{problem_summary}。"
    )

    return DiagnosisResponse(
        asin=asin_id,
        health_label=health_label,
        final_score=round(final_score, 1),
        summary=summary,
        problem_dimensions=problems,
        root_causes=root_causes,
        action_plan=action_plan,
        benchmark=benchmark,
    )
