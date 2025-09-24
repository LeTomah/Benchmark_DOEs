"""Pyomo model construction and solving utilities."""

from __future__ import annotations

from typing import Any, Callable, Dict

import pyomo.environ as pyo

from data.gurobi_config import get_wls_params


PowerflowBuilder = Callable[[pyo.ConcreteModel, Any], None]
ObjectiveBuilder = Callable[[pyo.ConcreteModel, Dict[str, Any]], None]
SecurityBuilder = Callable[[pyo.ConcreteModel, Any], None]


def build_sets(m: pyo.ConcreteModel, G: Any, parent_nodes, children_nodes):
    """Initialise core Pyomo sets shared by all builders."""

    m.Nodes = pyo.Set(initialize=list(G.nodes))
    m.Lines = pyo.Set(initialize=list(G.edges))
    m.VertP = pyo.Set(initialize=[0, 1])
    m.VertV = pyo.Set(initialize=[0, 1])
    m.parents = pyo.Set(initialize=parent_nodes)
    m.children = pyo.Set(initialize=children_nodes)

def build_params(m: pyo.ConcreteModel,
                 G: Any, nodes: list[Any],
                 lines: list[tuple[Any, Any]],
                 params: Dict[str, Any],
                 options: Dict[str, Any],
                 children: list[Any],
                 ) -> None:

    m.P = pyo.Param(
        m.Nodes,
        initialize={n: G.nodes[n].get("P", 0.0) for n in G.nodes},
        domain=pyo.Reals,
        mutable=True,
    )
    m.PositiveNodes = pyo.Set(
        initialize=[n for n in m.Nodes if G.nodes[n].get("P", 0.0) > 0]
    )
    m.NegativeNodes = pyo.Set(
        initialize=[n for n in m.Nodes if G.nodes[n].get("P", 0.0) < 0]
    )
    m.info_DSO_param = pyo.Param(
        m.children,
        initialize={n: float(info_DSO.get(n, 0.0)) for n in m.children},
        domain=pyo.Reals,
    )
    m.positive_demand = pyo.Set(
        initialize=[n for n in m.children if pyo.value(m.info_DSO_param[n]) > 0]
    )
    m.negative_demand = pyo.Set(
        initialize=[n for n in m.children if pyo.value(m.info_DSO_param[n]) < 0]
    )
    m.V_min = pyo.Param(initialize=0.9)
    m.V_max = pyo.Param(initialize=1.1)
    m.V_P = pyo.Param(m.VertV, initialize={0: 0.9, 1: 1.1}, domain=pyo.NonNegativeReals)
    m.P_min = pyo.Param(initialize=P_min)
    m.P_max = pyo.Param(initialize=P_max)
    m.theta_min = pyo.Param(initialize=-0.25)
    m.theta_max = pyo.Param(initialize=0.25)
    m.alpha = pyo.Param(initialize=alpha)
    m.beta = pyo.Param(initialize=beta)
    m.I_min = pyo.Param(
        m.Lines,
        initialize={
            (u, v): G[u][v].get("I_min_pu", -1) for (u, v) in m.Lines
        },
        domain=pyo.Reals,
    )
    m.I_max = pyo.Param(
        m.Lines,
        initialize={
            (u, v): G[u][v].get("I_max_pu", 1) for (u, v) in m.Lines
        },
        domain=pyo.Reals,
    )

def build_variables(m: pyo.ConcreteModel) -> None:
    """Create the decision variables used across the DOE models."""
    m.F = pyo.Var(m.Lines, m.VertP, m.VertV, domain=pyo.Reals)
    m.I = pyo.Var(m.Lines, m.VertP, m.VertV, domain=pyo.Reals)
    m.theta = pyo.Var(m.Nodes, m.VertP, m.VertV, domain=pyo.Reals)
    m.V = pyo.Var(m.Nodes, m.VertP, m.VertV, domain=pyo.NonNegativeReals)
    m.E = pyo.Var(m.Nodes, m.VertP, m.VertV, domain=pyo.Reals)
    m.P_plus = pyo.Var(m.parents, m.VertP, m.VertV, domain=pyo.Reals)
    # Bound child injections to realistic per-unit range
    m.P_minus = pyo.Var(
        m.children, m.VertP, m.VertV, domain=pyo.Reals
    )
    m.P_C_set = pyo.Var(m.children, m.VertP, domain=pyo.Reals)
    m.z = pyo.Var(m.Nodes, m.VertP, m.VertV, domain=pyo.NonNegativeReals)
    m.curt = pyo.Var(m.Nodes, m.VertP, m.VertV, domain=pyo.Reals)
    m.aux = pyo.Var(m.children, domain=pyo.Reals)
    m.envelope_volume = pyo.Var(domain=pyo.Reals)
    #Curtailment budget
    total_p_abs = sum(abs(pyo.value(m.P[n])) for n in m.Nodes)
    m.curtailment_budget = pyo.Var(domain=pyo.NonNegativeReals, bounds=(-total_p_abs, total_p_abs))

    m.diff_DSO = pyo.Var(m.children, domain=pyo.NonNegativeReals)
    m.envelope_center_gap = pyo.Var(domain=pyo.Reals)

def solve_model(
    G: Any,
    powerflow_builder: PowerflowBuilder,
    security_builder: SecurityBuilder,
    objective_builder: ObjectiveBuilder,
    params: Dict[str, Any],
    options: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Build and solve a DOE Pyomo m.

    Parameters
    ----------
    graph:
        NetworkX graph of the network.
    powerflow_builder / security_builder / objective_builder:
        Callbacks adding variables, constraints and objective to the m.
    params:
        Additional parameters passed to the objective builder.
    options:
        Currently unused placeholder for solver options.
    """

    m = pyo.ConcreteModel()

    nodes, lines, _parents, children = build_sets(m, G)
    build_params(m, G, nodes, lines, params, children)
    build_variables(m)

    powerflow_builder(m, G)
    security_builder(m, G)
    objective_builder(m, params)

    try:
        env_params = get_wls_params()
        solver = pyo.SolverFactory("gurobi", solver_io="python")
        if env_params:
            solver.options.update(env_params)
        result = solver.solve(m, tee=False)
        status = str(result.solver.termination_condition)
    except Exception:  # pragma: no cover - fallback when solver missing
        result = None
        status = "not_solved"

    objective_val = float(pyo.value(m.objective))

    envelopes = {n: (G.nodes[n]["P"], G.nodes[n]["P"]) for n in G.nodes}

    return {
        "status": status,
        "objective": objective_val,
        "envelopes": envelopes,
        "curtailment_report": {},
        "diagnostics": {
            "solver": status,
        },
    }
