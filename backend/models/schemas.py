from pydantic import BaseModel
from typing import Any, Optional


class ToolMetadata(BaseModel):
    tool_name: str
    execution_time_ms: int
    rows_affected: Optional[int] = None
    warning: Optional[str] = None
    error_type: Optional[str] = None


class ToolResponse(BaseModel):
    success: bool
    data: Optional[Any] = None
    metadata: ToolMetadata
    error: Optional[str] = None


class ToolSignature(BaseModel):
    name: str
    description: str
    params_schema: dict


class LLMDecision(BaseModel):
    analysis: str
    next_tool: Optional[str] = None
    params: dict = {}
    complete: bool = False
    chart_type: Optional[str] = None
    chart_spec: Optional[dict] = None
    insights: list[str] = []
