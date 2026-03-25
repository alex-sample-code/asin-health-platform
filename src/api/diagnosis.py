"""ASIN 智能诊断模块 — SSE 流式推送 + Agent 并行调用。

流程：
1. 从本地 JSON 计算问题概览 → 立即推送 problem_overview
2. 并行启动 root_cause Agent 和 competitor Agent
   - 各自完成后推送 root_cause / benchmark
3. 等根因结果出来后，调 action_advisor Agent → 推送 action_plan
4. 推送 done 事件
"""

from __future__ import annotations

import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Any, Generator

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

        # 跳过 Agent 过渡语（非行动建议内容）
        first_line_raw = section.strip().split("\n")[0].strip()
        skip_patterns = [
            r"数据已.*获取", r"以下是.*分析", r"以下是.*计划",
            r"综合.*分析", r"根据.*分析", r"基于.*数据",
            r"^---$", r"^##\s", r"总结",
        ]
        if any(re.search(p, first_line_raw) for p in skip_patterns):
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

        # 提取标题（第一行），清理 markdown 残留
        first_line = section.strip().split("\n")[0]
        title = first_line
        # 去掉 markdown 标题符号
        title = re.sub(r"^#{1,3}\s*", "", title)
        # 去掉优先级前缀（各种格式）
        title = re.sub(r"^(?:\*\*)?P[0-3]\s*(?:\*\*)?\s*", "", title)
        title = re.sub(r"^(?:紧急|高优|中优|低优)\s*", "", title)
        # 去掉 emoji
        title = re.sub(r"[\U0001f300-\U0001f9ff\U00002600-\U000027bf]", "", title)
        # 去掉 markdown bold
        title = re.sub(r"\*\*", "", title)
        # 去掉前导符号
        title = re.sub(r"^[\d\.\、:：\-—\s]+", "", title).strip()
        if not title or len(title) < 3:
            title = first_line.strip()[:100]

        # 提取步骤（去掉与标题重复的行和预期效果行）
        steps = []
        for line in section.split("\n")[1:]:  # 跳过第一行（标题）
            line = line.strip()
            # 跳过预期效果行（单独处理）
            if re.search(r"^预期效果[:：]", line):
                continue
            if line.startswith(("-", "•", "*", "·")) and len(line) > 3:
                step = line.lstrip("-•*· ")
                # 去掉 markdown bold
                step = re.sub(r"\*\*", "", step)
                steps.append(step)
            elif re.match(r"^\d+[\.\)]\s", line):
                step = re.sub(r"^\d+[\.\)]\s*", "", line)
                step = re.sub(r"\*\*", "", step)
                steps.append(step)

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
            if re.search(r"预期[效果]|expect", line, re.IGNORECASE):
                expected = line.strip().lstrip("-•*· ")
                # 清理前缀
                expected = re.sub(r"^预期效果[:：]\s*", "", expected)
                expected = re.sub(r"\*\*", "", expected)
                break
        if not expected:
            expected = "执行后预计改善相关维度评分"

        if title and len(title) >= 3:
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
    """执行完整诊断流程，root_cause 和 competitor 并行调用。"""

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

    # 3. 并行调 root_cause Agent 和 competitor Agent
    def _call_root_cause() -> str:
        try:
            agent = _get_root_cause_agent()
            prompt = (
                f"分析 ASIN {asin_id} 的健康度异常。"
                f"综合评分 {final_score:.1f}（{health_label}），"
                f"异常维度：{problem_summary}。"
                f"请给出根因假设和置信度（高/中/低），每个假设附上支撑证据。"
            )
            return str(agent(prompt))
        except Exception as e:
            logger.exception("Root cause agent 调用失败")
            return f"根因分析调用失败: {e}"

    def _call_competitor() -> str:
        try:
            agent = _get_competitor_agent()
            prompt = (
                f"分析 ASIN {asin_id} 在类目中的竞争力位置，对比行业基准。"
                f"重点关注弱于基准的维度。"
            )
            return str(agent(prompt))
        except Exception as e:
            logger.exception("Competitor agent 调用失败")
            return f"竞品分析调用失败: {e}"

    with ThreadPoolExecutor(max_workers=2) as executor:
        root_future = executor.submit(_call_root_cause)
        bench_future = executor.submit(_call_competitor)
        root_cause_text = root_future.result()
        benchmark_text = bench_future.result()

    root_causes = _parse_root_causes(root_cause_text)
    benchmark = _parse_benchmark(benchmark_text)

    # 4. 串行调 action_advisor Agent（依赖根因结果）
    try:
        root_cause_summary = "; ".join(rc.hypothesis for rc in root_causes[:3])
        agent = _get_action_advisor_agent()
        prompt = (
            f"为 ASIN {asin_id} 制定行动计划。"
            f"当前问题：综合评分 {final_score:.1f}，异常维度 {problem_summary}。"
            f"根因分析：{root_cause_summary}。"
            f"请按 P0-P3 优先级给出建议，每条包含具体步骤、预期效果和时间线。"
        )
        action_text = str(agent(prompt))
    except Exception as e:
        logger.exception("Action advisor agent 调用失败")
        action_text = f"行动建议调用失败: {e}"

    action_plan = _parse_action_items(action_text)

    # 5. 汇总
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


