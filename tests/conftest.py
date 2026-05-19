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
