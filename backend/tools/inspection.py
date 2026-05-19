import pandas as pd

from backend.tools.base import BaseTool


class SchemaInspector(BaseTool):
    """Inspect column names, data types, and shape of the dataset. No parameters required."""

    @property
    def name(self) -> str:
        return "schema_inspector"

    def _execute(self, df: pd.DataFrame, **params) -> dict:
        dtypes = {col: str(dtype) for col, dtype in df.dtypes.items()}
        return {
            "columns": df.columns.tolist(),
            "dtypes": dtypes,
            "row_count": df.shape[0],
            "column_count": df.shape[1],
        }


class MissingValueAnalyzer(BaseTool):
    """Analyze missing values across all columns. No parameters required."""

    @property
    def name(self) -> str:
        return "missing_value_analyzer"

    def _execute(self, df: pd.DataFrame, **params) -> dict:
        missing_counts = df.isnull().sum()
        missing_pcts = (df.isnull().mean() * 100).round(2)
        total_missing = int(missing_counts.sum())
        total_cells = df.shape[0] * df.shape[1]

        columns_with_missing = []
        for col in df.columns:
            count = int(missing_counts[col])
            if count > 0:
                columns_with_missing.append({
                    "column": col,
                    "missing_count": count,
                    "missing_pct": float(missing_pcts[col]),
                })

        return {
            "total_missing": total_missing,
            "total_cells": total_cells,
            "overall_missing_pct": round(total_missing / total_cells * 100, 2) if total_cells > 0 else 0.0,
            "columns_with_missing": columns_with_missing,
            "total_columns_with_missing": len(columns_with_missing),
        }
