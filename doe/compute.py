"""High level interface for computing DOEs."""

from __future__ import annotations

from importlib import import_module
from typing import Any, Dict, Iterable, Mapping, Sequence

import pandapower as pp

from .constraints import powerflow_dc, powerflow_ac, security
from .objectives import global_sum, fairness
from .solvers.pyomo_backend import ModelConfiguration, solve_model
from .utils.graph import build_nx_from_pandapower, compute_info_dso, op_graph

POWERFLOW = {"dc": powerflow_dc.build, "ac": powerflow_ac.build}
OBJECTIVES = {"global_sum": global_sum.build, "fairness": fairness.build}


def _load_network(network: Any) -> pp.pandapowerNet:
    """Return a :class:`pandapowerNet` built from a name or existing object.

    Parameters
    ----------
    network:
        Either an existing :class:`pandapowerNet` or the name of a module inside
        :mod:`data.networks` exposing a :func:`build` function.

    Returns
    -------
    pandapowerNet
        Network ready for DOE computations.

    Raises
    ------
    ValueError
        If ``network`` is a string that does not correspond to a known module
        or the module does not define ``build``.
    TypeError
        If ``network`` is neither a pandapower network nor a recognised name.
    """

    if isinstance(network, pp.pandapowerNet):
        return network
    if isinstance(network, str):
        try:
            module = import_module(f"data.networks.{network}")
        except ModuleNotFoundError as exc:
            raise ValueError(f"Unknown network '{network}'") from exc
        if not hasattr(module, "build"):
            raise ValueError(f"Network '{network}' does not provide a build() function")
        return module.build()
    raise TypeError("network must be a pandapowerNet or a known network name")


def _ensure_nodes_exist(nodes: Iterable[int], graph_nodes: Sequence[int], label: str) -> None:
    missing = [node for node in nodes if node not in graph_nodes]
    if missing:
        raise ValueError(f"{label} {missing!r} are not present in the network")


def compute(
    network: Any,
    powerflow_mode: str,
    objective: str,
    *,
    operational_nodes: Iterable[int] | None = None,
    parent_nodes: Iterable[int] | None = None,
    children_nodes: Iterable[int] | None = None,
    alpha: float = 1.0,
    beta: float = 1.0,
    p_min: float = -1.0,
    p_max: float = 1.0,
    q_min: float | None = None,
    q_max: float | None = None,
    theta_min: float | None = None,
    theta_max: float | None = None,
    v_min: float | None = None,
    v_max: float | None = None,
    curtailment_limit: float | None = None,
    envelope_center_gap: float = 0.0,
    solver_options: Mapping[str, Any] | None = None,
    **options: Any,
) -> Dict[str, Any]:
    """Compute a Distribution Operation Envelope (DOE).

    Parameters
    ----------
    network:
        A :class:`pandapowerNet` instance or the name of a network module
        located in :mod:`data.networks`.
    powerflow_mode:
        Either ``"dc"`` or ``"ac"`` to select the power flow formulation.
    objective:
        Either ``"global_sum"`` (implemented) or ``"fairness"`` (placeholder).
    operational_nodes, parent_nodes, children_nodes:
        Collections describing the operational perimeter and boundary nodes.
    alpha, beta:
        Weights applied to the envelope objective.
    p_min, p_max:
        Bounds on the active power exchanged with parent nodes (p.u.).
    q_min, q_max:
        Bounds on reactive power exchanged with parent nodes (p.u., AC mode).
    theta_min, theta_max:
        Voltage angle bounds used in DC mode (radians).
    v_min, v_max:
        Voltage magnitude bounds used in AC mode (p.u.).
    curtailment_limit:
        Optional upper bound on the total curtailment budget (p.u.).
    envelope_center_gap:
        Initial value of the deviation from DSO information (p.u.).
    solver_options:
        Mapping forwarded to the underlying Pyomo solver configuration.
    options:
        Additional keyword arguments accepted for forward compatibility.
    """

    if curtailment_limit is None and "curt_budget" in options:
        curtailment_limit = float(options["curt_budget"])

    net = _load_network(network)

    if powerflow_mode not in POWERFLOW:
        raise ValueError(f"Unknown powerflow mode '{powerflow_mode}'")
    if objective not in OBJECTIVES:
        raise ValueError(f"Unknown objective '{objective}'")

    if objective == "global_sum" and (alpha is None or beta is None):
        raise ValueError("alpha and beta must be provided for the global_sum objective")

    full_graph = build_nx_from_pandapower(net)
    all_nodes = list(full_graph.nodes)

    operational_nodes = list(operational_nodes) if operational_nodes is not None else all_nodes
    _ensure_nodes_exist(operational_nodes, all_nodes, "Operational nodes")

    parent_nodes = list(parent_nodes) if parent_nodes is not None else []
    children_nodes = list(children_nodes) if children_nodes is not None else []

    _ensure_nodes_exist(parent_nodes, all_nodes, "Parent nodes")
    _ensure_nodes_exist(children_nodes, all_nodes, "Child nodes")

    operational_graph = op_graph(full_graph, set(operational_nodes))
    parents_in_graph = [n for n in parent_nodes if n in operational_graph.nodes]
    children_in_graph = [n for n in children_nodes if n in operational_graph.nodes]

    info_dso = compute_info_dso(
        G=full_graph,
        operational_nodes=operational_nodes,
        children_nodes=children_in_graph,
    )

    envelope_size = sum(abs(operational_graph.nodes[n].get("P", 0.0)) for n in operational_graph.nodes)

    model_params: Dict[str, Any] = {
        "alpha": float(alpha),
        "beta": float(beta),
        "p_min": float(p_min),
        "p_max": float(p_max),
        "q_min": q_min,
        "q_max": q_max,
        "theta_min": theta_min,
        "theta_max": theta_max,
        "v_min": v_min,
        "v_max": v_max,
        "info_dso": info_dso,
        "curtailment_limit": curtailment_limit,
    }

    objective_params = {
        "alpha": float(alpha),
        "beta": float(beta),
        "envelope_size": envelope_size,
        "curt_budget": float(curtailment_limit or 0.0),
        "envelope_center_gap": float(envelope_center_gap),
    }

    config = ModelConfiguration(
        graph=operational_graph,
        parent_nodes=parents_in_graph,
        child_nodes=children_in_graph,
        params=model_params,
        powerflow_mode=powerflow_mode,
    )

    result = solve_model(
        config,
        powerflow_builder=POWERFLOW[powerflow_mode],
        security_builder=security.build,
        objective_builder=OBJECTIVES[objective],
        objective_params=objective_params,
        solver_options=dict(solver_options or {}),
    )

    return {
        "status": result.get("status"),
        "objective_value": result.get("objective"),
        "model": result.get("model"),
        "graph": result.get("graph"),
        "envelopes": result.get("envelopes"),
        "curtailment_report": result.get("curtailment_report"),
        "diagnostics": result.get("diagnostics"),
    }
