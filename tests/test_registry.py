import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from doe import registry


def test_registry_keys():
    assert "dc" in registry.POWERFLOW_REGISTRY
    assert "ac" in registry.POWERFLOW_REGISTRY
    assert "global_sum" in registry.OBJECTIVE_REGISTRY
    assert "fairness" in registry.OBJECTIVE_REGISTRY


def test_ac_placeholder():
    with pytest.raises(NotImplementedError):
        registry.POWERFLOW_REGISTRY["ac"](None, None, None, None)


def test_fairness_placeholder():
    with pytest.raises(NotImplementedError):
        registry.OBJECTIVE_REGISTRY["fairness"](None, None, None, None)
