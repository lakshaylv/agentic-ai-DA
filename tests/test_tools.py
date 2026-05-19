from backend.tools.inspection import SchemaInspector, MissingValueAnalyzer
from backend.tools.operations import GroupBy, FilterTool, DeriveAggregate


class TestSchemaInspector:
    def test_basic_schema(self, sample_df):
        tool = SchemaInspector()
        result = tool.execute(sample_df)
        assert result.success
        data = result.data
        assert data["row_count"] == 5
        assert data["column_count"] == 4
        assert set(data["columns"]) == {"category", "value", "score", "label"}
        assert data["dtypes"]["value"] == "int64"

    def test_metadata(self, sample_df):
        tool = SchemaInspector()
        result = tool.execute(sample_df)
        assert result.metadata.tool_name == "schema_inspector"
        assert result.metadata.execution_time_ms >= 0


class TestMissingValueAnalyzer:
    def test_no_missing(self, sample_df):
        tool = MissingValueAnalyzer()
        result = tool.execute(sample_df)
        assert result.success
        assert result.data["total_missing"] == 0
        assert result.data["total_columns_with_missing"] == 0

    def test_with_missing(self, df_with_missing):
        tool = MissingValueAnalyzer()
        result = tool.execute(df_with_missing)
        assert result.success
        assert result.data["total_missing"] == 5
        assert result.data["total_columns_with_missing"] == 3
        assert result.data["overall_missing_pct"] > 0

    def test_columns_with_missing_details(self, df_with_missing):
        tool = MissingValueAnalyzer()
        result = tool.execute(df_with_missing)
        cols = {c["column"] for c in result.data["columns_with_missing"]}
        assert cols == {"name", "age", "city"}


class TestGroupBy:
    def test_basic_groupby(self, sample_df):
        tool = GroupBy()
        result = tool.execute(sample_df, group_col="category", metric="value", aggregation="sum")
        assert result.success
        data = result.data
        assert len(data["grouped"]) == 3
        assert data["group_col"] == "category"
        assert data["metric"] == "value"
        assert data["aggregation"] == "sum"

    def test_all_aggregations(self, sample_df):
        tool = GroupBy()
        for agg in ["sum", "mean", "count", "min", "max", "std", "var", "median"]:
            result = tool.execute(sample_df, group_col="category", metric="value", aggregation=agg)
            assert result.success, f"Aggregation '{agg}' failed"

    def test_invalid_column(self, sample_df):
        tool = GroupBy()
        result = tool.execute(sample_df, group_col="nonexistent", metric="value")
        assert not result.success

    def test_invalid_aggregation(self, sample_df):
        tool = GroupBy()
        result = tool.execute(sample_df, group_col="category", metric="value", aggregation="invalid")
        assert not result.success

    def test_groupby_same_column(self, sample_df):
        tool = GroupBy()
        result = tool.execute(sample_df, group_col="category", metric="category", aggregation="count")
        assert result.success
        assert len(result.data["grouped"]) == 3


class TestFilterTool:
    def test_filter_eq(self, sample_df):
        tool = FilterTool()
        result = tool.execute(sample_df, column="category", operator="eq", value="A")
        assert result.success
        assert result.data["rows_after"] == 2

    def test_filter_gt(self, sample_df):
        tool = FilterTool()
        result = tool.execute(sample_df, column="value", operator="gt", value=25)
        assert result.success
        assert result.data["rows_after"] == 3

    def test_filter_contains(self, sample_df):
        tool = FilterTool()
        result = tool.execute(sample_df, column="label", operator="contains", value="x")
        assert result.success
        assert result.data["rows_after"] == 1

    def test_filter_all_rows(self, sample_df):
        tool = FilterTool()
        result = tool.execute(sample_df, column="value", operator="gte", value=10)
        assert result.success
        assert result.data["rows_after"] == 5

    def test_filter_no_match(self, sample_df):
        tool = FilterTool()
        result = tool.execute(sample_df, column="value", operator="gt", value=100)
        assert result.success
        assert result.data["rows_after"] == 0

    def test_invalid_column(self, sample_df):
        tool = FilterTool()
        result = tool.execute(sample_df, column="bad_col", operator="eq", value=1)
        assert not result.success

    def test_invalid_operator(self, sample_df):
        tool = FilterTool()
        result = tool.execute(sample_df, column="value", operator="bad_op", value=1)
        assert not result.success


class TestDeriveAggregate:
    def test_multiply(self, sample_df):
        tool = DeriveAggregate()
        result = tool.execute(
            sample_df, group_col="category", col1="value",
            col2="score", operation="multiply", aggregation="sum",
        )
        assert result.success
        data = result.data
        assert len(data["grouped"]) == 3
        assert data["operation"] == "multiply"
        assert data["expression"] == "value multiply score"

    def test_divide(self, sample_df):
        tool = DeriveAggregate()
        result = tool.execute(
            sample_df, group_col="category", col1="value",
            col2="score", operation="divide", aggregation="mean",
        )
        assert result.success
        assert len(result.data["grouped"]) == 3

    def test_add_and_subtract(self, sample_df):
        tool = DeriveAggregate()
        r1 = tool.execute(sample_df, group_col="category", col1="value", col2="score", operation="add")
        assert r1.success
        r2 = tool.execute(sample_df, group_col="category", col1="value", col2="score", operation="subtract")
        assert r2.success

    def test_invalid_column(self, sample_df):
        tool = DeriveAggregate()
        result = tool.execute(sample_df, group_col="category", col1="bad", col2="score")
        assert not result.success

    def test_invalid_operation(self, sample_df):
        tool = DeriveAggregate()
        result = tool.execute(sample_df, group_col="category", col1="value", col2="score", operation="power")
        assert not result.success

    def test_original_df_not_mutated(self, sample_df):
        original_cols = set(sample_df.columns)
        tool = DeriveAggregate()
        tool.execute(sample_df, group_col="category", col1="value", col2="score", operation="multiply")
        assert set(sample_df.columns) == original_cols
