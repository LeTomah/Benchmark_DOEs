"""Pyomo model construction and solving utilities.

This module centralises the creation of the optimisation model used to
compute Distribution Operation Envelopes (DOE).  All sets, parameters and
decision variables are defined here so that constraint builders can assume a
consistent interface.  The backend does not contain any business logic about
the DOE formulation itself: it simply orchestrates calls to the constraint
and objective modules.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Callable, Dict, Iterable, Mapping, Sequence

import pyomo.environ as pyo

from data.gurobi_config import get_wls_params

from ..constraints import common


PowerflowBuilder = Callable[[pyo.ConcreteModel, Any], None]
ObjectiveBuilder = Callable[[pyo.ConcreteModel, Dict[str, Any]], None]
SecurityBuilder = Callable[[pyo.ConcreteModel, Any], None]


@dataclass
class ModelConfiguration:
    """Container gathering all inputs required by the backend."""

    graph: Any
    parent_nodes: Sequence[Any]
    child_nodes: Sequence[Any]
    params: Mapping[str, Any]
    powerflow_mode: str


def _build_sets(
    model: pyo.ConcreteModel,
    nodes: Iterable[Any],
    lines: Iterable[tuple[Any, Any]],
    parents: Sequence[Any],
    children: Sequence[Any],
) -> None:
    """Create core sets describing the operational network."""

    model.Nodes = pyo.Set(initialize=list(nodes), doc="Operational nodes.")
    model.Lines = pyo.Set(
        initialize=list(lines), dimen=2, doc="Directed edges of the operational graph."
    )
    model.VertP = pyo.Set(initialize=[0, 1], doc="Indices of active power vertices.")
    model.VertV = pyo.Set(initialize=[0, 1], doc="Indices of voltage vertices.")
    model.ParentNodes = pyo.Set(
        initialize=list(parents), doc="Boundary nodes exchanging power with the upstream grid."
    )
    model.ChildNodes = pyo.Set(
        initialize=list(children), doc="Boundary nodes connected to external demand centres."
    )
    object.__setattr__(model, "parents", tuple(parents))
    object.__setattr__(model, "children", tuple(children))


def _initialise_node_parameters(
    model: pyo.ConcreteModel,
    graph: Any,
    params: Mapping[str, Any],
) -> None:
    """Populate parameters associated with nodes (P, Q, voltage limits)."""

    v_min_param = params.get("v_min")
    v_max_param = params.get("v_max")
    default_vmin = float(v_min_param) if v_min_param is not None else 0.9
    default_vmax = float(v_max_param) if v_max_param is not None else 1.1

    def node_active_power(n: Any) -> float:
        return float(graph.nodes[n].get("P", 0.0))

    def node_reactive_power(n: Any) -> float:
        return float(graph.nodes[n].get("Q", 0.0))

    def node_vmin(n: Any) -> float:
        graph_vmin = graph.nodes[n].get("V_min_pu")
        return default_vmin if graph_vmin is None else float(graph_vmin)

    def node_vmax(n: Any) -> float:
        graph_vmax = graph.nodes[n].get("V_max_pu")
        return default_vmax if graph_vmax is None else float(graph_vmax)

    model.P = pyo.Param(
        model.Nodes,
        initialize={n: node_active_power(n) for n in model.Nodes},
        domain=pyo.Reals,
        mutable=True,
        doc="Net active power demand at each node (p.u.).",
    )
    model.Q = pyo.Param(
        model.Nodes,
        initialize={n: node_reactive_power(n) for n in model.Nodes},
        domain=pyo.Reals,
        mutable=True,
        doc="Net reactive power demand at each node (p.u.).",
    )

    model.PositiveNodes = pyo.Set(
        initialize=[n for n in model.Nodes if node_active_power(n) > 0],
        doc="Nodes with positive net demand (loads).",
    )
    model.NegativeNodes = pyo.Set(
        initialize=[n for n in model.Nodes if node_active_power(n) < 0],
        doc="Nodes with negative net demand (generation).",
    )

    vmin_by_node = {n: node_vmin(n) for n in model.Nodes}
    vmax_by_node = {n: node_vmax(n) for n in model.Nodes}

    model.V_min = pyo.Param(
        model.Nodes,
        initialize=vmin_by_node,
        mutable=True,
        doc="Lower bound on voltage magnitude for every node (p.u.).",
    )
    model.V_max = pyo.Param(
        model.Nodes,
        initialize=vmax_by_node,
        mutable=True,
        doc="Upper bound on voltage magnitude for every node (p.u.).",
    )

    node_list = list(model.Nodes)
    ref_node = node_list[0] if node_list else None
    v_min_vertex = (
        float(v_min_param)
        if v_min_param is not None
        else (vmin_by_node[ref_node] if ref_node is not None else 0.9)
    )
    v_max_vertex = (
        float(v_max_param)
        if v_max_param is not None
        else (vmax_by_node[ref_node] if ref_node is not None else 1.1)
    )

    voltage_vertices = {0: v_min_vertex, 1: v_max_vertex}
    model.V_P = pyo.Param(
        model.VertV,
        initialize=voltage_vertices,
        domain=pyo.NonNegativeReals,
        doc="Voltage magnitude associated with each vertex (p.u.).",
    )


def _initialise_boundary_parameters(
    model: pyo.ConcreteModel,
    params: Mapping[str, Any],
) -> None:
    """Create parameters related to boundary exchanges and DSO information."""

    info_dso = params.get("info_dso", {})
    model.info_DSO_param = pyo.Param(
        model.ChildNodes,
        initialize={n: float(info_dso.get(n, 0.0)) for n in model.ChildNodes},
        domain=pyo.Reals,
        doc="External active power information provided by the DSO (p.u.).",
    )

    model.positive_demand = pyo.Set(
        initialize=[n for n in model.ChildNodes if float(info_dso.get(n, 0.0)) > 0],
        doc="Child nodes with positive demand according to the DSO.",
    )
    model.negative_demand = pyo.Set(
        initialize=[n for n in model.ChildNodes if float(info_dso.get(n, 0.0)) < 0],
        doc="Child nodes exporting power according to the DSO.",
    )

    model.P_min = pyo.Param(
        initialize=float(params.get("p_min", -1.0)),
        mutable=True,
        doc="Minimum active power exchanged at parent nodes (p.u.).",
    )
    model.P_max = pyo.Param(
        initialize=float(params.get("p_max", 1.0)),
        mutable=True,
        doc="Maximum active power exchanged at parent nodes (p.u.).",
    )

    q_min = params.get("q_min")
    q_max = params.get("q_max")
    model.Q_min = float(q_min) if q_min is not None else None
    model.Q_max = float(q_max) if q_max is not None else None

    model.alpha = pyo.Param(
        initialize=float(params.get("alpha", 1.0)),
        mutable=True,
        doc="Objective weight associated with curtailment.",
    )
    model.beta = pyo.Param(
        initialize=float(params.get("beta", 1.0)),
        mutable=True,
        doc="Objective weight associated with DSO deviation.",
    )

    theta_min = params.get("theta_min")
    theta_max = params.get("theta_max")
    model.theta_min = float(theta_min) if theta_min is not None else -0.25
    model.theta_max = float(theta_max) if theta_max is not None else 0.25

    curtailment_limit = params.get("curtailment_limit")
    model.curtailment_limit = (
        float(curtailment_limit) if curtailment_limit is not None else None
    )


def _initialise_line_parameters(
    model: pyo.ConcreteModel,
    graph: Any,
) -> None:
    """Populate line-related parameters such as current and impedances."""

    def current_min(edge: tuple[Any, Any]) -> float:
        return float(graph[edge[0]][edge[1]].get("I_min_pu", -math.inf))

    def current_max(edge: tuple[Any, Any]) -> float:
        return float(graph[edge[0]][edge[1]].get("I_max_pu", math.inf))

    model.I_min = pyo.Param(
        model.Lines,
        initialize={edge: current_min(edge) for edge in model.Lines},
        mutable=True,
        doc="Minimum current on each line (p.u.).",
    )
    model.I_max = pyo.Param(
        model.Lines,
        initialize={edge: current_max(edge) for edge in model.Lines},
        mutable=True,
        doc="Maximum current on each line (p.u.).",
    )

    model.R = pyo.Param(
        model.Lines,
        initialize={
            edge: float(graph[edge[0]][edge[1]].get("R", 0.0)) for edge in model.Lines
        },
        mutable=True,
        doc="Per-unit resistance of each line.",
    )
    model.X = pyo.Param(
        model.Lines,
        initialize={
            edge: float(graph[edge[0]][edge[1]].get("X", 0.0)) for edge in model.Lines
        },
        mutable=True,
        doc="Per-unit reactance of each line.",
    )
    model.Z2 = pyo.Param(
        model.Lines,
        initialize={
            edge: float(graph[edge[0]][edge[1]].get("R", 0.0)) ** 2
            + float(graph[edge[0]][edge[1]].get("X", 0.0)) ** 2
            for edge in model.Lines
        },
        mutable=True,
        doc="Squared magnitude of line impedance.",
    )


def _build_variables(model: pyo.ConcreteModel, powerflow_mode: str) -> None:
    """Create decision variables shared by the DOE models."""

    model.F = pyo.Var(model.Lines, model.VertP, model.VertV, domain=pyo.Reals)
    model.I = pyo.Var(model.Lines, model.VertP, model.VertV, domain=pyo.Reals)
    model.theta = pyo.Var(model.Nodes, model.VertP, model.VertV, domain=pyo.Reals)
    model.V = pyo.Var(model.Nodes, model.VertP, model.VertV, domain=pyo.NonNegativeReals)

    model.P_prime = pyo.Var(
        model.Nodes, model.VertP, model.VertV, domain=pyo.Reals, doc="Net active power after optimisation (p.u.)."
    )
    model.P_plus = pyo.Var(
        model.ParentNodes,
        model.VertP,
        model.VertV,
        domain=pyo.Reals,
        doc="Active power imported from the upstream grid (p.u.).",
    )
    model.P_minus = pyo.Var(
        model.ChildNodes,
        model.VertP,
        model.VertV,
        domain=pyo.Reals,
        doc="Active power exported to downstream consumers (p.u.).",
    )

    model.P_C_set = pyo.Var(
        model.ChildNodes,
        model.VertP,
        domain=pyo.Reals,
        doc="Bounds defining the power envelope for each child node (p.u.).",
    )
    model.z = pyo.Var(
        model.Nodes, model.VertP, model.VertV, domain=pyo.NonNegativeReals
    )
    model.curt = pyo.Var(
        model.Nodes, model.VertP, model.VertV, domain=pyo.Reals, doc="Curtailment applied at each node (p.u.)."
    )

    model.aux = pyo.Var(model.ChildNodes, domain=pyo.Reals)
    model.diff_DSO = pyo.Var(model.ChildNodes, domain=pyo.NonNegativeReals)
    model.envelope_volume = pyo.Var(domain=pyo.NonNegativeReals)

    total_p_abs = sum(abs(pyo.value(model.P[n])) for n in model.Nodes)
    upper = model.curtailment_limit if model.curtailment_limit is not None else total_p_abs
    model.curtailment_budget = pyo.Var(
        domain=pyo.NonNegativeReals,
        bounds=(0.0, upper if upper is not None else total_p_abs),
    )
    model.envelope_center_gap = pyo.Var(domain=pyo.NonNegativeReals)

    if powerflow_mode == "ac":
        model.G = pyo.Var(
            model.Lines, model.VertP, model.VertV, domain=pyo.Reals, doc="Reactive power flow (p.u.)."
        )
        model.I_squared = pyo.Var(
            model.Lines,
            model.VertP,
            model.VertV,
            domain=pyo.NonNegativeReals,
            doc="Squared current magnitude on each line.",
        )
        model.V_squared = pyo.Var(
            model.Nodes,
            model.VertP,
            model.VertV,
            domain=pyo.NonNegativeReals,
            doc="Squared voltage magnitude at each node.",
        )
        model.Q_prime = pyo.Var(
            model.Nodes, model.VertP, model.VertV, domain=pyo.Reals, doc="Net reactive power after optimisation (p.u.)."
        )
        model.Q_plus = pyo.Var(
            model.ParentNodes,
            model.VertP,
            model.VertV,
            domain=pyo.Reals,
            doc="Reactive power imported from the upstream grid (p.u.).",
        )
        model.Q_minus = pyo.Var(
            model.ChildNodes,
            model.VertP,
            model.VertV,
            domain=pyo.Reals,
            doc="Reactive power exported to downstream consumers (p.u.).",
        )
    else:
        # Ensure attributes exist even in DC mode for compatibility with plotting helpers
        model.G = None
        model.I_squared = None
        model.V_squared = None
        model.Q_prime = None
        model.Q_plus = None
        model.Q_minus = None


def _build_model_structure(model: pyo.ConcreteModel, config: ModelConfiguration) -> None:
    """Populate the Pyomo model with sets, parameters and variables."""

    graph = config.graph
    nodes = list(graph.nodes)
    lines = list(graph.edges)

    _build_sets(model, nodes, lines, config.parent_nodes, config.child_nodes)
    _initialise_node_parameters(model, graph, config.params)
    _initialise_boundary_parameters(model, config.params)
    _initialise_line_parameters(model, graph)
    _build_variables(model, config.powerflow_mode)


def _select_solver(options: Mapping[str, Any] | None) -> pyo.SolverFactory:
    """Return a configured Pyomo solver, falling back to open-source engines."""

    options = options or {}
    solver_name = options.get("solver", "gurobi")
    solver_io = options.get("solver_io")

    def try_create(name: str, solver_io: str | None = None) -> pyo.SolverFactory | None:
        try:
            solver = pyo.SolverFactory(name, solver_io=solver_io)
            available = solver.available(False)
        except Exception:  # pragma: no cover - defensive guard
            return None
        return solver if available else None

    solver = try_create(solver_name, solver_io)
    if solver is None and solver_name != "gurobi":
        raise RuntimeError(f"Solver '{solver_name}' is not available in this environment")

    if solver is None:
        # Try the default Gurobi configuration using a WLS token if available
        try:
            env_params = get_wls_params()
        except Exception:  # pragma: no cover - fallback when config missing
            env_params = {}
        solver = try_create("gurobi", solver_io)
        if solver is not None and env_params:
            solver.options.update(env_params)

    if solver is None:
        for candidate in ("appsi_highs", "glpk", "cbc"):
            solver = try_create(candidate)
            if solver is not None:
                break

    if solver is None:
        raise RuntimeError("No suitable optimisation solver is available")

    solver.options.update(options.get("solver_options", {}))
    return solver


def solve_model(
    config: ModelConfiguration,
    powerflow_builder: PowerflowBuilder,
    security_builder: SecurityBuilder,
    objective_builder: ObjectiveBuilder,
    objective_params: Dict[str, Any],
    solver_options: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Build and solve a DOE Pyomo model."""

    model = pyo.ConcreteModel()
    _build_model_structure(model, config)

    # Attach constraints and objectives provided by external builders
    common.build(model, config.graph)
    powerflow_builder(model, config.graph)
    security_builder(model, config.graph)
    objective_builder(model, objective_params)

    termination = None
    solver_status = "unknown"
    objective_val: float | None = None

    try:
        solver = _select_solver(solver_options)
        results = solver.solve(model, tee=bool((solver_options or {}).get("tee", False)))
        termination = results.solver.termination_condition
        solver_status = str(results.solver.status)
        if hasattr(model, "objective"):
            objective_val = float(pyo.value(model.objective))
    except Exception as exc:  # pragma: no cover - error path when solver missing
        solver_status = f"solver_error: {exc}"
        termination = None

    envelopes: Dict[Any, tuple[float, float]] = {}
    for child in model.ChildNodes:
        try:
            high = float(pyo.value(model.P_C_set[child, 0]))
            low = float(pyo.value(model.P_C_set[child, 1]))
            envelopes[child] = (low, high)
        except Exception:  # pragma: no cover - model may be infeasible
            envelopes[child] = (float("nan"), float("nan"))

    result = {
        "status": solver_status,
        "termination_condition": str(termination) if termination is not None else None,
        "objective": objective_val,
        "model": model,
        "graph": config.graph,
        "envelopes": envelopes,
        "curtailment_report": {},
        "diagnostics": {
            "solver": solver_status,
            "termination_condition": str(termination) if termination is not None else None,
        },
    }

    return result

