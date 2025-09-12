import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))
from doe import DOE


def test_compute_global_sum_dc():
    res = DOE.compute("network_test", "dc", "global_sum", alpha=0.1, beta=0.2)
    assert res["status"]
    assert res["envelopes"]
