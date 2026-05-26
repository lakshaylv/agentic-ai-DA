import re

import pandas as pd

from backend.models.schemas import AnalysisResult, ToolMetadata, ToolResponse
from backend.services.llm_service import LLMConfig, analyze as llm_analyze
from backend.tools.registry import ToolRegistry


def _clean_insight(text: str) -> str:
    text = " ".join(text.split())
    text = re.sub(r"\)(\w)", r") \1", text)
    text = re.sub(r"(\d), (\d{3})", r"\1,\2", text)
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
    text = text.replace("*", "").replace("_", "")
    return text


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
    working_df = df.copy()

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
                    grouped = last_data.get("grouped") or last_data.get("value_counts") or last_data.get("pivot")
                    if grouped:
                        chart_spec = {**chart_spec, "data": grouped}
            clean_insights = [_clean_insight(ins) for ins in decision.insights]
            return AnalysisResult(
                session_id=session_id,
                query=query,
                complete=True,
                iterations=i + 1,
                insights=clean_insights,
                chart_type=decision.chart_type,
                chart_spec=chart_spec,
                tool_results=tool_results,
                error=None,
            )

        if decision.next_tool == "reset":
            working_df = df.copy()
            response = ToolResponse(
                success=True,
                data={"message": "Reset complete. All filters and derived columns cleared."},
                metadata=ToolMetadata(tool_name="reset", execution_time_ms=0),
            )
        else:
            response = registry.execute(decision.next_tool, working_df, **decision.params)
            if response.success:
                tool = registry.get(decision.next_tool)
                if tool is not None:
                    new_df = tool.mutate(working_df, **decision.params)
                    if new_df is not None:
                        working_df = new_df

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
