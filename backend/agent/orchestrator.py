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

    col_info = f"Columns: {', '.join(df.columns)}. Rows: {df.shape[0]}."
    prompt = f"{col_info}\nQuery: {query}"
    conversation = [{"role": "user", "content": prompt}]
    tool_results = []
    error = None
    consecutive_failures = 0
    max_consecutive_failures = 3

    for i in range(max_iterations):
        decision = llm_analyze(
            messages=conversation,
            tools=registry.list_signatures(),
            config=llm_config,
        )

        if error is None and not decision.complete and not decision.next_tool:
            error = decision.analysis or "LLM returned no next_tool but did not mark complete"
            break

        if decision.complete:
            chart_spec = decision.chart_spec
            if chart_spec and not chart_spec.get("data") and tool_results:
                last_data = tool_results[-1].get("response", {}).get("data", {})
                if isinstance(last_data, dict):
                    grouped = last_data.get("grouped") or last_data.get("value_counts")
                    if grouped:
                        chart_spec = {**chart_spec, "data": grouped}
            return AnalysisResult(
                session_id=session_id,
                query=query,
                complete=True,
                iterations=i + 1,
                insights=decision.insights,
                chart_type=decision.chart_type,
                chart_spec=chart_spec,
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

        assistant_msg = f"Analysis: {decision.analysis}\nCalled tool: {decision.next_tool}"
        conversation.append({"role": "assistant", "content": assistant_msg})

        if not response.success:
            consecutive_failures += 1
            if consecutive_failures >= max_consecutive_failures:
                error = f"Tool '{decision.next_tool}' failed {consecutive_failures} consecutive times: {response.error}"
                break
            conversation.append({
                "role": "user",
                "content": f"Tool '{decision.next_tool}' failed: {response.error}. Try a different approach or tool.",
            })
        else:
            consecutive_failures = 0
            tool_output = response.model_dump_json()
            if len(tool_output) > 800:
                tool_output = tool_output[:800] + "... [truncated]"
            conversation.append({
                "role": "user",
                "content": f"Tool '{decision.next_tool}' returned: {tool_output}",
            })

    return AnalysisResult(
        session_id=session_id,
        query=query,
        complete=False,
        iterations=max_iterations,
        insights=[],
        tool_results=tool_results,
        error=error or f"Exceeded max iterations ({max_iterations})",
    )
