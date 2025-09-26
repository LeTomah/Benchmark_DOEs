from __future__ import annotations

from typing import Any, Callable, Dict

import pyomo.environ as pyo
from doe.solvers.pyomo_backend_dc import create_pyo_env
from data.gurobi_config import get_wls_params

PowerflowBuilder = Callable[[pyo.ConcreteModel, Any], None]
ObjectiveBuilder = Callable[[pyo.ConcreteModel, Dict[str, Any]], None]
SecurityBuilder = Callable[[pyo.ConcreteModel, Any], None]


def solve_model(
    G: Any,
    powerflow_builder: PowerflowBuilder,
    security_builder: SecurityBuilder,
    objective_builder: ObjectiveBuilder,
    params: Dict[str, Any],
    options: Dict[str, Any],
) -> Dict[str, Any]:
    """Build and solve a DOE Pyomo model using scalar power limits."""

    # Older revisions reconstructed ``P_min``/``P_max`` from a ``p_limits``
    # mapping.  That normalisation step is kept below for documentation because
    # user interfaces used to expose per-node dictionaries.
    # p_limits_option = options.get("p_limits")
    # if isinstance(p_limits_option, dict):
    #     P_min = min(limits.get("pmin", 0.0) for limits in p_limits_option.values())
    #     P_max = max(limits.get("pmax", 0.0) for limits in p_limits_option.values())
    # else:
    #     P_min, P_max = p_limits_option

    P_min = float(options["P_min"])
    P_max = float(options["P_max"])

    m, operational_graph = create_pyo_env(
        graph=G,
        operational_nodes=options.get("operational_nodes"),
        parent_nodes=options.get("parent_nodes"),
        children_nodes=options.get("children_nodes"),
        info_DSO=options.get("info_DSO") or {},
        alpha=float(params.get("alpha", 1.0)),
        beta=float(params.get("beta", 1.0)),
        P_min=P_min,
        P_max=P_max,
    )

    powerflow_builder(m, operational_graph)
    security_builder(m, operational_graph)
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

    envelopes = {
        n: (
            operational_graph.nodes[n]["P"],
            operational_graph.nodes[n]["P"],
        )
        for n in operational_graph.nodes
    }

    return {
        "status": status,
        "objective": objective_val,
        "envelopes": envelopes,
        "curtailment_report": {},
        "diagnostics": {
            "solver": status,
        },
    }