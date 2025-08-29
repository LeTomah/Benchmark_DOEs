"""DOE-specific constraints and objective."""

import pyomo.environ as pyo

from .constraints_common import (
    add_current_bounds,
    add_current_definition,
    add_curtailment_abs,
    add_dc_flow_constraints,
    add_parent_power_bounds,
    add_phase_bounds,
    add_power_balance,
    add_voltage_vertices,
)


def apply(m, G):
    """Apply DOE constraints and objective to model `m`."""

    # Common constraints
    add_curtailment_abs(m)
    add_current_bounds(m)
    add_dc_flow_constraints(m, G)
    add_current_definition(m)
    add_phase_bounds(m)
    add_power_balance(m)
    add_parent_power_bounds(m)
    add_voltage_vertices(m)

    # Children nodes consumption envelope
    def worst_case_children(m, u, vp, vv):
        return m.P_C_set[u, vp] == m.P_minus[u, vp, vv]

    m.worst_case = pyo.Constraint(m.children, m.VertP, m.VertV, rule=worst_case_children)

    def logical_constraint_rule(m, u):
        return m.P_C_set[u, 0] >= m.P_C_set[u, 1]

    m.logical_constraint = pyo.Constraint(m.children, rule=logical_constraint_rule)

    def children_voltage_rule(m, children, vp, vv):
        return pyo.inequality(m.V_min, m.V[children, vp, vv], m.V_max)

    m.children_voltage = pyo.Constraint(m.children, m.VertP, m.VertV, rule=children_voltage_rule)

    # Envelope volume and DSO gap
    def aux_constraint_rule(m, u):
        return m.aux[u] == m.P_C_set[u, 0] - m.P_C_set[u, 1]

    m.aux_constraint = pyo.Constraint(m.children, rule=aux_constraint_rule)

    def envelope_volume_rule(m):
        return m.envelope_volume == sum(m.aux[u] for u in m.children)

    m.envelope_volume_constraint = pyo.Constraint(rule=envelope_volume_rule)

    def diff_dso_rule(m, u):
        return -m.diff_DSO[u] <= (
                ((m.P_C_set[u, 0] + m.P_C_set[u, 1]) / 2) - m.info_DSO_param[u]
        )

    m.diff_DSO_constraint = pyo.Constraint(m.children, rule=diff_dso_rule)

    def diff_bis_dso_rule(m, u):
        return (
                ((m.P_C_set[u, 0] + m.P_C_set[u, 1]) / 2) - m.info_DSO_param[u]
            <= m.diff_DSO[u]
        )

    m.diff_bis_dso_constraint = pyo.Constraint(m.children, rule=diff_bis_dso_rule)

    def envelope_center_gap_rule(m):
        return m.envelope_center_gap == sum(m.diff_DSO[u] for u in m.children)

    m.envelope_center_gap_constraint = pyo.Constraint(rule=envelope_center_gap_rule)

    # Constraints on E based on sign of P
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

    # def p_C_minus_limit_rule(m, pos):
    #     return m.info_DSO_param[pos] >= m.P_C_set[pos, 1]
    #
    # m.p_C_minus_limit = pyo.Constraint(m.positive_demand, rule=p_C_minus_limit_rule)
    #
    # def p_C_plus_limit_rule(m, neg):
    #     return m.P_C_set[neg, 0] >= m.info_DSO_param[neg]
    #
    # m.p_C_plus_limit = pyo.Constraint(m.negative_demand, rule=p_C_plus_limit_rule)

    # Objective
    def objective_rule_doe(m):
        return (
            m.envelope_volume -(m.alpha * m.curtailment_budget) -(m.beta * m.envelope_center_gap)
        )

    m.objective_doe = pyo.Objective(rule=objective_rule_doe, sense=pyo.maximize)
