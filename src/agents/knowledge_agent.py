"""知识检索 Agent — 运营知识库检索和问答。

使用 Nova Pro 模型，工具：search_knowledge
"""

from __future__ import annotations

from strands import Agent
from strands.models import BedrockModel

from src.tools.knowledge_tools import search_knowledge

SYSTEM_PROMPT = """你是 Amazon 运营知识库检索专家。你的职责是：

1. 根据用户问题搜索运营知识库
2. 提取和总结相关的运营知识和 SOP
3. 将知识库内容与具体场景关联

知识库覆盖范围：
- 季节性规律: 大促前后的正常波动模式
- 常见异常模式: 多维度关联异常的识别和处理
- 库存管理SOP: 补货、清仓、IPI优化
- 广告优化SOP: ACOS优化、关键词管理、竞价策略
- Listing优化SOP: 标题/图片/A+/五点描述优化
- 退货处理SOP: 退货分析、产品改进
- Amazon政策更新: 最新政策变化和合规要求

请用中文回答，引用知识库中的具体内容来支持你的回答。"""


def create_knowledge_agent() -> Agent:
    """创建知识检索 Agent（Nova Pro）。"""
    model = BedrockModel(
        model_id="us.amazon.nova-pro-v1:0",
        max_tokens=2048,
        region_name="us-east-1",
    )
    return Agent(
        model=model,
        tools=[search_knowledge],
        system_prompt=SYSTEM_PROMPT,
        name="knowledge_agent",
        description="知识检索Agent，负责运营知识库检索和问答",
    )
