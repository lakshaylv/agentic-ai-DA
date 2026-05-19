from unittest.mock import patch

from backend.agent.orchestrator import run_analysis
from backend.models.schemas import LLMDecision, AnalysisResult
from backend.tools.registry import ToolRegistry
from backend.tools.inspection import SchemaInspector


class MockLLMConfig:
    provider = "mock"
    api_key = "mock-key"
    model = "mock-model"


def test_orchestrator_completes_directly(sample_df):
    registry = ToolRegistry()
    registry.register(SchemaInspector())

    with patch("backend.agent.orchestrator.llm_analyze") as mock_llm:
        mock_llm.return_value = LLMDecision(
            analysis="Done",
            next_tool=None,
            complete=True,
            insights=["All good"],
        )
        result = run_analysis(sample_df, "test query", registry=registry, llm_config=MockLLMConfig())
    assert result.complete
    assert result.iterations == 1
    assert result.insights == ["All good"]
    assert result.error is None


def test_orchestrator_tool_then_complete(sample_df):
    registry = ToolRegistry()
    registry.register(SchemaInspector())

    call_count = 0

    def mock_analyze(messages, tools, config):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return LLMDecision(
                analysis="Check schema first",
                next_tool="schema_inspector",
                params={},
                complete=False,
            )
        return LLMDecision(
            analysis="Got schema, done",
            next_tool=None,
            complete=True,
            insights=["Schema analyzed"],
        )

    with patch("backend.agent.orchestrator.llm_analyze", side_effect=mock_analyze):
        result = run_analysis(sample_df, "analyze schema", registry=registry, llm_config=MockLLMConfig())

    assert result.complete
    assert result.iterations == 2
    assert len(result.tool_results) == 1
    assert result.tool_results[0]["tool"] == "schema_inspector"


def test_orchestrator_max_iterations(sample_df):
    registry = ToolRegistry()
    registry.register(SchemaInspector())

    with patch("backend.agent.orchestrator.llm_analyze") as mock_llm:
        mock_llm.return_value = LLMDecision(
            analysis="Still working",
            next_tool="schema_inspector",
            params={},
            complete=False,
        )
        result = run_analysis(
            sample_df, "loop forever", registry=registry,
            llm_config=MockLLMConfig(), max_iterations=3
        )

    assert not result.complete
    assert result.iterations == 3
    assert "max iterations" in (result.error or "").lower()
    assert len(result.tool_results) == 3


def test_orchestrator_returns_error_tool_not_found(sample_df):
    registry = ToolRegistry()

    with patch("backend.agent.orchestrator.llm_analyze") as mock_llm:
        mock_llm.return_value = LLMDecision(
            analysis="Use nonexistent tool",
            next_tool="does_not_exist",
            params={},
            complete=False,
        )
        result = run_analysis(sample_df, "bad tool", registry=registry, llm_config=MockLLMConfig(), max_iterations=2)

    assert not result.complete
    assert len(result.tool_results) == 2
