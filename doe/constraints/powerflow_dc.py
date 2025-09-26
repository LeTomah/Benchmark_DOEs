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


def build(m: pyo.ConcreteModel, G: Any) -> None:
    """Add DC power flow variables and constraints to ``m``.

    Parameters
    ----------
    m:
        Pyomo model to augment.
    G:
        NetworkX graph describing the electrical network.
    """

    # nodes = list(G.nodes)
    # lines = list(G.edges)
    #
    # m.Nodes = pyo.Set(initialize=nodes)
    # m.Lines = pyo.Set(initialize=lines, dimen=2)
    #
    # m.theta = pyo.Var(m.Nodes, bounds=(-0.1, math.pi))
    # m.F = pyo.Var(m.Lines)

    def dc_flow_rule(m, u, v, vp, vv):
        # Vérifie d'abord la présence de ``b_pu`` avant toute conversion.
        b_attr = G[u][v].get("b_pu")
        if b_attr is None:
            edge_type = G[u][v].get("type")
            if edge_type == "line":
                raise KeyError(f"Edge {u}{v} missing 'b_pu' attribute")
            return pyo.Constraint.Skip
        b_pu = float(b_attr)
        return m.F[u, v, vp, vv] == (m.V_P[vv] **2) * b_pu * (
            m.theta[u, vp, vv] - m.theta[v, vp, vv]
        )

    m.DCPowerFlow = pyo.Constraint(m.Lines, m.VertP, m.VertV, rule=dc_flow_rule)

    def current_def_rule(m, u, v, vp, vv):
        """Link current, voltage and power flow in per-unit: I*V = F."""
        return math.sqrt(3) * m.I[u, v, vp, vv] * m.V_P[vv] == m.F[u, v, vp, vv]

    m.current_def = pyo.Constraint(m.Lines, m.VertP, m.VertV, rule=current_def_rule)

    def power_balance_rule(m, u, vp, vv):
        # Compute net flow into node n by summing over all lines (i,j) in m.Lines
        expr = sum(
            (m.F[i, j, vp, vv] if j == u else 0)
            - (m.F[i, j, vp, vv] if i == u else 0)
            for (i, j) in m.Lines
        )
        # If n is a parent node, subtract P_plus; otherwise use only E[n]
        if u in m.parents:
            return expr == m.E[u, vp, vv] - m.P_plus[u, vp, vv]
        if u in m.children:
            return expr == m.E[u, vp, vv] + m.P_minus[u, vp, vv]
        else:
            return expr == m.E[u, vp, vv]

    m.power_balance = pyo.Constraint(m.Nodes, m.VertP, m.VertV, rule=power_balance_rule)

    def add_curtailment_abs(m):
        """Define curtailment ``curt`` and its absolute value ``z``.

        Also enforce ``sum(z) <= curtailment_budget`` for each vertex pair.
        """

        def curt_def_rule(m, u, vp, vv):
            return m.curt[u, vp, vv] == m.P[u] - m.E[u, vp, vv]

        m.curt_def = pyo.Constraint(m.Nodes, m.VertP, m.VertV, rule=curt_def_rule)

        def abs_pos_rule(m, u, vp, vv):
            return m.z[u, vp, vv] >= m.curt[u, vp, vv]

        m.abs_E_pos = pyo.Constraint(m.Nodes, m.VertP, m.VertV, rule=abs_pos_rule)

        def abs_neg_rule(m, u, vp, vv):
            return m.z[u, vp, vv] >= -m.curt[u, vp, vv]

        m.abs_E_neg = pyo.Constraint(m.Nodes, m.VertP, m.VertV, rule=abs_neg_rule)

        def upper_bound_rule(m, vp, vv):
            return sum(m.z[u, vp, vv] for u in m.Nodes) <= m.curtailment_budget

        m.upper_bound = pyo.Constraint(m.VertP, m.VertV, rule=upper_bound_rule)
