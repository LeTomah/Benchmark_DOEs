"""DC power flow constraints."""
from __future__ import annotations

import math
import pyomo.environ as pyo


def _add_dc_flow_constraints(m, G):
    """Linearised power flow equations.

    Assumes small-angle differences and unit voltage magnitude.
    """

    def dc_power_flow_rule(m, u, v, vp, vv):
        b_pu = G[u][v].get("b_pu")
        if b_pu is None:
            edge_type = G[u][v].get("type")
            if edge_type == "line":
                raise KeyError(f"Edge ({u},{v}) missing 'b_pu' attribute")
            return pyo.Constraint.Skip
        return m.F[u, v, vp, vv] == (m.V_P[vv] ** 2) * b_pu * (
            m.theta[u, vp, vv] - m.theta[v, vp, vv]
        )

    m.DCFlow = pyo.Constraint(m.Lines, m.VertP, m.VertV, rule=dc_power_flow_rule)


def _add_current_definition(m):
    """Link current, voltage and power flow in per-unit."""

    def current_def_rule(m, u, v, vp, vv):
        return math.sqrt(3) * m.I[u, v, vp, vv] * m.V_P[vv] == m.F[u, v, vp, vv]

    m.current_def = pyo.Constraint(m.Lines, m.VertP, m.VertV, rule=current_def_rule)


def _add_power_balance(m):
    """Enforce active power balance at each node."""

    def power_balance_rule(m, u, vp, vv):
        expr = sum(
            (m.F[i, j, vp, vv] if j == u else 0)
            - (m.F[i, j, vp, vv] if i == u else 0)
            for (i, j) in m.Lines
        )
        if u in m.parents:
            return expr == m.E[u, vp, vv] - m.P_plus[u, vp, vv]
        if u in m.children:
            return expr == m.E[u, vp, vv] + m.P_minus[u, vp, vv]
        return expr == m.E[u, vp, vv]

    m.power_balance = pyo.Constraint(m.Nodes, m.VertP, m.VertV, rule=power_balance_rule)


def build(model, data, params, logger):
    """Attach DC power flow constraints to ``model``."""

    _add_dc_flow_constraints(model, data.graph)
    _add_current_definition(model)
    _add_power_balance(model)
