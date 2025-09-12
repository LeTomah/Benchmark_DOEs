import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from doe.compute import DOE


def test_compute_dc_global_sum():
    result = DOE.compute("toy.py", "dc", "global_sum", alpha=1.0, beta=1.0)
    assert result["status"] == "optimal"
    assert result["envelopes"], "Envelopes should not be empty"
    assert isinstance(result["objective_value"], float)
