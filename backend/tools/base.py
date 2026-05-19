import math
import time
from abc import ABC, abstractmethod

import pandas as pd

from backend.models.schemas import ToolMetadata, ToolResponse


def _clean_nan(obj):
    if isinstance(obj, float) and math.isnan(obj):
        return None
    if isinstance(obj, dict):
        return {k: _clean_nan(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_clean_nan(v) for v in obj]
    return obj


class BaseTool(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    def param_schema(self) -> dict:
        return {}

    @abstractmethod
    def _execute(self, df: pd.DataFrame, **params) -> dict:
        ...

    def execute(self, df: pd.DataFrame, **params) -> ToolResponse:
        start = time.perf_counter()
        try:
            data = _clean_nan(self._execute(df, **params))
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            metadata = ToolMetadata(
                tool_name=self.name,
                execution_time_ms=elapsed_ms,
                rows_affected=None,
            )
            return ToolResponse(success=True, data=data, metadata=metadata, error=None)
        except Exception as e:
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            metadata = ToolMetadata(
                tool_name=self.name,
                execution_time_ms=elapsed_ms,
                error_type=type(e).__name__,
            )
            return ToolResponse(success=False, data=None, metadata=metadata, error=str(e))
