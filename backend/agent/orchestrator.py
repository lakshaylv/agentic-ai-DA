import json

import pandas as pd

from backend.models.schemas import AnalysisResult
from backend.services.llm_service import LLMConfig, analyze as llm_analyze
from backend.tools.registry import ToolRegistry


def run_analysis(
    df: pd.DataFrame,
    query: str,
    session_id: str = "",
    registry: ToolRegistry | None = None,
    llm_config: LLMConfig | None = None,
    max_iterations: int = 10,
) -> AnalysisResult:
    if registry is None:
        raise ValueError("ToolRegistry is required")
    if llm_config is None:
        llm_config = LLMConfig()

    conversation = [{"role": "user", "content": query}]
    tool_results = []
    error = None

    for i in range(max_iterations):
        decision = llm_analyze(
            messages=conversation,
            tools=registry.list_signatures(),
            config=llm_config,
        )

        if error is None and not decision.complete and not decision.next_tool:
            error = "LLM returned no next_tool but did not mark complete"
            break

        if decision.complete:
            return AnalysisResult(
                session_id=session_id,
                query=query,
                complete=True,
                iterations=i + 1,
                insights=decision.insights,
                chart_type=decision.chart_type,
                chart_spec=decision.chart_spec,
                tool_results=tool_results,
                error=None,
            )

        response = registry.execute(decision.next_tool, df, **decision.params)
        tool_results.append({
            "tool": decision.next_tool,
            "params": decision.params,
            "analysis": decision.analysis,
            "response": response.model_dump(),
        })

        conversation.append({"role": "assistant", "content": decision.model_dump_json()})
        conversation.append({
            "role": "user",
            "content": f"Tool '{decision.next_tool}' returned: {response.model_dump_json()}",
        })

        if error is None and not response.success:
            error = f"Tool '{decision.next_tool}' failed: {response.error}"
            break

    return AnalysisResult(
        session_id=session_id,
        query=query,
        complete=False,
        iterations=max_iterations,
        insights=[],
        tool_results=tool_results,
        error=error or f"Exceeded max iterations ({max_iterations})",
    )
