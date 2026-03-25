"""Agent 创建和基本功能测试。

注意：这些测试验证 Agent 对象的创建和配置，不实际调用 LLM。
"""

from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock

from src.agents.score_query_agent import create_score_query_agent
from src.agents.root_cause_agent import create_root_cause_agent
from src.agents.action_advisor_agent import create_action_advisor_agent
from src.agents.competitor_agent import create_competitor_agent
from src.agents.knowledge_agent import create_knowledge_agent
from src.agents.supervisor_agent import create_supervisor_agent


class TestAgentCreation:
    """测试各 Agent 可以正确创建。"""

    @patch("src.agents.score_query_agent.BedrockModel")
    def test_create_score_query_agent(self, mock_model_cls: MagicMock) -> None:
        agent = create_score_query_agent()
        assert agent.name == "score_query_agent"
        assert len(agent.tool_names) == 3
        assert "get_asin_score" in agent.tool_names
        assert "get_score_summary" in agent.tool_names
        assert "list_asins_by_health" in agent.tool_names
        # 验证使用 Nova Pro
        mock_model_cls.assert_called_once()
        call_kwargs = mock_model_cls.call_args
        assert "us.amazon.nova-pro-v1:0" in str(call_kwargs)

    @patch("src.agents.root_cause_agent.BedrockModel")
    def test_create_root_cause_agent(self, mock_model_cls: MagicMock) -> None:
        agent = create_root_cause_agent()
        assert agent.name == "root_cause_agent"
        assert "get_asin_score" in agent.tool_names
        assert "get_asin_metrics" in agent.tool_names
        assert "get_metrics_trend" in agent.tool_names
        assert "search_knowledge" in agent.tool_names
        # 验证使用 Sonnet 4.6
        call_kwargs = mock_model_cls.call_args
        assert "claude-sonnet-4-6" in str(call_kwargs)

    @patch("src.agents.action_advisor_agent.BedrockModel")
    def test_create_action_advisor_agent(self, mock_model_cls: MagicMock) -> None:
        agent = create_action_advisor_agent()
        assert agent.name == "action_advisor_agent"
        assert "get_asin_score" in agent.tool_names
        assert "search_knowledge" in agent.tool_names

    @patch("src.agents.competitor_agent.BedrockModel")
    def test_create_competitor_agent(self, mock_model_cls: MagicMock) -> None:
        agent = create_competitor_agent()
        assert agent.name == "competitor_agent"
        assert "get_category_benchmark" in agent.tool_names
        assert "get_competitor_list" in agent.tool_names

    @patch("src.agents.knowledge_agent.BedrockModel")
    def test_create_knowledge_agent(self, mock_model_cls: MagicMock) -> None:
        agent = create_knowledge_agent()
        assert agent.name == "knowledge_agent"
        assert "search_knowledge" in agent.tool_names

    @patch("src.agents.supervisor_agent.BedrockModel")
    def test_create_supervisor_agent(self, mock_model_cls: MagicMock) -> None:
        agent = create_supervisor_agent()
        assert agent.name == "supervisor_agent"
        # Supervisor 应该有 5 个 sub-agent 工具
        assert len(agent.tool_names) == 5
        assert "query_score" in agent.tool_names
        assert "analyze_root_cause" in agent.tool_names
        assert "suggest_actions" in agent.tool_names
        assert "analyze_competition" in agent.tool_names
        assert "search_knowledge_base" in agent.tool_names
