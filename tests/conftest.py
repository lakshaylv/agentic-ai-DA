import pandas as pd
import pytest


@pytest.fixture
def sample_df():
    return pd.DataFrame({
        "category": ["A", "A", "B", "B", "C"],
        "value": [10, 20, 30, 40, 50],
        "score": [1.5, 2.5, 3.5, 4.5, 5.0],
        "label": ["x", "y", "z", "w", "v"],
    })


@pytest.fixture
def df_with_missing():
    return pd.DataFrame({
        "name": ["alice", "bob", None, "dave", None],
        "age": [25, None, 35, None, 45],
        "city": ["nyc", "sf", "nyc", "sf", None],
    })


@pytest.fixture
def df_with_dates():
    return pd.DataFrame({
        "date": pd.to_datetime(["2024-01-15", "2024-03-20", "2024-06-10", "2024-09-05", "2024-12-25"]),
        "category": ["A", "B", "A", "B", "A"],
        "value": [100, 200, 150, 300, 250],
        "score": [1.0, 2.0, 3.0, 4.0, 5.0],
    })


@pytest.fixture
def df_wide():
    return pd.DataFrame({
        "region": ["North", "North", "South", "South", "East"],
        "product": ["A", "B", "A", "B", "A"],
        "sales": [100, 200, 150, 250, 300],
        "profit": [10, 30, 20, 50, 60],
    })
