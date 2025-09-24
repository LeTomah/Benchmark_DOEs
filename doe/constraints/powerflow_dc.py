"""DC power flow constraints used in DOE models.

The DC formulation assumes flat voltage profile (|V|≈1 p.u.) and small
angle differences. Power flows on each line ``F[u,v]`` are linearised as
``b_pu * (theta[u] - theta[v])`` where ``b_pu`` is the per-unit
susceptance. Nodal active power balance is enforced for every bus.
"""

from __future__ import annotations

import math
from typing import Any

import pyomo.environ as pyo


def build(model: pyo.ConcreteModel, graph: Any) -> None:
    """Add DC power flow constraints to ``model``."""

    if not hasattr(model, "Lines"):
        return

    def susceptance(edge: tuple[Any, Any]) -> float | None:
        return graph[edge[0]][edge[1]].get("b_pu")

    def dc_flow_rule(m, u, v, vp, vv):
        b_pu = susceptance((u, v))
        if b_pu is None:
            return pyo.Constraint.Skip
        return m.F[u, v, vp, vv] == (m.V_P[vv] ** 2) * float(b_pu) * (
            m.theta[u, vp, vv] - m.theta[v, vp, vv]
        )

    model.DCPowerFlow = pyo.Constraint(
        model.Lines, model.VertP, model.VertV, rule=dc_flow_rule
    )

    def current_def_rule(m, u, v, vp, vv):
        voltage = float(pyo.value(m.V_P[vv]))
        return math.sqrt(3) * m.I[u, v, vp, vv] * voltage == m.F[u, v, vp, vv]

    model.current_def = pyo.Constraint(
        model.Lines, model.VertP, model.VertV, rule=current_def_rule
    )

    parent_nodes = set(getattr(model, "ParentNodes", getattr(model, "parents", [])))
    child_nodes = set(getattr(model, "ChildNodes", getattr(model, "children", [])))

    def power_balance_rule(m, node, vp, vv):
        incoming = sum(m.F[i, j, vp, vv] for (i, j) in m.Lines if j == node)
        outgoing = sum(m.F[i, j, vp, vv] for (i, j) in m.Lines if i == node)
        balance = incoming - outgoing
        if node in parent_nodes:
            return balance == m.P_prime[node, vp, vv] - m.P_plus[node, vp, vv]
        if node in child_nodes:
            return balance == m.P_prime[node, vp, vv] + m.P_minus[node, vp, vv]
        return balance == m.P_prime[node, vp, vv]

    model.power_balance = pyo.Constraint(
        model.Nodes, model.VertP, model.VertV, rule=power_balance_rule
    )
