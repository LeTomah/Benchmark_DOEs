"""Generic security constraints shared across power flow modes."""
from __future__ import annotations

import pyomo.environ as pyo


def _add_current_bounds(m):
    def current_bounds_rule(m, u, v, vp, vv):
        return pyo.inequality(m.I_min[u, v], m.I[u, v, vp, vv], m.I_max[u, v])

    m.CurrentBounds = pyo.Constraint(m.Lines, m.VertP, m.VertV, rule=current_bounds_rule)


def _add_voltage_vertices(m):
    def voltage_rule(m, n, vp, vv):
        return m.V[n, vp, vv] == m.V_P[vv]

    m.voltageConstr = pyo.Constraint(m.Nodes, m.VertP, m.VertV, rule=voltage_rule)


def _add_curtailment_abs(m):
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
        return sum(m.z[u, vp, vv] for u in m.Nodes) <= m.curt_budget

    m.upper_bound = pyo.Constraint(m.VertP, m.VertV, rule=upper_bound_rule)


def _add_parent_power_bounds(m):
    def parent_power_constraint_rule(m, parent, vp, vv):
        return pyo.inequality(m.P_min, m.P_plus[parent, vp, vv], m.P_max)

    m.parent_power_constraint = pyo.Constraint(
        m.parents, m.VertP, m.VertV, rule=parent_power_constraint_rule
    )


def _add_phase_bounds(m):
    def phase_constr_rule(m, u, vp, vv):
        return pyo.inequality(m.theta_min, m.theta[u, vp, vv], m.theta_max)

    m.phaseConstr = pyo.Constraint(m.Nodes, m.VertP, m.VertV, rule=phase_constr_rule)


def attach_security_constraints(model, data, params, logger):
    """Attach security-related constraints to the model."""

    m = model
    _add_curtailment_abs(m)
    _add_current_bounds(m)
    _add_phase_bounds(m)
    _add_parent_power_bounds(m)
    _add_voltage_vertices(m)

    def worst_case_children(m, u, vp, vv):
        return m.P_C_set[u, vp] == m.P_minus[u, vp, vv]

    m.worst_case = pyo.Constraint(m.children, m.VertP, m.VertV, rule=worst_case_children)

    def logical_constraint_rule(m, u):
        return m.P_C_set[u, 0] >= m.P_C_set[u, 1]

    m.logical_constraint = pyo.Constraint(m.children, rule=logical_constraint_rule)

    def children_voltage_rule(m, u, vp, vv):
        return pyo.inequality(m.V_min, m.V[u, vp, vv], m.V_max)

    m.children_voltage = pyo.Constraint(m.children, m.VertP, m.VertV, rule=children_voltage_rule)

    def aux_constraint_rule(m, u):
        return m.aux[u] == m.P_C_set[u, 0] - m.P_C_set[u, 1]

    m.aux_constraint = pyo.Constraint(m.children, rule=aux_constraint_rule)

    def envelope_size_rule(m):
        return m.envelope_size == sum(m.aux[u] for u in m.children)

    m.envelope_size_constraint = pyo.Constraint(rule=envelope_size_rule)

    def diff_dso_rule(m, u):
        return -m.diff_DSO[u] <= ((m.P_C_set[u, 0] + m.P_C_set[u, 1]) / 2) - m.info_DSO_param[u]

    m.diff_DSO_constraint = pyo.Constraint(m.children, rule=diff_dso_rule)

    def diff_bis_dso_rule(m, u):
        return ((m.P_C_set[u, 0] + m.P_C_set[u, 1]) / 2) - m.info_DSO_param[u] <= m.diff_DSO[u]

    m.diff_bis_dso_constraint = pyo.Constraint(m.children, rule=diff_bis_dso_rule)

    def envelope_center_gap_rule(m):
        return m.envelope_center_gap == sum(m.diff_DSO[u] for u in m.children)

    m.envelope_center_gap_constraint = pyo.Constraint(rule=envelope_center_gap_rule)

    def net_power_upper_rule(m, n, vp, vv):
        return m.E[n, vp, vv] <= m.P[n]

    m.net_power_upper = pyo.Constraint(
        m.PositiveNodes, m.VertP, m.VertV, rule=net_power_upper_rule
    )

    def sign_E_upper_rule(m, n, vp, vv):
        return m.E[n, vp, vv] >= 0

    m.sign_E_upper = pyo.Constraint(
        m.PositiveNodes, m.VertP, m.VertV, rule=sign_E_upper_rule
    )

    def net_power_lower_rule(m, n, vp, vv):
        return m.E[n, vp, vv] >= m.P[n]

    m.net_power_lower = pyo.Constraint(
        m.NegativeNodes, m.VertP, m.VertV, rule=net_power_lower_rule
    )

    def sign_E_lower_rule(m, n, vp, vv):
        return m.E[n, vp, vv] <= 0

    m.sign_E_lower = pyo.Constraint(
        m.NegativeNodes, m.VertP, m.VertV, rule=sign_E_lower_rule
    )
