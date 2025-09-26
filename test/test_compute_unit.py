"""Unit tests for the high level compute module."""
import importlib
import pathlib
import sys
import types
from typing import Dict, List

import pytest


ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

compute_module = importlib.import_module("doe.compute")  # noqa: E402
from doe.compute import _load_network, compute  # noqa: E402
from data.networks import network_test  # noqa: E402
from doe.utils.graph import create_graph  # noqa: E402


@pytest.fixture(scope="module")
def example_network():
    """Return the demo pandapower network used across tests."""

    return network_test.build()


@pytest.fixture(scope="module")
def compute_argument_sets(example_network) -> List[Dict[str, object]]:
    """Collect the argument sets used to exercise the compute helper."""

    graph = create_graph(example_network)
    sorted_nodes: List[int] = sorted(graph.nodes)

    operational_nodes = sorted_nodes[:5]
    parent_nodes = sorted_nodes[5:7]
    children_nodes = sorted_nodes[7:9]

    dc_case = {
        "network": example_network,
        "network_name": "network_test",
        "mode": "dc",
        "objective": "global_sum",
        "operational_nodes": operational_nodes,
        "parent_nodes": parent_nodes,
        "children_nodes": children_nodes,
        "P_min": -5.0,
        "P_max": 5.0,
        "Q_min": -2.0,
        "Q_max": 2.0,
        "alpha": 1.0,
        "beta": 2.0,
        "security": {"theta_min": -0.5, "theta_max": 0.5},
    }

    ac_network = network_test.build()
    ac_case = {
        "network": ac_network,
        "network_name": "network_test",
        "mode": "ac",
        "objective": "global_sum",
        "operational_nodes": operational_nodes,
        "parent_nodes": parent_nodes,
        "children_nodes": children_nodes,
        "P_min": -5.0,
        "P_max": 5.0,
        "Q_min": -2.0,
        "Q_max": 2.0,
        "alpha": 1.0,
        "beta": 2.0,
        "security": {"v_min": 0.95, "v_max": 1.05},
    }

    argument_sets = [dc_case, ac_case]

    printable = []
    for case in argument_sets:
        summary = {
            "network": case["network_name"],
            "mode": case["mode"],
            "objective": case["objective"],
            "operational_nodes": case["operational_nodes"],
            "parent_nodes": case["parent_nodes"],
            "children_nodes": case["children_nodes"],
            "P_min": case["P_min"],
            "P_max": case["P_max"],
            "alpha": case["alpha"],
            "beta": case["beta"],
            "security": case["security"],
        }
        summary["Q_min"] = case["Q_min"]
        summary["Q_max"] = case["Q_max"]
        printable.append(summary)

    print("compute_argument_sets ->", printable)
    return argument_sets


def _build_compute_kwargs(case: Dict[str, object]) -> Dict[str, object]:
    """Return a shallow copy of the keyword arguments for ``compute``."""

    kwargs = {
        "alpha": case["alpha"],
        "beta": case["beta"],
        "operational_nodes": case["operational_nodes"],
        "parent_nodes": case["parent_nodes"],
        "children_nodes": case["children_nodes"],
        "P_min": case["P_min"],
        "P_max": case["P_max"],
        "security": case["security"],
    }
    kwargs["Q_min"] = case["Q_min"]
    kwargs["Q_max"] = case["Q_max"]
    return kwargs


def test_load_network_from_object(example_network):
    """Passing an existing pandapower network should return it unchanged."""

    loaded = _load_network(example_network)
    print(f"_load_network(object) -> buses: {len(loaded.bus)}")
    assert loaded is example_network


def test_load_network_from_name():
    """Loading from a known module name should instantiate the network."""

    loaded = _load_network("network_test")
    print(f"_load_network('network_test') -> type: {type(loaded)}")
    # The module returns a fresh pandapower network instance
    assert hasattr(loaded, "bus")
    assert len(loaded.bus) > 0


def test_load_network_invalid_name():
    """Unknown network names should raise a ``ValueError``."""

    with pytest.raises(ValueError):
        _load_network("does_not_exist")


