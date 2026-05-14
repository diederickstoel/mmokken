# Installation

```bash
pip install mmokken
```

For an editable development install from a clone:

```bash
git clone https://github.com/diederickstoel/mmokken
cd mmokken
pip install -e ".[dev,test,docs]"
```

`mmokken` requires Python ≥ 3.10 and depends on numpy, scipy, and pandas.
matplotlib is an optional dependency for the plotting helpers
(`pip install mmokken[plot]`).
