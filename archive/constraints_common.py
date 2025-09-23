"""Shared Pyomo constraints for OPF and DOE models.

Angles are expressed in radians. Power sign convention: P < 0 for
production, P > 0 for consumption. The underlying graph is
undirected but each edge (u, v) appears only once with the canonical
orientation given by NetworkX; power flows ``F[u,v]`` follow this
orientation.
"""

import pyomo.environ as pyo
import math


def add_dc_flow_constraints(m, G):
    """Add DC power flow constraints F[u,v] = b_pu*(theta[u]-theta[v]).

    Only applies to lines. For edges missing ``b_pu`` an explicit
    error is raised. Transformers (``b_pu`` is ``None``) are skipped.
    """

    def dc_power_flow_rule(m, u, v, vp, vv):
        b_pu = G[u][v].get("b_pu")
        if b_pu is None:
            edge_type = G[u][v].get("type")
            if edge_type == "line":
                raise KeyError(f"Edge ({u},{v}) missing 'b_pu' attribute")
            return pyo.Constraint.Skip
        return m.F[u, v, vp, vv] == (m.V_P[vv] **2) * b_pu * (
            m.theta[u, vp, vv] - m.theta[v, vp, vv]
        )

    m.DCFlow = pyo.Constraint(m.Lines, m.VertP, m.VertV, rule=dc_power_flow_rule)


def add_current_bounds(m):
    """Bound the current magnitude using pre-computed limits."""

    def current_bounds_rule(m, u, v, vp, vv):
        return pyo.inequality(m.I_min[u, v], m.I[u, v, vp, vv], m.I_max[u, v])

    m.CurrentBounds = pyo.Constraint(m.Lines, m.VertP, m.VertV, rule=current_bounds_rule)


def add_voltage_vertices(m):
    """Fix voltage magnitude to discrete vertex values ``V_P``."""

    def voltage_rule(m, n, vp, vv):
        return m.V[n, vp, vv] == m.V_P[vv]

    m.voltageConstr = pyo.Constraint(m.Nodes, m.VertP, m.VertV, rule=voltage_rule)


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


def add_power_balance(m):
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
          return expr ==  m.E[u, vp, vv] + m.P_minus[u, vp, vv]
        else:
          return expr == m.E[u, vp, vv]

    m.power_balance = pyo.Constraint(m.Nodes, m.VertP, m.VertV, rule=power_balance_rule)



def add_phase_bounds(m):
    """Bound voltage angle variables between ``theta_min`` and ``theta_max``."""

    def phase_constr_rule(m, u, vp, vv):
        return pyo.inequality(m.theta_min, m.theta[u, vp, vv], m.theta_max)

    m.phaseConstr = pyo.Constraint(m.Nodes, m.VertP, m.VertV, rule=phase_constr_rule)


def add_current_definition(m):
    """Link current, voltage and power flow in per-unit: I*V = F."""

    def current_def_rule(m, u, v, vp, vv):
        return math.sqrt(3) * m.I[u, v, vp, vv] * m.V_P[vv] == m.F[u, v, vp, vv]

    m.current_def = pyo.Constraint(m.Lines, m.VertP, m.VertV, rule=current_def_rule)


def add_parent_power_bounds(m):
    """Bound power entering the operational graph at parent nodes."""

    def parent_power_constraint_rule(m, parent, vp, vv):
        return pyo.inequality(m.P_min, m.P_plus[parent, vp, vv], m.P_max)

    m.parent_power_constraint = pyo.Constraint(
        m.parents, m.VertP, m.VertV, rule=parent_power_constraint_rule
    )