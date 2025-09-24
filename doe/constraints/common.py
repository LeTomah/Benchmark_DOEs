from __future__ import annotations

from typing import Any

import pyomo.environ as pyo


def build(model: pyo.ConcreteModel, graph: Any) -> None:
    """Add common DOE constraints shared by AC and DC formulations."""

    if not hasattr(model, "Nodes"):
        return

    def add_curtailment_abs(m: pyo.ConcreteModel) -> None:
        """Define curtailment ``curt`` and its absolute value ``z``."""

        def curt_def_rule(m, node, vp, vv):
            return m.curt[node, vp, vv] == m.P[node] - m.P_prime[node, vp, vv]

        m.curt_def = pyo.Constraint(m.Nodes, m.VertP, m.VertV, rule=curt_def_rule)

        def abs_pos_rule(m, node, vp, vv):
            return m.z[node, vp, vv] >= m.curt[node, vp, vv]

        m.abs_curt_pos = pyo.Constraint(m.Nodes, m.VertP, m.VertV, rule=abs_pos_rule)

        def abs_neg_rule(m, node, vp, vv):
            return m.z[node, vp, vv] >= -m.curt[node, vp, vv]

        m.abs_curt_neg = pyo.Constraint(m.Nodes, m.VertP, m.VertV, rule=abs_neg_rule)

        def upper_bound_rule(m, vp, vv):
            return sum(m.z[node, vp, vv] for node in m.Nodes) <= m.curtailment_budget

        m.curtailment_upper_bound = pyo.Constraint(
            m.VertP, m.VertV, rule=upper_bound_rule
        )

    def add_voltage_vertices(m: pyo.ConcreteModel) -> None:
        """Fix voltage magnitude to discrete vertex values ``V_P``."""

        def voltage_rule(m, node, vp, vv):
            return m.V[node, vp, vv] == m.V_P[vv]

        m.voltage_vertices = pyo.Constraint(m.Nodes, m.VertP, m.VertV, rule=voltage_rule)

    parent_set = getattr(model, "ParentNodes", None)
    if parent_set is None:
        parent_set = getattr(model, "parents", [])
    child_set = getattr(model, "ChildNodes", None)
    if child_set is None:
        child_set = getattr(model, "children", [])

    def add_parent_power_bounds(m: pyo.ConcreteModel, parents) -> None:
        """Bound power entering the operational graph at parent nodes."""

        parent_iter = list(parents)
        if not parent_iter:
            return

        def parent_power_constraint_rule(m, parent, vp, vv):
            return pyo.inequality(m.P_min, m.P_plus[parent, vp, vv], m.P_max)

        m.parent_power_constraint = pyo.Constraint(
            parent_iter, m.VertP, m.VertV, rule=parent_power_constraint_rule
        )

        if getattr(m, "Q_plus", None) is not None and (
            m.Q_min is not None or m.Q_max is not None
        ):

            def parent_reactive_constraint_rule(m, parent, vp, vv):
                lower = m.Q_min if m.Q_min is not None else -pyo.infinity
                upper = m.Q_max if m.Q_max is not None else pyo.infinity
                return pyo.inequality(lower, m.Q_plus[parent, vp, vv], upper)

            m.parent_reactive_constraint = pyo.Constraint(
                parent_iter, m.VertP, m.VertV, rule=parent_reactive_constraint_rule
            )

    def add_children_envelopes(m: pyo.ConcreteModel, children) -> None:
        """Link child node envelopes to downstream power variables."""

        child_iter = list(children)
        if not child_iter:
            return

        def worst_case_children(m, child, vp, vv):
            return m.P_C_set[child, vp] == m.P_minus[child, vp, vv]

        m.worst_case = pyo.Constraint(child_iter, m.VertP, m.VertV, rule=worst_case_children)

        def logical_constraint_rule(m, child):
            return m.P_C_set[child, 0] >= m.P_C_set[child, 1]

        m.envelope_ordering = pyo.Constraint(child_iter, rule=logical_constraint_rule)

        def children_voltage_rule(m, child, vp, vv):
            return pyo.inequality(m.V_min[child], m.V[child, vp, vv], m.V_max[child])

        m.children_voltage = pyo.Constraint(
            child_iter, m.VertP, m.VertV, rule=children_voltage_rule
        )

        def aux_constraint_rule(m, child):
            return m.aux[child] == m.P_C_set[child, 0] - m.P_C_set[child, 1]

        m.aux_constraint = pyo.Constraint(child_iter, rule=aux_constraint_rule)

        def envelope_volume_rule(m):
            return m.envelope_volume == sum(m.aux[child] for child in child_iter)

        m.envelope_volume_constraint = pyo.Constraint(rule=envelope_volume_rule)

        def diff_dso_rule(m, child):
            return -m.diff_DSO[child] <= (
                (m.P_C_set[child, 0] + m.P_C_set[child, 1]) / 2
                - m.info_DSO_param[child]
            )

        m.diff_DSO_constraint = pyo.Constraint(child_iter, rule=diff_dso_rule)

        def diff_dso_upper_rule(m, child):
            return (
                (m.P_C_set[child, 0] + m.P_C_set[child, 1]) / 2
                - m.info_DSO_param[child]
            ) <= m.diff_DSO[child]

        m.diff_DSO_upper_constraint = pyo.Constraint(child_iter, rule=diff_dso_upper_rule)

        def envelope_center_gap_rule(m):
            return m.envelope_center_gap == sum(m.diff_DSO[child] for child in child_iter)

        m.envelope_center_gap_constraint = pyo.Constraint(rule=envelope_center_gap_rule)

    def add_net_power_sign_rules(m: pyo.ConcreteModel) -> None:
        """Ensure the net power variables follow the sign of injections."""

        def net_power_upper_rule(m, node, vp, vv):
            return m.P_prime[node, vp, vv] <= m.P[node]

        def sign_positive_rule(m, node, vp, vv):
            return m.P_prime[node, vp, vv] >= 0

        def net_power_lower_rule(m, node, vp, vv):
            return m.P_prime[node, vp, vv] >= m.P[node]

        def sign_negative_rule(m, node, vp, vv):
            return m.P_prime[node, vp, vv] <= 0

        if len(model.PositiveNodes):
            m.net_power_upper = pyo.Constraint(
                m.PositiveNodes, m.VertP, m.VertV, rule=net_power_upper_rule
            )
            m.sign_positive = pyo.Constraint(
                m.PositiveNodes, m.VertP, m.VertV, rule=sign_positive_rule
            )
        if len(model.NegativeNodes):
            m.net_power_lower = pyo.Constraint(
                m.NegativeNodes, m.VertP, m.VertV, rule=net_power_lower_rule
            )
            m.sign_negative = pyo.Constraint(
                m.NegativeNodes, m.VertP, m.VertV, rule=sign_negative_rule
            )

    add_curtailment_abs(model)
    add_voltage_vertices(model)
    add_parent_power_bounds(model, parent_set)
    add_children_envelopes(model, child_set)
    add_net_power_sign_rules(model)
