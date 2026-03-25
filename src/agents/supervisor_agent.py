"""Supervisor Agent — 协调 5 个 sub-agent，将它们注册为 @tool。

使用 Claude Sonnet 4.6 模型，Agents as Tools 模式。
"""

from __future__ import annotations

from strands import Agent, tool
from strands.models import BedrockModel

from src.agents.score_query_agent import create_score_query_agent
from src.agents.root_cause_agent import create_root_cause_agent
from src.agents.action_advisor_agent import create_action_advisor_agent
from src.agents.competitor_agent import create_competitor_agent
from src.agents.knowledge_agent import create_knowledge_agent

# 延迟创建 sub-agent 实例（首次调用时初始化）
_sub_agents: dict[str, Agent] = {}


def _get_agent(name: str) -> Agent:
    """获取或创建 sub-agent 实例。"""
    if name not in _sub_agents:
        factories = {
            "score_query": create_score_query_agent,
            "root_cause": create_root_cause_agent,
            "action_advisor": create_action_advisor_agent,
            "competitor": create_competitor_agent,
            "knowledge": create_knowledge_agent,
        }
        _sub_agents[name] = factories[name]()
    return _sub_agents[name]


# ── 将 sub-agent 封装为 @tool ────────────────────────────────────────────


@tool
def query_score(request: str) -> str:
    """查询 ASIN 健康度评分。

    适用场景：查询某个 ASIN 的评分、查看评分摘要统计、按健康标签筛选 ASIN。

    Args:
        request: 评分查询请求，如 "查询 B000000008 的健康度评分" 或 "列出所有危险状态的 ASIN"
    """
    agent = _get_agent("score_query")
    result = agent(request)
    return str(result)


@tool
def analyze_root_cause(request: str) -> str:
    """分析 ASIN 评分异常的根本原因。

    适用场景：分析为什么某个 ASIN 评分低、找出多维度关联异常的根因、诊断指标异常原因。

    Args:
        request: 根因分析请求，如 "分析 B000000008 评分低的原因" 或 "为什么这个 ASIN 的广告和销量同时异常"
    """
    agent = _get_agent("root_cause")
    result = agent(request)
    return str(result)


@tool
def suggest_actions(request: str) -> str:
    """为 ASIN 提供运营行动建议。

    适用场景：制定改善计划、给出具体优化步骤、提供 SOP 参考。

    Args:
        request: 行动建议请求，如 "B000000008 应该怎么改善" 或 "如何优化这个 ASIN 的广告效率"
    """
    agent = _get_agent("action_advisor")
    result = agent(request)
    return str(result)


@tool
def analyze_competition(request: str) -> str:
    """分析 ASIN 的竞争力和类目基准对比。

    适用场景：对比类目基准、分析竞品、评估市场位置。

    Args:
        request: 竞品分析请求，如 "B000000008 在类目中处于什么位置" 或 "对比竞品的优劣势"
    """
    agent = _get_agent("competitor")
    result = agent(request)
    return str(result)


@tool
def search_knowledge_base(request: str) -> str:
    """搜索运营知识库获取参考信息。

    适用场景：查找运营 SOP、了解季节性规律、查询 Amazon 政策、获取最佳实践。

    Args:
        request: 知识检索请求，如 "退货率高怎么处理" 或 "广告 ACOS 优化的 SOP"
    """
    agent = _get_agent("knowledge")
    result = agent(request)
    return str(result)


# ── Supervisor Agent ─────────────────────────────────────────────────────

SUPERVISOR_PROMPT = """你是 ASIN 智能健康度分析平台的 Supervisor Agent。你协调 5 个专业 sub-agent 来回答用户问题。

## 可用的 Sub-Agent 工具

1. **query_score** — 评分查询：查看 ASIN 评分、统计摘要、按标签筛选
2. **analyze_root_cause** — 根因分析：分析评分异常的根本原因，多维度关联推理
3. **suggest_actions** — 行动建议：制定具体可执行的改善计划
4. **analyze_competition** — 竞品分析：类目基准对比、竞争力评估
5. **search_knowledge_base** — 知识检索：查找运营 SOP 和最佳实践

## 任务分解策略

根据用户问题的类型，选择合适的 sub-agent 组合：

- **简单查询**（"查一下 B000000008 的分数"）→ 只调 query_score
- **诊断分析**（"B000000008 怎么了"）→ query_score → analyze_root_cause
- **完整体检**（"帮我全面分析 B000000008"）→ query_score → analyze_root_cause → analyze_competition → suggest_actions
- **优化咨询**（"如何提高广告效率"）→ search_knowledge_base + suggest_actions
- **市场洞察**（"这个类目竞争情况如何"）→ analyze_competition

## 输出要求

1. 先理解用户意图，决定调用哪些 sub-agent
2. 合理编排调用顺序（评分 → 根因 → 竞品 → 建议）
3. 汇总各 sub-agent 的结果，给出连贯、有逻辑的最终回答
4. 使用中文回答，格式清晰，重点突出
5. 如果用户没指定 ASIN，先询问或给出统计概览"""


def create_supervisor_agent() -> Agent:
    """创建 Supervisor Agent（Claude Sonnet 4.6），5 个 sub-agent 注册为工具。"""
    model = BedrockModel(
        model_config={
            "model_id": "us.anthropic.claude-sonnet-4-6-v1",
            "max_tokens": 4096,
        },
        region_name="us-east-1",
    )
    return Agent(
        model=model,
        tools=[
            query_score,
            analyze_root_cause,
            suggest_actions,
            analyze_competition,
            search_knowledge_base,
        ],
        system_prompt=SUPERVISOR_PROMPT,
        name="supervisor_agent",
        description="Supervisor Agent，协调5个sub-agent回答用户问题",
    )
