import pathlib
import sys

import pytest

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))
from doe import DOE


def test_compute_global_sum_ac():
    """Ensure the AC placeholder objective returns a populated result."""
    res = DOE.compute("network_test", "ac", "global_sum", alpha=0.1, beta=0.2)
    assert res["status"]
    assert res["envelopes"]

def test_fairness_placeholder():
    """Verify the fairness objective raises a clear ``NotImplementedError``."""
    with pytest.raises(NotImplementedError):
        DOE.compute("network_test", "dc", "fairness", alpha=0.1, beta=0.2)
