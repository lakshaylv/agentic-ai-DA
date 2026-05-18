import time
from abc import ABC, abstractmethod

import pandas as pd

from backend.models.schemas import ToolMetadata, ToolResponse


class BaseTool(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def _execute(self, df: pd.DataFrame, **params) -> dict:
        ...

    def execute(self, df: pd.DataFrame, **params) -> ToolResponse:
        start = time.perf_counter()
        try:
            data = self._execute(df, **params)
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            metadata = ToolMetadata(
                tool_name=self.name,
                execution_time_ms=elapsed_ms,
                rows_affected=len(df) if isinstance(df, pd.DataFrame) else None,
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
