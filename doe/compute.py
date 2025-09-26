"""High level interface for computing DOEs."""

from __future__ import annotations

from importlib import import_module
from typing import Any, Dict, Iterable, Tuple

import gurobipy as gp
import pandapower as pp
import pyomo.environ as pyo

from data.gurobi_config import get_wls_params

from .constraints import powerflow_ac, powerflow_dc, security
from .objectives import fairness, global_sum
from .solvers.pyomo_backend_ac import create_pyo_env as create_ac_env
from .solvers.pyomo_backend_dc import create_pyo_env as create_dc_env
from .utils import graph as graph_utils

POWERFLOW = {"dc": powerflow_dc.build, "ac": powerflow_ac.build}
OBJECTIVES = {"global_sum": global_sum.build, "fairness": fairness.build}
ENV_BUILDERS = {"dc": create_dc_env, "ac": create_ac_env}


def _load_network(network: Any) -> pp.pandapowerNet:
    """Return a :class:`pandapowerNet` built from a name or existing object."""

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


def _normalise_key(name: str | None) -> str | None:
    """Normalise user provided identifiers (case and spacing)."""

    if name is None:
        return None
    return name.strip().lower().replace(" ", "_")


def _extract_arguments(args: Tuple[Any, ...], options: Dict[str, Any]) -> Tuple[Any, str, str]:
    """Resolve positional/keyword arguments into ``(network, mode, objective)``."""

    network = options.pop("network", None)
    powerflow_mode = options.pop("powerflow_mode", None)
    objective = options.pop("objective", None)

    if len(args) == 3:
        network, powerflow_mode, objective = args
    elif len(args) == 2:
        powerflow_mode, objective = args
    elif len(args) == 1:
        network = args[0]
    elif len(args) > 3:
        raise TypeError("compute() accepts at most three positional arguments")

    powerflow_mode = _normalise_key(powerflow_mode)
    objective = _normalise_key(objective)

    if network is None:
        raise ValueError("'network' argument is required")
    if not powerflow_mode:
        raise ValueError("'powerflow_mode' argument is required")
    if not objective:
        raise ValueError("'objective' argument is required")

    return network, powerflow_mode, objective


def _build_solver() -> pyo.SolverFactory:
    """Instantiate a Gurobi solver with optional WLS credentials."""

    params = get_wls_params()
    try:
        env = gp.Env(params=params) if params else gp.Env()
        return pyo.SolverFactory("gurobi", env=env)
    except gp.GurobiError:
        return pyo.SolverFactory("gurobi")


def _prepare_objective_params(
    operational_graph: Any,
    alpha: float,
    beta: float,
    options: Dict[str, Any],
) -> Dict[str, float]:
    """Build the dictionary expected by objective builders."""

    envelope_size = options.get("envelope_size")
    if envelope_size is None:
        envelope_size = sum(abs(operational_graph.nodes[n].get("P", 0.0)) for n in operational_graph.nodes)

    curt_budget = float(options.get("curt_budget", 0.0))
    center_gap = float(options.get("envelope_center_gap", 0.0))

    return {
        "alpha": float(alpha),
        "beta": float(beta),
        "envelope_size": float(envelope_size),
        "curt_budget": curt_budget,
        "envelope_center_gap": center_gap,
    }


def _solve_model(
    model: pyo.ConcreteModel,
    graph: Any,
    powerflow_builder,
    objective_builder,
    alpha: float,
    beta: float,
    options: Dict[str, Any],
) -> Dict[str, Any]:
    """Attach builders, solve the model and extract envelopes."""

    powerflow_builder(model, graph)
    security.build(model, graph)

    params = _prepare_objective_params(graph, alpha, beta, options)
    objective_builder(model, params)

    solver = _build_solver()
    results = solver.solve(model, tee=bool(options.get("tee", False)))

    solver_status = getattr(results, "solver", None)
    if solver_status is not None:
        status = str(getattr(solver_status, "status", "unknown"))
    else:
        status = "unknown"

    objective_value = None
    if hasattr(model, "objective"):
        objective_value = float(pyo.value(model.objective))

    envelopes: Dict[Any, Tuple[float, float]] = {}
    if hasattr(model, "P_C_set") and hasattr(model, "children"):
        vertices = list(model.VertP) if hasattr(model, "VertP") else [0]
        for node in model.children:
            values = [float(pyo.value(model.P_C_set[node, v])) for v in vertices]
            if values:
                envelopes[node] = (min(values), max(values))

    if not envelopes and hasattr(model, "parents"):
        pmin = float(getattr(model, "P_min", -1.0))
        pmax = float(getattr(model, "P_max", 1.0))
        envelopes = {node: (pmin, pmax) for node in model.parents}

    return {
        "status": status,
        "objective": objective_value,
        "envelopes": envelopes,
        "model": model,
        "graph": graph,
    }


def compute(*args: Any, **options: Any) -> Dict[str, Any]:
    """Compute a Distribution Operation Envelope (DOE)."""

    options = dict(options)
    network, powerflow_mode, objective = _extract_arguments(args, options)

    if powerflow_mode not in POWERFLOW:
        raise ValueError(f"Unknown powerflow mode '{powerflow_mode}'")
    if objective not in OBJECTIVES:
        raise ValueError(f"Unknown objective '{objective}'")

    if objective == "global_sum":
        if "alpha" not in options or "beta" not in options:
            raise ValueError("alpha and beta must be provided for the global_sum objective")
    alpha = float(options.get("alpha", 1.0))
    beta = float(options.get("beta", 1.0))

    net = _load_network(network)
    full_graph = graph_utils.create_graph(net)

    operational_nodes = options.get("operational_nodes")
    if operational_nodes is None:
        operational_nodes = tuple(full_graph.nodes)

    children_nodes: Iterable[int] | None = options.get("children_nodes")
    parent_nodes: Iterable[int] | None = options.get("parent_nodes")

    info_dso = options.get("info_DSO")
    if info_dso is None and children_nodes:
        info_dso = graph_utils.compute_info_P(
            G=full_graph,
            operational_nodes=operational_nodes,
            children_nodes=children_nodes,
        )

    env_kwargs = {
        "graph": full_graph,
        "operational_nodes": operational_nodes,
        "parent_nodes": parent_nodes,
        "children_nodes": children_nodes,
        "info_DSO": info_dso,
        "alpha": alpha,
        "beta": beta,
        "P_min": float(options.get("P_min", -1.0)),
        "P_max": float(options.get("P_max", 1.0)),
    }
    if powerflow_mode == "ac":
        env_kwargs.update(
            {
                "Q_min": float(options.get("Q_min", -1.0)),
                "Q_max": float(options.get("Q_max", 1.0)),
            }
        )

    model, operational_graph = ENV_BUILDERS[powerflow_mode](**env_kwargs)

    result = _solve_model(
        model=model,
        graph=operational_graph,
        powerflow_builder=POWERFLOW[powerflow_mode],
        objective_builder=OBJECTIVES[objective],
        alpha=alpha,
        beta=beta,
        options=options,
    )

    envelopes = result.get("envelopes", {})
    if envelopes:
        print("Enveloppes de puissance (p.u.) :")
        for node, (emin, emax) in envelopes.items():
            print(f" - Noeud {node}: [{emin:.4f}, {emax:.4f}]")

    return {
        "status": result.get("status"),
        "objective_value": result.get("objective"),
        "envelopes": envelopes,
        "curtailment_report": {},
        "diagnostics": {"solver": result.get("status")},
    }