# ── SSE 流式诊断 ─────────────────────────────────────────────────────────


def _sse_event(event: str, data: dict[str, Any]) -> str:
    """格式化一个 SSE 事件。"""
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


def run_diagnosis_stream(asin_id: str) -> Generator[str, None, None]:
    """流式诊断生成器，yield SSE 事件字符串。"""

    # 1. 加载评分数据
    _, by_asin = _load_scores()
    score_data = by_asin.get(asin_id)
    if score_data is None:
        yield _sse_event("error", {"module": "score_data", "message": f"未找到 ASIN {asin_id} 的评分数据"})
        return

    health_label = score_data["health_label"]
    final_score = score_data["final_score"]

    # 2. 识别异常维度 → 立即推送 problem_overview
    problems = _identify_problems(score_data)
    if not problems:
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
    summary = (
        f"ASIN {asin_id} 综合健康度 {final_score:.1f} 分（{health_label}），"
        f"主要问题维度：{problem_summary}。"
    )

    yield _sse_event("problem_overview", {
        "asin": asin_id,
        "health_label": health_label,
        "final_score": round(final_score, 1),
        "summary": summary,
        "problem_dimensions": [p.model_dump() for p in problems],
    })

    # 3. 并行调 root_cause Agent 和 competitor Agent
    root_cause_text = ""
    benchmark_text = ""

    def _call_root_cause() -> str:
        try:
            agent = _get_root_cause_agent()
            prompt = (
                f"分析 ASIN {asin_id} 的健康度异常。"
                f"综合评分 {final_score:.1f}（{health_label}），"
                f"异常维度：{problem_summary}。"
                f"请给出根因假设和置信度（高/中/低），每个假设附上支撑证据。"
            )
            return str(agent(prompt))
        except Exception as e:
            logger.exception("Root cause agent 调用失败")
            return ""

    def _call_competitor() -> str:
        try:
            agent = _get_competitor_agent()
            prompt = (
                f"分析 ASIN {asin_id} 在类目中的竞争力位置，对比行业基准。"
                f"重点关注弱于基准的维度。"
            )
            return str(agent(prompt))
        except Exception as e:
            logger.exception("Competitor agent 调用失败")
            return ""

    with ThreadPoolExecutor(max_workers=2) as executor:
        root_future: Future[str] = executor.submit(_call_root_cause)
        bench_future: Future[str] = executor.submit(_call_competitor)

        # 等两个都完成，谁先完成先推送谁
        root_done = False
        bench_done = False

        while not (root_done and bench_done):
            if not root_done and root_future.done():
                root_cause_text = root_future.result()
                root_done = True
                if root_cause_text:
                    root_causes = _parse_root_causes(root_cause_text)
                    yield _sse_event("root_cause", {
                        "root_causes": [rc.model_dump() for rc in root_causes],
                    })
                else:
                    yield _sse_event("error", {"module": "root_cause", "message": "根因分析调用失败"})

            if not bench_done and bench_future.done():
                benchmark_text = bench_future.result()
                bench_done = True
                if benchmark_text:
                    benchmark = _parse_benchmark(benchmark_text)
                    yield _sse_event("benchmark", {"benchmark": benchmark.model_dump()})
                else:
                    yield _sse_event("error", {"module": "benchmark", "message": "竞品分析调用失败"})

            if not (root_done and bench_done):
                # 短暂等待避免忙循环
                import time
                time.sleep(0.1)

    # 4. 串行调 action_advisor Agent（依赖根因结果）
    try:
        if root_cause_text:
            root_causes_parsed = _parse_root_causes(root_cause_text)
        else:
            root_causes_parsed = []
        root_cause_summary = "; ".join(rc.hypothesis for rc in root_causes_parsed[:3])

        agent = _get_action_advisor_agent()
        prompt = (
            f"为 ASIN {asin_id} 制定行动计划。"
            f"当前问题：综合评分 {final_score:.1f}，异常维度 {problem_summary}。"
            f"根因分析：{root_cause_summary}。"
            f"请按 P0-P3 优先级给出建议，每条包含具体步骤、预期效果和时间线。"
        )
        action_text = str(agent(prompt))
        action_plan = _parse_action_items(action_text)
        yield _sse_event("action_plan", {
            "action_plan": [item.model_dump() for item in action_plan],
        })
    except Exception as e:
        logger.exception("Action advisor agent 调用失败")
        yield _sse_event("error", {"module": "action_plan", "message": "行动建议调用失败"})

    # 5. 完成
    yield _sse_event("done", {"status": "complete"})
