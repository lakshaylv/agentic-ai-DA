import pandas as pd

from backend.tools.base import BaseTool


SUPPORTED_AGGREGATIONS = {"sum", "mean", "median", "min", "max", "count", "std", "var"}

DERIVE_OPERATIONS = {
    "multiply": lambda a, b: a * b,
    "divide": lambda a, b: a / b,
    "add": lambda a, b: a + b,
    "subtract": lambda a, b: a - b,
}

SUPPORTED_OPERATORS = {
    "eq": lambda col, val: col == val,
    "ne": lambda col, val: col != val,
    "gt": lambda col, val: col > val,
    "gte": lambda col, val: col >= val,
    "lt": lambda col, val: col < val,
    "lte": lambda col, val: col <= val,
    "contains": lambda col, val: col.astype(str).str.contains(str(val), na=False, regex=False),
}


class GroupBy(BaseTool):
    """Group a column by another column with an aggregation (sum, mean, count, etc.)."""

    @property
    def name(self) -> str:
        return "groupby"

    @property
    def param_schema(self) -> dict:
        return {
            "group_col": {"type": "string", "description": "Column to group by"},
            "metric": {"type": "string", "description": "Column to aggregate"},
            "aggregation": {
                "type": "string",
                "description": "Aggregation function",
                "default": "sum",
                "enum": sorted(SUPPORTED_AGGREGATIONS),
            },
        }

    def _execute(self, df: pd.DataFrame, group_col: str, metric: str, aggregation: str = "sum") -> dict:
        if group_col not in df.columns:
            raise ValueError(f"Column '{group_col}' not found. Available: {df.columns.tolist()}")
        if metric not in df.columns:
            raise ValueError(f"Column '{metric}' not found. Available: {df.columns.tolist()}")
        if aggregation not in SUPPORTED_AGGREGATIONS:
            raise ValueError(f"Unsupported aggregation '{aggregation}'. Supported: {sorted(SUPPORTED_AGGREGATIONS)}")

        if group_col == metric:
            grouped = df.groupby(group_col).size().reset_index(name=f"{metric}_{aggregation}")
        else:
            grouped = df.groupby(group_col)[metric].agg(aggregation).reset_index()
        grouped[group_col] = grouped[group_col].astype(str)
        for col in grouped.select_dtypes(include="number").columns:
            grouped[col] = grouped[col].round(2)

        return {
            "grouped": grouped.to_dict(orient="records"),
            "group_col": group_col,
            "metric": metric,
            "aggregation": aggregation,
        }


class FilterTool(BaseTool):
    """Filter rows based on a column condition (eq, gt, lt, contains, etc.)."""

    @property
    def name(self) -> str:
        return "filter"

    @property
    def param_schema(self) -> dict:
        return {
            "column": {"type": "string", "description": "Column to filter on"},
            "operator": {
                "type": "string",
                "description": "Comparison operator",
                "default": "eq",
                "enum": sorted(SUPPORTED_OPERATORS.keys()),
            },
            "value": {"description": "Value to compare against"},
        }

    def _execute(self, df: pd.DataFrame, column: str, operator: str = "eq", value: object = None) -> dict:
        if column not in df.columns:
            raise ValueError(f"Column '{column}' not found. Available: {df.columns.tolist()}")
        if operator not in SUPPORTED_OPERATORS:
            raise ValueError(f"Unsupported operator '{operator}'. Supported: {sorted(SUPPORTED_OPERATORS.keys())}")

        op_func = SUPPORTED_OPERATORS[operator]
        mask = op_func(df[column], value)
        filtered = df[mask]

        return {
            "rows_before": df.shape[0],
            "rows_after": filtered.shape[0],
            "column": column,
            "operator": operator,
            "value": str(value),
            "preview": filtered.head(10).to_dict(orient="records"),
        }


class DeriveAggregate(BaseTool):
    """Compute a derived column from two existing columns using an operation (e.g., multiply), then group by another column and aggregate."""

    @property
    def name(self) -> str:
        return "derive_aggregate"

    @property
    def param_schema(self) -> dict:
        return {
            "group_col": {"type": "string", "description": "Column to group by"},
            "col1": {"type": "string", "description": "First operand column"},
            "col2": {"type": "string", "description": "Second operand column"},
            "operation": {
                "type": "string",
                "description": "Operation: col1 <op> col2",
                "default": "multiply",
                "enum": sorted(DERIVE_OPERATIONS.keys()),
            },
            "aggregation": {
                "type": "string",
                "description": "Aggregation function",
                "default": "sum",
                "enum": sorted(SUPPORTED_AGGREGATIONS),
            },
        }

    def _execute(
        self,
        df: pd.DataFrame,
        group_col: str,
        col1: str,
        col2: str,
        operation: str = "multiply",
        aggregation: str = "sum",
    ) -> dict:
        if group_col not in df.columns:
            raise ValueError(f"Column '{group_col}' not found. Available: {df.columns.tolist()}")
        if col1 not in df.columns:
            raise ValueError(f"Column '{col1}' not found. Available: {df.columns.tolist()}")
        if col2 not in df.columns:
            raise ValueError(f"Column '{col2}' not found. Available: {df.columns.tolist()}")
        if operation not in DERIVE_OPERATIONS:
            raise ValueError(f"Unsupported operation '{operation}'. Supported: {sorted(DERIVE_OPERATIONS.keys())}")
        if aggregation not in SUPPORTED_AGGREGATIONS:
            raise ValueError(f"Unsupported aggregation '{aggregation}'. Supported: {sorted(SUPPORTED_AGGREGATIONS)}")

        op_func = DERIVE_OPERATIONS[operation]
        temp = df.copy()
        derived_col = f"{col1}_{operation}_{col2}"
        temp[derived_col] = op_func(temp[col1], temp[col2])

        result = temp.groupby(group_col)[derived_col].agg(aggregation).reset_index()
        result[group_col] = result[group_col].astype(str)

        return {
            "grouped": result.to_dict(orient="records"),
            "group_col": group_col,
            "operation": operation,
            "expression": f"{col1} {operation} {col2}",
            "aggregation": aggregation,
            "derived_column": derived_col,
        }
