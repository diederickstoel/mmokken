"""Loader for the MSP 5 ``.dat`` + ``.var`` file pair.

The MSP 5 program (ProGAMMA, 2003) stored Mokken data as two files:

* ``.var`` — one variable per line in the form ``type|name|label`` where
  ``type`` is ``0`` for an item, ``1`` for a grouping/background variable,
  and ``3`` for a respondent identifier.
* ``.dat`` — a whitespace-delimited numeric matrix whose columns match the
  ``.var`` row order exactly. Score range is supplied by the analyst at
  analysis time (in the ``.ms*`` script files), not by ``.var``.

The loader returns the validated item-score matrix along with grouping and
respondent-id arrays, so downstream code can pass ``items`` directly into
``mmokken.aisp`` / ``check_*`` without further preprocessing.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from ..validation import check_data

_ENCODINGS = ("utf-8", "cp1252", "latin1")
_VAR_ITEM = 0
_VAR_GROUP = 1
_VAR_ID = 3


@dataclass(frozen=True)
class MspDataset:
    """Structured result of :func:`load_msp_dataset`.

    Attributes
    ----------
    items
        ``(N, J)`` float array of item scores, validated by
        :func:`mmokken.check_data` (integers, non-negative, shifted to start
        at 0). Pass this directly to :func:`mmokken.aisp` and the
        ``check_*`` diagnostics.
    item_labels
        Length-``J`` list of item names from the ``.var`` file (column 2).
    item_long_labels
        Length-``J`` list of descriptive labels (column 3, may be empty).
    groups
        ``(N, K)`` float array of grouping variable values. ``K`` is 0 when
        no ``type==1`` columns are present in the ``.var`` file.
    group_labels
        Length-``K`` list of group variable names.
    respondent_id
        Length-``N`` integer array of respondent IDs when a ``type==3``
        column is present, otherwise ``None``.
    """

    items: np.ndarray
    item_labels: list[str]
    item_long_labels: list[str]
    groups: np.ndarray
    group_labels: list[str]
    respondent_id: np.ndarray | None


def _read_text(path: Path) -> str:
    last_err: Exception | None = None
    for enc in _ENCODINGS:
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError as err:
            last_err = err
            continue
    raise UnicodeDecodeError(  # pragma: no cover - all three encodings fail is rare
        "msp_loader",
        b"",
        0,
        1,
        f"Could not decode {path} with any of {_ENCODINGS}: {last_err}",
    )


def _parse_var(var_path: Path) -> tuple[list[int], list[str], list[str]]:
    """Parse a ``.var`` file. Returns (types, names, labels)."""
    text = _read_text(var_path)
    types: list[int] = []
    names: list[str] = []
    labels: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        parts = line.split("|")
        if len(parts) < 2:
            raise ValueError(
                f"Malformed line in {var_path.name}: {raw!r} — expected "
                "type|name[|label]"
            )
        try:
            type_code = int(parts[0])
        except ValueError as err:
            raise ValueError(
                f"Non-integer type code in {var_path.name}: {raw!r}"
            ) from err
        if type_code not in (_VAR_ITEM, _VAR_GROUP, _VAR_ID):
            raise ValueError(
                f"Unknown type code {type_code} in {var_path.name}; "
                f"allowed: 0 (item), 1 (grouping), 3 (respondent ID)"
            )
        types.append(type_code)
        names.append(parts[1].strip())
        labels.append("|".join(parts[2:]).strip() if len(parts) > 2 else "")
    if not types:
        raise ValueError(f"{var_path.name} contains no variable definitions")
    return types, names, labels


def _parse_dat(dat_path: Path, expected_cols: int) -> np.ndarray:
    """Parse a free-field numeric ``.dat`` file into a float array."""
    text = _read_text(dat_path)
    rows: list[list[float]] = []
    for line_no, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        tokens = line.split()
        if len(tokens) != expected_cols:
            raise ValueError(
                f"{dat_path.name} line {line_no}: expected {expected_cols} "
                f"columns, got {len(tokens)}"
            )
        try:
            rows.append([float(tok) for tok in tokens])
        except ValueError as err:
            raise ValueError(
                f"{dat_path.name} line {line_no}: non-numeric token — {err}"
            ) from err
    if not rows:
        raise ValueError(f"{dat_path.name} contains no data rows")
    return np.asarray(rows, dtype=float)


def load_msp_dataset(dat_path, var_path) -> MspDataset:
    """Load an MSP 5 ``.dat`` + ``.var`` pair.

    Parameters
    ----------
    dat_path, var_path
        Filesystem paths to the data and variable-definition files.

    Returns
    -------
    MspDataset
        Validated structure ready for downstream Mokken analysis.

    Raises
    ------
    ValueError
        If the ``.var`` file is empty or malformed, if the column count in
        ``.dat`` does not match the ``.var`` definition, if more than one
        respondent-ID column is present, or if any item value fails
        :func:`mmokken.check_data`.
    """
    dat_p = Path(dat_path)
    var_p = Path(var_path)

    types, names, labels = _parse_var(var_p)
    if sum(1 for t in types if t == _VAR_ID) > 1:
        raise ValueError(
            f"{var_p.name} defines more than one respondent ID column "
            "(type=3); only one is permitted"
        )

    data = _parse_dat(dat_p, expected_cols=len(types))

    item_mask = np.array([t == _VAR_ITEM for t in types], dtype=bool)
    group_mask = np.array([t == _VAR_GROUP for t in types], dtype=bool)
    id_mask = np.array([t == _VAR_ID for t in types], dtype=bool)

    if not item_mask.any():
        raise ValueError(f"{var_p.name} defines no item columns (type=0)")

    item_block = data[:, item_mask]
    items = check_data(item_block, check_scores=True)

    groups = data[:, group_mask] if group_mask.any() else np.zeros((data.shape[0], 0))
    respondent_id = (
        data[:, id_mask][:, 0].astype(int) if id_mask.any() else None
    )

    item_labels = [names[i] for i in np.where(item_mask)[0]]
    item_long_labels = [labels[i] for i in np.where(item_mask)[0]]
    group_labels = [names[i] for i in np.where(group_mask)[0]]

    return MspDataset(
        items=items,
        item_labels=item_labels,
        item_long_labels=item_long_labels,
        groups=groups,
        group_labels=group_labels,
        respondent_id=respondent_id,
    )
