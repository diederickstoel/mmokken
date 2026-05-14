from pathlib import Path

import numpy as np
import pytest

from mmokken.io.msp_loader import load_msp_dataset


# ---------- helpers ----------


def _write_pair(tmp_path: Path, var_lines: list[str], dat_rows: list[list[int]]) -> tuple[Path, Path]:
    var_p = tmp_path / "test.var"
    dat_p = tmp_path / "test.dat"
    var_p.write_text("\n".join(var_lines) + "\n", encoding="utf-8")
    dat_p.write_text(
        "\n".join("  ".join(str(v) for v in row) for row in dat_rows) + "\n",
        encoding="utf-8",
    )
    return dat_p, var_p


# ---------- unit tests with synthetic .dat/.var ----------


def test_load_msp_dataset_detects_item_group_and_id_columns(tmp_path):
    dat_p, var_p = _write_pair(
        tmp_path,
        var_lines=[
            "3|id|respondent number",
            "1|gender|0=male 1=female",
            "0|Item1|first item",
            "0|Item2|second item",
            "0|Item3|third item",
        ],
        dat_rows=[
            [101, 0, 0, 1, 2],
            [102, 1, 1, 1, 0],
            [103, 0, 0, 1, 1],
        ],
    )
    out = load_msp_dataset(dat_p, var_p)
    assert out.items.shape == (3, 3)
    assert out.item_labels == ["Item1", "Item2", "Item3"]
    assert out.item_long_labels == ["first item", "second item", "third item"]
    assert out.groups.shape == (3, 1)
    assert out.group_labels == ["gender"]
    assert out.respondent_id is not None
    assert np.array_equal(out.respondent_id, np.array([101, 102, 103]))


def test_load_msp_dataset_without_grouping_variables(tmp_path):
    dat_p, var_p = _write_pair(
        tmp_path,
        var_lines=["0|A|first", "0|B|second"],
        dat_rows=[[0, 1], [1, 0], [1, 1], [0, 0]],
    )
    out = load_msp_dataset(dat_p, var_p)
    assert out.items.shape == (4, 2)
    assert out.groups.shape == (4, 0)
    assert out.respondent_id is None


def test_load_msp_dataset_with_respondent_id(tmp_path):
    dat_p, var_p = _write_pair(
        tmp_path,
        var_lines=["3|sub|subject", "0|q1|", "0|q2|"],
        dat_rows=[[7, 0, 1], [8, 1, 1], [9, 1, 0]],
    )
    out = load_msp_dataset(dat_p, var_p)
    assert out.respondent_id is not None
    assert out.respondent_id.tolist() == [7, 8, 9]
    assert out.items.shape == (3, 2)


def test_load_msp_dataset_raises_on_column_count_mismatch(tmp_path):
    dat_p, var_p = _write_pair(
        tmp_path,
        var_lines=["0|A|", "0|B|"],
        dat_rows=[[0, 1, 2], [1, 0, 1]],
    )
    with pytest.raises(ValueError, match="expected 2 columns"):
        load_msp_dataset(dat_p, var_p)


def test_load_msp_dataset_rejects_multiple_id_columns(tmp_path):
    dat_p, var_p = _write_pair(
        tmp_path,
        var_lines=["3|id1|", "3|id2|", "0|A|"],
        dat_rows=[[1, 11, 0], [2, 22, 1]],
    )
    with pytest.raises(ValueError, match="more than one respondent ID"):
        load_msp_dataset(dat_p, var_p)


def test_load_msp_dataset_rejects_unknown_var_type(tmp_path):
    dat_p, var_p = _write_pair(
        tmp_path,
        var_lines=["0|A|", "2|wrong|"],  # 2 is not allowed
        dat_rows=[[0, 1], [1, 0]],
    )
    with pytest.raises(ValueError, match="Unknown type code"):
        load_msp_dataset(dat_p, var_p)


def test_load_msp_dataset_rejects_missing_item_column(tmp_path):
    dat_p, var_p = _write_pair(
        tmp_path,
        var_lines=["3|id|", "1|gender|"],
        dat_rows=[[1, 0], [2, 1]],
    )
    with pytest.raises(ValueError, match="no item columns"):
        load_msp_dataset(dat_p, var_p)


# ---------- integration test with real MSP 5 TEST.DAT ----------

_MSP_INSTALLED = Path(__file__).resolve().parents[1] / "msp_reference" / "installed"


@pytest.mark.skipif(
    not (_MSP_INSTALLED / "TEST.DAT").exists(),
    reason="MSP 5 installation not present at msp_reference/installed/",
)
def test_load_msp_dataset_reads_real_msp5_test_data():
    """Sanity check on the bundled MSP 5 odour-annoyance test set (828 × 17)."""
    out = load_msp_dataset(
        _MSP_INSTALLED / "TEST.DAT",
        _MSP_INSTALLED / "Test.var",
    )
    assert out.items.shape == (828, 17), "Expected 828 respondents × 17 items"
    assert out.item_labels[0] == "Item1"
    assert out.item_long_labels[0] == "keep windows closed"
    # Score range: items are 0..3 after check_data normalisation
    assert out.items.min() == 0
    assert out.items.max() == 3
    # No grouping or respondent ID in this test set
    assert out.groups.shape == (828, 0)
    assert out.respondent_id is None