def test_load_network_invalid_type():
    """Non string/non pandapower objects should raise a ``TypeError``."""

    with pytest.raises(TypeError):
        _load_network(42)


def test_load_network_module_without_build(monkeypatch):
    """Modules without a ``build`` attribute must trigger a ``ValueError``."""

    module_name = "data.networks.fake_module"
    fake_module = types.ModuleType(module_name)
    sys.modules[module_name] = fake_module
    try:
        with pytest.raises(ValueError):
            _load_network("fake_module")
    finally:
        del sys.modules[module_name]


def test_compute_builds_parameters_and_uses_solver(
    monkeypatch, compute_argument_sets
):
    """The public compute function should forward the correct parameters."""

    for case in compute_argument_sets:
        captured: Dict[str, object] = {}

        def fake_solver(
            graph,
            *,
            powerflow_builder,
            security_builder,
            objective_builder,
            params,
            options,
        ):
            captured.update(
                {
                    "graph": graph,
                    "powerflow_builder": powerflow_builder,
                    "security_builder": security_builder,
                    "objective_builder": objective_builder,
                    "params": params,
                    "options": options,
                }
            )
            return {
                "status": "optimal",
                "objective": 123.0,
                "envelopes": {"node": (1.0, 2.0)},
                "curtailment_report": {"node": 0.1},
                "diagnostics": {"iterations": 1},
            }

        monkeypatch.setattr(compute_module, "solve_model", fake_solver)

        kwargs = _build_compute_kwargs(case)
        result = compute(case["network"], case["mode"], case["objective"], **kwargs)
        print(f"compute({case['mode']}) -> {result}")

        assert result["status"] == "optimal"
        assert result["objective_value"] == 123.0
        assert captured["params"]["alpha"] == case["alpha"]
        assert captured["params"]["beta"] == case["beta"]
        assert captured["options"]["operational_nodes"] == case["operational_nodes"]
        assert captured["options"]["parent_nodes"] == case["parent_nodes"]
        assert captured["options"]["children_nodes"] == case["children_nodes"]
        assert captured["options"]["P_min"] == case["P_min"]
        assert captured["options"]["P_max"] == case["P_max"]
        assert captured["options"]["Q_min"] == case["Q_min"]
        assert captured["options"]["Q_max"] == case["Q_max"]
        if case["mode"] == "dc":
            assert captured["options"]["security"]["theta_min"] == case["security"]["theta_min"]
            assert captured["options"]["security"]["theta_max"] == case["security"]["theta_max"]
        else:
            assert captured["options"]["security"]["v_min"] == case["security"]["v_min"]
            assert captured["options"]["security"]["v_max"] == case["security"]["v_max"]
        assert result["envelopes"] == {"node": (1.0, 2.0)}


def test_compute_requires_alpha_and_beta(compute_argument_sets):
    """Both alpha and beta must be provided for the global_sum objective."""

    dc_case = next(case for case in compute_argument_sets if case["mode"] == "dc")

    kwargs_without_beta = _build_compute_kwargs(dc_case)
    kwargs_without_beta.pop("beta")
    with pytest.raises(ValueError):
        compute(dc_case["network"], dc_case["mode"], dc_case["objective"], **kwargs_without_beta)

    kwargs_without_alpha = _build_compute_kwargs(dc_case)
    kwargs_without_alpha.pop("alpha")
    with pytest.raises(ValueError):
        compute(dc_case["network"], dc_case["mode"], dc_case["objective"], **kwargs_without_alpha)


def test_compute_invalid_modes(compute_argument_sets):
    """Unknown powerflow or objective names should be rejected."""

    dc_case = next(case for case in compute_argument_sets if case["mode"] == "dc")
    valid_kwargs = _build_compute_kwargs(dc_case)

    with pytest.raises(ValueError):
        compute(dc_case["network"], "invalid", dc_case["objective"], **valid_kwargs)
    with pytest.raises(ValueError):
        compute(dc_case["network"], dc_case["mode"], "not_an_objective", **valid_kwargs)
