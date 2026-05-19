import pandas as pd

from backend.models.schemas import ToolMetadata, ToolResponse, ToolSignature
from backend.tools.base import BaseTool


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def list_signatures(self) -> list[ToolSignature]:
        sigs = []
        for tool in self._tools.values():
            sigs.append(ToolSignature(
                name=tool.name,
                description=tool.__class__.__doc__ or tool.name,
                params_schema=tool.param_schema,
            ))
        return sigs

    def execute(self, name: str, df: pd.DataFrame, **params) -> ToolResponse:
        tool = self.get(name)
        if tool is None:
            return ToolResponse(
                success=False,
                data=None,
                metadata=ToolMetadata(tool_name=name, execution_time_ms=0, error_type="tool_not_found"),
                error=f"Tool '{name}' not found. Available: {sorted(self._tools.keys())}",
            )
        return tool.execute(df, **params)
