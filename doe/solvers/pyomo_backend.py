"""Pyomo model construction and solving utilities."""

from __future__ import annotations

from typing import Any, Callable, Dict

import pyomo.environ as pyo

from data.gurobi_config import get_wls_params


PowerflowBuilder = Callable[[pyo.ConcreteModel, Any], None]
ObjectiveBuilder = Callable[[pyo.ConcreteModel, Dict[str, Any]], None]
SecurityBuilder = Callable[[pyo.ConcreteModel, Any], None]


def solve_model(
    graph: Any,
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
    powerflow_builder(m, graph)
    security_builder(m, graph)
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

    envelopes = {n: (graph.nodes[n]["P"], graph.nodes[n]["P"]) for n in graph.nodes}

    return {
        "status": status,
        "objective": objective_val,
        "envelopes": envelopes,
        "curtailment_report": {},
        "diagnostics": {
            "solver": status,
        },
    }
