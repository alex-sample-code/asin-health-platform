"""知识检索 Agent — 运营知识库检索和问答。

使用 Claude Sonnet 4.6 模型，工具：search_knowledge
"""

from __future__ import annotations

from strands import Agent
from strands.models import BedrockModel

from src.tools.knowledge_tools import search_knowledge

SYSTEM_PROMPT = """你是 Amazon 运营知识库检索专家。

## 规则
- **最多调用 1 次工具**，然后直接总结回答
- **回复控制在 300 字以内**
- 直接给结论和关键 SOP 步骤，不要复述知识库原文"""


def create_knowledge_agent() -> Agent:
    """创建知识检索 Agent（Amazon Nova Pro — 简单检索+总结）。"""
    model = BedrockModel(
        model_id="us.amazon.nova-pro-v1:0",
        max_tokens=1024,
        region_name="us-east-1",
    )
    return Agent(
        model=model,
        tools=[search_knowledge],
        system_prompt=SYSTEM_PROMPT,
        name="knowledge_agent",
        description="知识检索Agent，负责运营知识库检索和问答",
    )
