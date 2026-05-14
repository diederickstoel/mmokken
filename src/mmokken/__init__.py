"""mmokken — multidimensional non-parametric measurement models in Python.

Track B of the mMokken research programme: a behaviour-first port of the R
``mokken`` package (Van der Ark, 2007), with a multidimensional extension
(Stoel) and a forward-looking unified estimator API spanning non-parametric
and parametric IRT.

Current scope is the unidimensional core (B1). Multidimensional and parametric
families land in subsequent releases.
"""

from __future__ import annotations

from .core.scalability import coefH, coefHTiny
from .core.zscores import coefZ
from .diagnostics.errors import check_errors
from .diagnostics.monotonicity import check_monotonicity
from .diagnostics.pmatrix import check_pmatrix
from .diagnostics.reliability import check_reliability
from .diagnostics.restscore import check_restscore
from .search.aisp import aisp
from .search.normal import search_normal
from .utils.recode import recode
from .utils.twoway import twoway
from .validation import check_data, check_ml_data

__all__ = [
    "aisp",
    "check_data",
    "check_errors",
    "check_ml_data",
    "check_monotonicity",
    "check_pmatrix",
    "check_reliability",
    "check_restscore",
    "coefH",
    "coefHTiny",
    "coefZ",
    "recode",
    "search_normal",
    "twoway",
]

__version__ = "0.1.0.dev0"
