import pandas as pd

from backend.tools.base import BaseTool


SUPPORTED_PIVOT_AGGREGATIONS = {"sum", "mean", "median", "min", "max", "count", "std"}

DATE_PARTS = {"year", "month", "quarter", "day", "weekday", "hour"}


class SortTopK(BaseTool):
    """Sort a dataset by a column and return the top or bottom N rows."""

    @property
    def name(self) -> str:
        return "sort_topk"

    @property
    def param_schema(self) -> dict:
        return {
            "sort_col": {"type": "string", "description": "Column to sort by"},
            "ascending": {"type": "boolean", "description": "Sort ascending (default false = top first)", "default": False},
            "limit": {"type": "integer", "description": "Number of rows to return", "default": 10},
        }

    def _execute(self, df: pd.DataFrame, sort_col: str, ascending: bool = False, limit: int = 10) -> dict:
        if sort_col not in df.columns:
            raise ValueError(f"Column '{sort_col}' not found. Available: {df.columns.tolist()}")
        if limit < 1:
            raise ValueError("limit must be >= 1")

        sorted_df = df.sort_values(by=sort_col, ascending=ascending).head(limit)
        return {
            "sorted": sorted_df.to_dict(orient="records"),
            "sort_col": sort_col,
            "ascending": ascending,
            "limit": limit,
            "total_rows": df.shape[0],
        }


class ValueCounts(BaseTool):
    """Get frequency counts of unique values in a column."""

    @property
    def name(self) -> str:
        return "value_counts"

    @property
    def param_schema(self) -> dict:
        return {
            "column": {"type": "string", "description": "Column to count values for"},
        }

    def _execute(self, df: pd.DataFrame, column: str) -> dict:
        if column not in df.columns:
            raise ValueError(f"Column '{column}' not found. Available: {df.columns.tolist()}")

        counts = df[column].value_counts(dropna=False).reset_index()
        counts.columns = [column, "count"]
        counts[column] = counts[column].astype(str)

        return {
            "value_counts": counts.to_dict(orient="records"),
            "column": column,
            "unique_values": int(df[column].nunique()),
            "total_rows": df.shape[0],
        }


class SummaryStats(BaseTool):
    """Compute summary statistics (min, max, mean, std, quartiles) for numeric columns."""

    @property
    def name(self) -> str:
        return "summary_stats"

    @property
    def param_schema(self) -> dict:
        return {
            "columns": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Columns to summarize (default: all numeric columns)",
            },
        }

    def _execute(self, df: pd.DataFrame, columns: list[str] | None = None) -> dict:
        numeric_df = df.select_dtypes(include="number")
        if numeric_df.empty:
            raise ValueError("No numeric columns found in the dataset")

        if columns:
            missing = [c for c in columns if c not in numeric_df.columns]
            if missing:
                non_numeric = [c for c in missing if c in df.columns and c not in numeric_df.columns]
                if non_numeric:
                    raise ValueError(f"Columns are not numeric: {non_numeric}")
                raise ValueError(f"Columns not found: {missing}")
            numeric_df = numeric_df[columns]

        stats = numeric_df.describe(percentiles=[.25, .5, .75]).transpose()
        stats = stats.drop(columns=["count"], errors="ignore")
        stats = stats.reset_index().rename(columns={"index": "column"})
        stats = stats.round(4)

        return {
            "stats": stats.to_dict(orient="records"),
            "columns_analyzed": numeric_df.columns.tolist(),
        }


class Correlation(BaseTool):
    """Compute correlation between two numeric columns or return the full correlation matrix."""

    @property
    def name(self) -> str:
        return "correlation"

    @property
    def param_schema(self) -> dict:
        return {
            "col1": {"type": "string", "description": "First column (optional — if omitted, returns full matrix)"},
            "col2": {"type": "string", "description": "Second column (optional — if omitted, returns full matrix)"},
        }

    def _execute(self, df: pd.DataFrame, col1: str | None = None, col2: str | None = None) -> dict:
        numeric_df = df.select_dtypes(include="number")
        if numeric_df.shape[1] < 2:
            raise ValueError("Need at least 2 numeric columns for correlation")

        if col1 and col2:
            for c in (col1, col2):
                if c not in df.columns:
                    raise ValueError(f"Column '{c}' not found. Available: {df.columns.tolist()}")
                if c not in numeric_df.columns:
                    raise ValueError(f"Column '{c}' is not numeric")
            val = numeric_df[col1].corr(numeric_df[col2])
            return {
                "correlation": round(val, 4),
                "col1": col1,
                "col2": col2,
                "method": "pearson",
            }
        elif col1 or col2:
            raise ValueError("Provide both col1 and col2, or omit both for the full matrix")

        matrix = numeric_df.corr().round(4).reset_index()
        matrix = matrix.rename(columns={"index": "column"})
        matrix = matrix.where(pd.notna(matrix), None)

        return {
            "correlation_matrix": matrix.to_dict(orient="records"),
            "columns": numeric_df.columns.tolist(),
            "method": "pearson",
        }


