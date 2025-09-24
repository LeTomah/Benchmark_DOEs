import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))
from doe import DOE


def test_compute_global_sum_dc():
    """Run the DC solver pipeline on the demo network and assert success."""
    res = DOE.compute(
        "network_test",
        "dc",
        "global_sum",
        alpha=0.1,
        beta=0.2,
        p_min=-1.0,
        p_max=1.0,
        theta_min=-0.3,
        theta_max=0.3,
    )
    assert res["status"]
    assert res["model"] is not None
    assert isinstance(res["envelopes"], dict)
