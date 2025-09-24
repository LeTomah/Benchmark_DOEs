"""Security constraints for the DOE optimisation models."""

from __future__ import annotations

from typing import Any

import pyomo.environ as pyo


def build(model: pyo.ConcreteModel, graph: Any) -> None:
    """Attach both DC and AC security constraints to ``model``."""

    build_dc(model, graph)
    build_ac(model, graph)


def build_dc(model: pyo.ConcreteModel, graph: Any) -> None:
    """Add DC security constraints to ``model``."""

    if not hasattr(model, "Lines") or not hasattr(model, "I"):
        return

    def line_limit_rule(m, u, v, vp, vv):
        return pyo.inequality(m.I_min[u, v], m.I[u, v, vp, vv], m.I_max[u, v])

    model.LineLimits = pyo.Constraint(
        model.Lines, model.VertP, model.VertV, rule=line_limit_rule
    )

    def phase_constr_rule(m, node, vp, vv):
        return pyo.inequality(m.theta_min, m.theta[node, vp, vv], m.theta_max)

    model.phase_constraints = pyo.Constraint(
        model.Nodes, model.VertP, model.VertV, rule=phase_constr_rule
    )


def build_ac(model: pyo.ConcreteModel, graph: Any) -> None:
    """Add AC security constraints to ``model``."""

    if getattr(model, "I_squared", None) is None:
        return

    default_vmin = 0.9
    default_vmax = 1.1

    v_min = {}
    v_max = {}
    for node in model.Nodes:
        raw_min = graph.nodes[node].get("V_min_pu")
        raw_max = graph.nodes[node].get("V_max_pu")
        v_min[node] = float(raw_min) if raw_min is not None else default_vmin
        v_max[node] = float(raw_max) if raw_max is not None else default_vmax

    model.V_min_squared = pyo.Param(
        model.Nodes,
        initialize={node: v_min[node] ** 2 for node in model.Nodes},
        mutable=True,
    )
    model.V_max_squared = pyo.Param(
        model.Nodes,
        initialize={node: v_max[node] ** 2 for node in model.Nodes},
        mutable=True,
    )

    def voltage_limit_rule(m, node, vp, vv):
        return pyo.inequality(
            m.V_min_squared[node], m.V_squared[node, vp, vv], m.V_max_squared[node]
        )

    model.VoltageLimits = pyo.Constraint(
        model.Nodes, model.VertP, model.VertV, rule=voltage_limit_rule
    )

    default_imax = 1e3
    i_max_init = {}
    for (u, v) in model.Lines:
        data = graph[u][v]
        imax = data.get("I_max_pu", default_imax)
        if imax is None:
            imax = default_imax
        imax_val = max(float(imax), 0.0)
        i_max_init[(u, v)] = imax_val ** 2

    model.I_squared_max = pyo.Param(
        model.Lines, initialize=i_max_init, mutable=True
    )

    def current_limit_rule(m, u, v, vp, vv):
        return pyo.inequality(0.0, m.I_squared[u, v, vp, vv], m.I_squared_max[u, v])

    model.CurrentLimits = pyo.Constraint(
        model.Lines, model.VertP, model.VertV, rule=current_limit_rule
    )
