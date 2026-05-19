from backend.tools.inspection import SchemaInspector, MissingValueAnalyzer
from backend.tools.operations import GroupBy, FilterTool, DeriveAggregate
from backend.tools.analysis import (
    SortTopK, ValueCounts, SummaryStats, Correlation,
    DateExtract, PivotTable, Preview, ColumnSelect,
)


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


class TestSortTopK:
    def test_top_by_value(self, sample_df):
        tool = SortTopK()
        result = tool.execute(sample_df, sort_col="value")
        assert result.success
        assert result.data["sort_col"] == "value"
        assert result.data["ascending"] is False
        assert result.data["limit"] == 10
        assert result.data["sorted"][0]["value"] == 50

    def test_bottom_ascending(self, sample_df):
        tool = SortTopK()
        result = tool.execute(sample_df, sort_col="value", ascending=True, limit=2)
        assert result.success
        assert len(result.data["sorted"]) == 2
        assert result.data["sorted"][0]["value"] == 10

    def test_invalid_column(self, sample_df):
        tool = SortTopK()
        result = tool.execute(sample_df, sort_col="bad")
        assert not result.success

    def test_invalid_limit(self, sample_df):
        tool = SortTopK()
        result = tool.execute(sample_df, sort_col="value", limit=0)
        assert not result.success


class TestValueCounts:
    def test_basic_counts(self, sample_df):
        tool = ValueCounts()
        result = tool.execute(sample_df, column="category")
        assert result.success
        assert result.data["column"] == "category"
        assert len(result.data["value_counts"]) == 3
        assert result.data["unique_values"] == 3

    def test_invalid_column(self, sample_df):
        tool = ValueCounts()
        result = tool.execute(sample_df, column="bad")
        assert not result.success


class TestSummaryStats:
    def test_all_numeric(self, sample_df):
        tool = SummaryStats()
        result = tool.execute(sample_df)
        assert result.success
        cols = {s["column"] for s in result.data["stats"]}
        assert "value" in cols
        assert "score" in cols
        for stat in result.data["stats"]:
            assert "mean" in stat
            assert "min" in stat
            assert "max" in stat
            assert "std" in stat

    def test_specific_columns(self, sample_df):
        tool = SummaryStats()
        result = tool.execute(sample_df, columns=["value"])
        assert result.success
        assert result.data["columns_analyzed"] == ["value"]

    def test_non_numeric_column(self, sample_df):
        tool = SummaryStats()
        result = tool.execute(sample_df, columns=["category"])
        assert not result.success


class TestCorrelation:
    def test_pair(self, sample_df):
        tool = Correlation()
        result = tool.execute(sample_df, col1="value", col2="score")
        assert result.success
        assert isinstance(result.data["correlation"], float)
        assert -1 <= result.data["correlation"] <= 1

    def test_matrix(self, sample_df):
        tool = Correlation()
        result = tool.execute(sample_df)
        assert result.success
        assert len(result.data["correlation_matrix"]) == 2
        assert result.data["method"] == "pearson"

    def test_missing_one_col(self, sample_df):
        tool = Correlation()
        result = tool.execute(sample_df, col1="value")
        assert not result.success

    def test_invalid_column(self, sample_df):
        tool = Correlation()
        result = tool.execute(sample_df, col1="value", col2="bad")
        assert not result.success

    def test_non_numeric_column(self, sample_df):
        tool = Correlation()
        result = tool.execute(sample_df, col1="value", col2="category")
        assert not result.success

    def test_single_numeric_col(self, sample_df):
        single_col_df = sample_df[["value"]]
        tool = Correlation()
        result = tool.execute(single_col_df, col1="value", col2="value")
        assert not result.success


class TestDateExtract:
    def test_extract_year(self, df_with_dates):
        tool = DateExtract()
        result = tool.execute(df_with_dates, column="date", part="year")
        assert result.success
        assert result.data["part"] == "year"
        assert all(r["year"] == "2024" for r in result.data["extracted"])

    def test_extract_month(self, df_with_dates):
        tool = DateExtract()
        result = tool.execute(df_with_dates, column="date", part="month")
        assert result.success
        months = [int(r["month"]) for r in result.data["extracted"]]
        assert sorted(months) == [1, 3, 6, 9, 12]

    def test_extract_quarter(self, df_with_dates):
        tool = DateExtract()
        result = tool.execute(df_with_dates, column="date", part="quarter")
        assert result.success
        assert result.data["total_rows"] == 5

    def test_extract_weekday(self, df_with_dates):
        tool = DateExtract()
        result = tool.execute(df_with_dates, column="date", part="weekday")
        assert result.success
        assert len(result.data["extracted"]) > 0

    def test_invalid_column(self, sample_df):
        tool = DateExtract()
        result = tool.execute(sample_df, column="category", part="year")
        assert not result.success

    def test_invalid_part(self, df_with_dates):
        tool = DateExtract()
        result = tool.execute(df_with_dates, column="date", part="decade")
        assert not result.success


class TestPivotTable:
    def test_basic_pivot(self, df_wide):
        tool = PivotTable()
        result = tool.execute(df_wide, index="region", columns="product", values="sales")
        assert result.success
        assert result.data["index"] == "region"
        assert result.data["columns"] == "product"
        assert result.data["values"] == "sales"
        assert result.data["aggregation"] == "sum"

    def test_with_mean(self, df_wide):
        tool = PivotTable()
        result = tool.execute(df_wide, index="region", columns="product", values="sales", aggregation="mean")
        assert result.success

    def test_invalid_column(self, df_wide):
        tool = PivotTable()
        result = tool.execute(df_wide, index="bad", columns="product", values="sales")
        assert not result.success

    def test_non_numeric_values(self, sample_df):
        tool = PivotTable()
        result = tool.execute(sample_df, index="category", columns="label", values="label")
        assert not result.success

    def test_invalid_aggregation(self, df_wide):
        tool = PivotTable()
        result = tool.execute(df_wide, index="region", columns="product", values="sales", aggregation="bad")
        assert not result.success


class TestPreview:
    def test_head(self, sample_df):
        tool = Preview()
        result = tool.execute(sample_df)
        assert result.success
        assert len(result.data["rows"]) == 5
        assert result.data["method"] == "head"

    def test_tail(self, sample_df):
        tool = Preview()
        result = tool.execute(sample_df, method="tail")
        assert result.success
        assert result.data["method"] == "tail"

    def test_sample(self, sample_df):
        tool = Preview()
        result = tool.execute(sample_df, method="sample", n=3)
        assert result.success
        assert result.data["returned"] == 3

    def test_invalid_method(self, sample_df):
        tool = Preview()
        result = tool.execute(sample_df, method="middle")
        assert not result.success

    def test_invalid_n(self, sample_df):
        tool = Preview()
        result = tool.execute(sample_df, n=0)
        assert not result.success


class TestColumnSelect:
    def test_select_columns(self, sample_df):
        tool = ColumnSelect()
        result = tool.execute(sample_df, columns=["category", "value"])
        assert result.success
        assert result.data["columns"] == ["category", "value"]
        assert len(result.data["rows"]) == 5

    def test_invalid_column(self, sample_df):
        tool = ColumnSelect()
        result = tool.execute(sample_df, columns=["bad"])
        assert not result.success

    def test_empty_columns(self, sample_df):
        tool = ColumnSelect()
        result = tool.execute(sample_df, columns=[])
        assert not result.success

    def test_select_single(self, sample_df):
        tool = ColumnSelect()
        result = tool.execute(sample_df, columns=["value"])
        assert result.success
        assert list(result.data["rows"][0].keys()) == ["value"]
