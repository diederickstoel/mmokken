import numpy as np

from mokken_py.core.transforms import complete_observed_frequencies, dphi, phi


def test_phi_actions_match_expected_numpy_forms():
    # Source mapping: R/internalFunctions.R::phi
    A = np.array([[1.0, 2.0, 3.0], [0.0, 1.0, 0.0]])
    f = np.array([0.2, 0.5, 0.8])

    assert np.allclose(phi(A, f, "identity"), A @ f)
    assert np.allclose(phi(A, f, "exp"), A @ np.exp(f))
    assert np.allclose(phi(A, f, "log"), A @ np.log(np.abs(f) + 1e-80))
    assert np.allclose(phi(A, f, "sqrt"), A @ np.sqrt(f))
    assert np.allclose(phi(A, f, "xlogx"), A @ (-f * np.log(f + 1e-80)))
    assert np.allclose(phi(A, f, "xbarx"), A @ (f * (1 - f)))


def test_phi_log_uses_abs_and_eps_for_zero_and_negative_values():
    f = np.array([0.0, -2.0, 3.0])
    A = np.eye(3)
    out = phi(A, f, "log")
    expected = np.log(np.abs(f) + 1e-80)
    assert np.allclose(out, expected)
    assert np.isfinite(out).all()


def test_dphi_actions_match_expected_numpy_forms():
    # Source mapping: R/internalFunctions.R::dphi
    A = np.array([[1.0, 2.0, 3.0], [0.0, 1.0, 0.0]])
    f = np.array([0.2, 0.5, 0.8])
    df = np.array([[1.0, 0.0], [0.5, 1.0], [2.0, 1.0]])

    assert np.allclose(dphi(A, f, df, "identity"), A @ df)
    assert np.allclose(dphi(A, f, df, "exp"), A @ (np.exp(f)[:, None] * df))
    assert np.allclose(dphi(A, f, df, "log"), A @ ((1 / (f + 1e-80))[:, None] * df))
    assert np.allclose(dphi(A, f, df, "sqrt"), A @ ((1 / (2 * np.sqrt(f)))[:, None] * df))
    assert np.allclose(dphi(A, f, df, "xlogx"), A @ ((-1 - np.log(f + 1e-80))[:, None] * df))
    assert np.allclose(dphi(A, f, df, "xbarx"), A @ ((1 - 2 * f)[:, None] * df))


def test_dphi_log_preserves_zero_division_edge_case_behavior():
    A = np.eye(2)
    f = np.array([0.0, 2.0])
    df = np.array([[1.0], [1.0]])
    out = dphi(A, f, df, "log")
    expected = (1.0 / (f + 1e-80))[:, None] * df
    assert np.allclose(out, expected)


def test_complete_observed_frequencies_counts_patterns():
    # Source mapping: R/internalFunctions.R::complete.observed.frequencies
    data = np.array(
        [
            [0, 0],
            [0, 1],
            [1, 0],
            [1, 1],
            [1, 1],
        ],
        dtype=float,
    )
    out = complete_observed_frequencies(data, J=2, m=2, order_items=False)
    expected = np.array([[1.0], [1.0], [1.0], [2.0]])
    assert out.shape == (4, 1)
    assert np.array_equal(out, expected)


def test_complete_observed_frequencies_order_items_matches_manual_reorder():
    data = np.array(
        [
            [0, 1, 0],
            [1, 1, 0],
            [1, 0, 0],
            [1, 1, 1],
        ],
        dtype=float,
    )
    out_ordered = complete_observed_frequencies(data, J=3, m=2, order_items=True)
    # R logic: rev(order(colMeans(data)))
    order_idx = np.argsort(np.mean(data, axis=0), kind="mergesort")[::-1]
    out_manual = complete_observed_frequencies(data[:, order_idx], J=3, m=2, order_items=False)
    assert np.array_equal(out_ordered, out_manual)

