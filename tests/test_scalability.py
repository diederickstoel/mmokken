import numpy as np

from mokken.scalability import coefHTiny


def test_coef_htiny_small_matrix_matches_reference_values():
    # Source mapping: R/internalFunctions.R::coefHTiny
    X = np.array(
        [
            [0, 0, 0],
            [0, 1, 0],
            [1, 0, 1],
            [1, 1, 1],
            [2, 1, 1],
            [2, 2, 2],
        ],
        dtype=float,
    )

    result = coefHTiny(X)

    assert np.isclose(result["H"], 0.7735849056603773)
    assert np.allclose(result["Hi"], np.array([0.83333333, 0.65714286, 0.82857143]))
    assert result["Hij"].shape == (3, 3)
