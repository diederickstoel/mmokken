import numpy as np
import pandas as pd
import pytest

from mmokken.validation import check_data, check_ml_data


def test_check_data_shifts_minimum_to_zero():
    # Source mapping: R/internalFunctions.R::check.data
    x = np.array([[1, 2], [2, 3], [3, 4]], dtype=float)
    out = check_data(x, check_scores=False)
    assert np.min(out) == 0
    assert np.array_equal(out, np.array([[0, 1], [1, 2], [2, 3]], dtype=float))


def test_check_data_accepts_dataframe():
    x = pd.DataFrame([[0, 1], [1, 2], [2, 3]])
    out = check_data(x, check_scores=False)
    assert isinstance(out, np.ndarray)
    assert out.shape == (3, 2)


def test_check_data_raises_on_missing_values():
    x = np.array([[0, 1], [np.nan, 2]])
    with pytest.raises(ValueError, match="Missing values are not allowed"):
        check_data(x)


def test_check_data_raises_on_noninteger_values():
    x = np.array([[0.0, 1.5], [1.0, 2.0]])
    with pytest.raises(ValueError, match="All scores must be integers"):
        check_data(x)


def test_check_data_raises_on_negative_values():
    x = np.array([[0, 1], [-1, 2]])
    with pytest.raises(ValueError, match="All scores should be nonnegative"):
        check_data(x)


def test_check_data_warns_on_varying_observed_score_support():
    x = np.array([[0, 0], [1, 1], [2, 1]], dtype=float)
    with pytest.warns(UserWarning, match="Varying numbers of item scores were observed"):
        check_data(x, check_scores=True)


def test_check_data_raises_when_more_than_ten_categories():
    x = np.array([[0, 10], [10, 0]], dtype=float)
    with pytest.raises(ValueError, match="more than 10 categories"):
        check_data(x, check_scores=False)


def test_check_ml_data_keeps_first_column_and_shifts_items():
    # Source mapping: R/internalFunctions.R::check.ml.data
    x = np.array(
        [
            [101, 2, 3],
            [101, 3, 4],
            [102, 4, 5],
        ],
        dtype=float,
    )
    out = check_ml_data(x, check_scores=False)
    assert np.array_equal(out[:, 0], np.array([101, 101, 102], dtype=float))
    assert np.array_equal(out[:, 1:], np.array([[0, 1], [1, 2], [2, 3]], dtype=float))