class DateExtract(BaseTool):
    """Extract a date part (year, month, quarter, day, weekday, hour) from a datetime column."""

    @property
    def name(self) -> str:
        return "date_extract"

    @property
    def param_schema(self) -> dict:
        return {
            "column": {"type": "string", "description": "Date/datetime column to extract from"},
            "part": {
                "type": "string",
                "description": "Date part to extract",
                "enum": sorted(DATE_PARTS),
            },
        }

    def _execute(self, df: pd.DataFrame, column: str, part: str) -> dict:
        if column not in df.columns:
            raise ValueError(f"Column '{column}' not found. Available: {df.columns.tolist()}")
        if part not in DATE_PARTS:
            raise ValueError(f"Unsupported date part '{part}'. Supported: {sorted(DATE_PARTS)}")

        col = pd.to_datetime(df[column], errors="coerce")
        if col.isna().all():
            raise ValueError(f"Column '{column}' could not be parsed as datetime")

        extractors = {
            "year": col.dt.year,
            "month": col.dt.month,
            "quarter": col.dt.quarter,
            "day": col.dt.day,
            "weekday": col.dt.day_name(),
            "hour": col.dt.hour,
        }
        extracted = extractors[part]
        counts = extracted.value_counts(dropna=False).reset_index()
        counts.columns = [part, "count"]
        counts[part] = counts[part].astype(str)
        counts = counts.sort_values(part).to_dict(orient="records")

        return {
            "part": part,
            "column": column,
            "extracted": counts,
            "total_rows": int(col.notna().sum()),
            "null_count": int(col.isna().sum()),
        }


class PivotTable(BaseTool):
    """Create a cross-tabulation (pivot table) with an aggregation."""

    @property
    def name(self) -> str:
        return "pivot_table"

    @property
    def param_schema(self) -> dict:
        return {
            "index": {"type": "string", "description": "Row index column"},
            "columns": {"type": "string", "description": "Column to pivot"},
            "values": {"type": "string", "description": "Value column to aggregate"},
            "aggregation": {
                "type": "string",
                "description": "Aggregation function",
                "default": "sum",
                "enum": sorted(SUPPORTED_PIVOT_AGGREGATIONS),
            },
        }

    def _execute(self, df: pd.DataFrame, index: str, columns: str, values: str, aggregation: str = "sum") -> dict:
        for col in (index, columns, values):
            if col not in df.columns:
                raise ValueError(f"Column '{col}' not found. Available: {df.columns.tolist()}")
        if aggregation not in SUPPORTED_PIVOT_AGGREGATIONS:
            raise ValueError(f"Unsupported aggregation '{aggregation}'. Supported: {sorted(SUPPORTED_PIVOT_AGGREGATIONS)}")
        if values not in df.select_dtypes(include="number").columns:
            raise ValueError(f"Column '{values}' must be numeric for pivot aggregation")

        pivot = df.pivot_table(
            index=index,
            columns=columns,
            values=values,
            aggfunc=aggregation,
            fill_value=0,
        )
        pivot = pivot.reset_index()
        pivot = pivot.where(pd.notna(pivot), None)
        for col in pivot.columns:
            if col != index:
                pivot[col] = pivot[col].astype(float)

        return {
            "pivot": pivot.to_dict(orient="records"),
            "index": index,
            "columns": columns,
            "values": values,
            "aggregation": aggregation,
        }


class Preview(BaseTool):
    """Show the first N rows, last N rows, or a random sample of the dataset."""

    @property
    def name(self) -> str:
        return "preview"

    @property
    def param_schema(self) -> dict:
        return {
            "n": {"type": "integer", "description": "Number of rows to show", "default": 5},
            "method": {
                "type": "string",
                "description": "Which rows to show",
                "default": "head",
                "enum": ["head", "tail", "sample"],
            },
        }

    def _execute(self, df: pd.DataFrame, n: int = 5, method: str = "head") -> dict:
        if n < 1:
            raise ValueError("n must be >= 1")
        if method not in ("head", "tail", "sample"):
            raise ValueError(f"Unsupported method '{method}'. Use head, tail, or sample")

        methods = {
            "head": df.head(n),
            "tail": df.tail(n),
            "sample": df.sample(n=min(n, df.shape[0])),
        }
        result = methods[method]
        return {
            "rows": result.to_dict(orient="records"),
            "method": method,
            "requested": n,
            "returned": result.shape[0],
            "total_rows": df.shape[0],
            "columns": df.columns.tolist(),
        }


class ColumnSelect(BaseTool):
    """View specific columns from the dataset."""

    @property
    def name(self) -> str:
        return "column_select"

    @property
    def param_schema(self) -> dict:
        return {
            "columns": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Columns to select",
            },
        }

    def _execute(self, df: pd.DataFrame, columns: list[str]) -> dict:
        if not columns:
            raise ValueError("Must provide at least one column")
        missing = [c for c in columns if c not in df.columns]
        if missing:
            raise ValueError(f"Columns not found: {missing}. Available: {df.columns.tolist()}")

        selected = df[columns]
        return {
            "rows": selected.head(50).to_dict(orient="records"),
            "columns": columns,
            "total_rows": df.shape[0],
            "returned_rows": min(50, df.shape[0]),
        }
