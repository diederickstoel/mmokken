import numpy as np


def coefHTiny(X):
    """
    Original R source:
    - r_reference/mokken_3.1.2/mokken/R/internalFunctions.R::coefHTiny

    Compute Mokken scalability coefficients.

    Parameters
    ----------
    X : numpy array (respondents x items)

    Returns
    -------
    dict with
        Hij : item pair scalability matrix
        Hi  : item scalability vector
        H   : overall scalability
    """

    X = np.asarray(X)

    # covariance matrix
    S = np.cov(X, rowvar=False)

    # sorted items for Smax
    X_sorted = np.sort(X, axis=0)

    Smax = np.cov(X_sorted, rowvar=False)

    Hij = S / Smax

    np.fill_diagonal(S, 0)
    np.fill_diagonal(Smax, 0)

    Hi = S.sum(axis=1) / Smax.sum(axis=1)

    H = S.sum() / Smax.sum()

    return {
        "Hij": Hij,
        "Hi": Hi,
        "H": H
    }
