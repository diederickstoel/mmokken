import numpy as np
import pytest

from mmokken.utils.recode import recode
from mmokken.utils.twoway import twoway


# -------------------- recode --------------------


def test_recode_reverses_specified_items_with_default_range():
    x = np.array([[0, 1, 2], [1, 1, 0], [2, 0, 1]], dtype=float)
    out = recode(x, items=[0])
    expected = np.array([[2, 1, 2], [1, 1, 0], [0, 0, 1]], dtype=float)
    assert np.array_equal(out, expected)
    # Untouched items returned unchanged
    assert np.array_equal(out[:, 1:], x[:, 1:])


def test_recode_preserves_nans():
    x = np.array([[0, 1], [np.nan, 2], [2, 0]], dtype=float)
    out = recode(x, items=[0])
    assert np.isnan(out[1, 0])
    assert np.array_equal(np.isfinite(out[:, 0]), np.array([True, False, True]))


def test_recode_with_explicit_values_uses_passed_range():
    x = np.array([[0, 1], [1, 0]], dtype=float)
    out = recode(x, items=[0], values=[0, 1, 2, 3])
    # max=3, min=0 -> new = 3 - x + 0
    assert np.array_equal(out[:, 0], np.array([3, 2]))


def test_recode_no_items_is_noop():
    x = np.array([[0, 1], [1, 2]], dtype=float)
    out = recode(x)
    assert np.array_equal(out, x)


# -------------------- twoway --------------------


def test_twoway_warns_when_no_missing_values():
    x = np.array([[0, 1, 2], [1, 2, 0]], dtype=float)
    with pytest.warns(UserWarning, match="does not contain missing values"):
        out = twoway(x)
    assert np.array_equal(out, x)


def test_twoway_imputes_missing_within_bounds():
    rng = np.random.default_rng(42)
    base = rng.integers(0, 4, size=(40, 5)).astype(float)
    # Inject missing values randomly
    mask = rng.random((40, 5)) < 0.1
    x = base.copy()
    x[mask] = np.nan
    out = twoway(x, seed=0)
    assert out.shape == x.shape
    assert not np.isnan(out).any()
    # Observed cells preserved
    observed = ~np.isnan(x)
    assert np.array_equal(out[observed], x[observed])
    # Bounds respected
    assert out.min() >= 0
    assert out.max() <= 3


def test_twoway_multiple_completed_datasets_returns_list():
    rng = np.random.default_rng(1)
    x = rng.integers(0, 3, size=(20, 4)).astype(float)
    x[0, 0] = np.nan
    x[3, 2] = np.nan
    out = twoway(x, n_completed_data_sets=3, seed=2)
    assert isinstance(out, list)
    assert len(out) == 3
    # Datasets should differ because of random noise
    diffs = [not np.array_equal(out[0], out[i]) for i in (1, 2)]
    assert any(diffs)


def test_twoway_rejects_row_with_all_missing():
    x = np.array([[1, 2], [np.nan, np.nan], [0, 1]], dtype=float)
    with pytest.raises(ValueError, match="At least one row"):
        twoway(x, seed=0)


def test_twoway_rejects_column_with_all_missing():
    x = np.array([[1, np.nan], [2, np.nan]], dtype=float)
    with pytest.raises(ValueError, match="At least one column"):
        twoway(x, seed=0)


def test_twoway_rejects_noninteger_or_negative():
    x = np.array([[0, 1.5], [1, 0]], dtype=float)
    with pytest.raises(ValueError, match="integers"):
        twoway(x, seed=0)
    x = np.array([[-1, 0], [0, 1]], dtype=float)
    with pytest.raises(ValueError, match="nonnegative"):
        twoway(x, seed=0)
