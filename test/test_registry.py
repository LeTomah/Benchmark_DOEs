import pathlib
import sys

import pytest

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))
from doe import DOE


def test_ac_placeholder():
    with pytest.raises(NotImplementedError):
        DOE.compute("network_test", "ac", "global_sum", alpha=0.1, beta=0.2)


def test_fairness_placeholder():
    with pytest.raises(NotImplementedError):
        DOE.compute("network_test", "dc", "fairness", alpha=0.1, beta=0.2)
