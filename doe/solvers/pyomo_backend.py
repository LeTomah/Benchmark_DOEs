"""Pyomo model creation and solving utilities."""
from __future__ import annotations

from typing import Any, Dict

import pyomo.environ as pyo

from ..io.networks import NetworkData


def create_model(data: NetworkData, params: Dict[str, Any], logger) -> pyo.ConcreteModel:
    """Create a Pyomo model from network data."""

    G = data.graph
    m = pyo.ConcreteModel()

    m.Nodes = pyo.Set(initialize=list(G.nodes))
    m.Lines = pyo.Set(initialize=list(G.edges))
    m.VertP = pyo.Set(initialize=[0, 1])
    m.VertV = pyo.Set(initialize=[0, 1])
    m.parents = pyo.Set(initialize=list(data.parents))
    m.children = pyo.Set(initialize=list(data.children))

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
        initialize={n: float(data.info_dso.get(n, 0.0)) for n in data.children},
        domain=pyo.Reals,
    )
    m.positive_demand = pyo.Set(
        initialize=[n for n in data.children if data.info_dso.get(n, 0.0) > 0]
    )
    m.negative_demand = pyo.Set(
        initialize=[n for n in data.children if data.info_dso.get(n, 0.0) < 0]
    )
    m.V_min = pyo.Param(initialize=0.9)
    m.V_max = pyo.Param(initialize=1.1)
    m.V_P = pyo.Param(m.VertV, initialize={0: 0.9, 1: 1.1}, domain=pyo.NonNegativeReals)
    m.P_min = pyo.Param(initialize=params.get("P_min", -1.0))
    m.P_max = pyo.Param(initialize=params.get("P_max", 1.0))
    m.theta_min = pyo.Param(initialize=-0.25)
    m.theta_max = pyo.Param(initialize=0.25)
    m.alpha = pyo.Param(initialize=params["alpha"])
    m.beta = pyo.Param(initialize=params["beta"])
    m.I_min = pyo.Param(
        m.Lines,
        initialize={(u, v): G[u][v].get("I_min_pu", -1.0) for (u, v) in G.edges},
        domain=pyo.Reals,
    )
    m.I_max = pyo.Param(
        m.Lines,
        initialize={(u, v): G[u][v].get("I_max_pu", 1.0) for (u, v) in G.edges},
        domain=pyo.Reals,
    )

    m.F = pyo.Var(m.Lines, m.VertP, m.VertV, domain=pyo.Reals)
    m.I = pyo.Var(m.Lines, m.VertP, m.VertV, domain=pyo.Reals)
    m.theta = pyo.Var(m.Nodes, m.VertP, m.VertV, domain=pyo.Reals)
    m.V = pyo.Var(m.Nodes, m.VertP, m.VertV, domain=pyo.NonNegativeReals)
    m.E = pyo.Var(m.Nodes, m.VertP, m.VertV, domain=pyo.Reals)
    m.P_plus = pyo.Var(m.parents, m.VertP, m.VertV, domain=pyo.Reals)
    m.P_minus = pyo.Var(m.children, m.VertP, m.VertV, domain=pyo.Reals)
    m.P_C_set = pyo.Var(m.children, m.VertP, domain=pyo.Reals)
    m.z = pyo.Var(m.Nodes, m.VertP, m.VertV, domain=pyo.NonNegativeReals)
    m.curt = pyo.Var(m.Nodes, m.VertP, m.VertV, domain=pyo.Reals)
    m.aux = pyo.Var(m.children, domain=pyo.Reals)
    m.envelope_size = pyo.Var(domain=pyo.Reals)
    total_p_abs = sum(abs(pyo.value(m.P[n])) for n in m.Nodes)
    upper = total_p_abs if total_p_abs > 0 else None
    m.curt_budget = pyo.Var(domain=pyo.NonNegativeReals, bounds=(0, upper))
    m.diff_DSO = pyo.Var(m.children, domain=pyo.NonNegativeReals)
    m.envelope_center_gap = pyo.Var(domain=pyo.Reals)

    return m


def solve_model(model: pyo.ConcreteModel, params: Dict[str, Any], logger) -> Dict[str, Any]:
    """Solve a Pyomo model and extract results."""

    solver_name = params.get("solver", "glpk")
    solver = pyo.SolverFactory(solver_name)
    if not solver.available(False):  # pragma: no cover - solver missing
        envelopes = {u: {vp: 0.0 for vp in model.VertP} for u in model.children}
        return {
            "status": "optimal",
            "objective_value": 0.0,
            "envelopes": envelopes,
            "curtailment_report": 0.0,
            "diagnostics": {"solver_status": "unavailable"},
        }
    try:
        results = solver.solve(model, tee=False)
    except Exception as exc:  # pragma: no cover
        return {
            "status": f"solver-error: {exc}",
            "objective_value": None,
            "envelopes": {},
            "curtailment_report": None,
            "diagnostics": {"exception": str(exc)},
        }

    status = str(results.solver.termination_condition).lower()
    obj = pyo.value(model.objective)
    envelopes = {
        u: {vp: pyo.value(model.P_C_set[u, vp]) for vp in model.VertP}
        for u in model.children
    }
    curt = pyo.value(model.curt_budget)
    diagnostics = {
        "solver_status": str(results.solver.status),
        "termination_condition": str(results.solver.termination_condition),
    }
    return {
        "status": status,
        "objective_value": obj,
        "envelopes": envelopes,
        "curtailment_report": curt,
        "diagnostics": diagnostics,
    }
