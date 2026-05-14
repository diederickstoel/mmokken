import numpy as np
import pytest

from mmokken.search.aisp import aisp
from mmokken.search.ga import search_ga


def _synthetic_monotone_data(n=200, seed=0, j=6):
    rng = np.random.default_rng(seed)
    t = rng.standard_normal(n)
    thresholds = [
        [-0.5, 0.5],
        [-0.3, 0.7],
        [-0.4, 0.6],
        [-0.2, 0.8],
        [-0.45, 0.55],
        [-0.35, 0.65],
    ]
    cols = []
    for k in range(j):
        cols.append(np.digitize(t + 0.1 * rng.standard_normal(n), thresholds[k % 6]))
    return np.column_stack(cols).astype(float)


def _two_independent_scales(n=300, seed=0):
    """Synthetic data with two independent Mokken scales of 4 items each."""
    rng = np.random.default_rng(seed)
    t1 = rng.standard_normal(n)
    t2 = rng.standard_normal(n)
    cols = []
    for thr in ([-0.5, 0.5], [-0.3, 0.7], [-0.4, 0.6], [-0.2, 0.8]):
        cols.append(np.digitize(t1 + 0.1 * rng.standard_normal(n), thr))
    for thr in ([-0.4, 0.6], [-0.3, 0.7], [-0.45, 0.55], [-0.5, 0.5]):
        cols.append(np.digitize(t2 + 0.1 * rng.standard_normal(n), thr))
    return np.column_stack(cols).astype(float)


def test_search_ga_returns_partition_vector():
    x = _synthetic_monotone_data(n=200, seed=1)
    out = search_ga(x, lowerbound=0.3, alpha=0.05, popsize=20, maxgens=200, random_state=42)
    assert out.shape == (x.shape[1],)
    assert out.dtype == np.int64
    assert (out >= 0).all()


def test_search_ga_finds_single_scale_on_strongly_monotone_data():
    x = _synthetic_monotone_data(n=300, seed=2)
    out = search_ga(x, lowerbound=0.3, alpha=0.05, popsize=30, maxgens=300, random_state=0)
    # Strong unidimensional signal -> all 6 items in scale 1
    assert int((out == 1).sum()) == x.shape[1]


def test_search_ga_recovers_two_independent_scales():
    x = _two_independent_scales(n=400, seed=3)
    out = search_ga(x, lowerbound=0.3, alpha=0.05, popsize=40, maxgens=500, random_state=1)
    # We don't enforce label parity, only that the two halves are largely
    # separated. The first four items should mostly share a scale, the last
    # four likewise.
    first = out[:4]
    second = out[4:]
    # Within-half agreement: at least 3 of 4 share the same scale.
    assert max([int((first == k).sum()) for k in set(first)]) >= 3
    assert max([int((second == k).sum()) for k in set(second)]) >= 3


def test_search_ga_deterministic_with_seed():
    x = _synthetic_monotone_data(n=150, seed=4)
    out1 = search_ga(x, lowerbound=0.3, alpha=0.05, popsize=20, maxgens=200, random_state=7)
    out2 = search_ga(x, lowerbound=0.3, alpha=0.05, popsize=20, maxgens=200, random_state=7)
    assert np.array_equal(out1, out2)


def test_aisp_search_ga_calls_through():
    x = _synthetic_monotone_data(n=200, seed=5)
    out = aisp(
        x,
        lowerbound=0.3,
        search="ga",
        alpha=0.05,
        popsize=20,
        maxgens=200,
        verbose=False,
        random_state=11,
    )
    assert out.shape == (x.shape[1], 1)
    # On a clean unidim dataset the GA should put all items in one scale
    assert int((out[:, 0] == 1).sum()) == x.shape[1]


def test_aisp_search_ga_level_two_var_not_implemented():
    x = _synthetic_monotone_data(n=100, seed=6)
    with pytest.raises(NotImplementedError):
        aisp(
            x,
            lowerbound=0.3,
            search="ga",
            level_two_var=np.repeat(np.arange(50), 2),
            random_state=0,
        )
