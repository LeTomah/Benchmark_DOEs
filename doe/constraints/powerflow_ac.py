"""AC power flow constraints based on a simplified DistFlow model."""

from __future__ import annotations

from typing import Any

import pyomo.environ as pyo


def build(model: pyo.ConcreteModel, graph: Any) -> None:
    """Add AC power flow constraints following a simplified DistFlow model."""

    if getattr(model, "I_squared", None) is None:
        return  # AC-specific variables were not created (DC mode)

    parent_nodes = set(getattr(model, "ParentNodes", getattr(model, "parents", [])))
    child_nodes = set(getattr(model, "ChildNodes", getattr(model, "children", [])))

    def active_balance_rule(m, node, vp, vv):
        incoming = sum(m.F[i, j, vp, vv] for (i, j) in m.Lines if j == node)
        outgoing = sum(
            m.F[node, j, vp, vv] + m.R[node, j] * m.I_squared[node, j, vp, vv]
            for (node2, j) in m.Lines
            if node2 == node
        )
        balance = incoming - outgoing
        if node in parent_nodes:
            return balance == m.P_prime[node, vp, vv] - m.P_plus[node, vp, vv]
        if node in child_nodes:
            return balance == m.P_prime[node, vp, vv] + m.P_minus[node, vp, vv]
        return balance == m.P_prime[node, vp, vv]

    model.active_balance = pyo.Constraint(
        model.Nodes, model.VertP, model.VertV, rule=active_balance_rule
    )

    def reactive_balance_rule(m, node, vp, vv):
        incoming = sum(m.G[i, j, vp, vv] for (i, j) in m.Lines if j == node)
        outgoing = sum(
            m.G[node, j, vp, vv] + m.X[node, j] * m.I_squared[node, j, vp, vv]
            for (node2, j) in m.Lines
            if node2 == node
        )
        balance = incoming - outgoing
        if node in parent_nodes and getattr(m, "Q_plus", None) is not None:
            return balance == m.Q_prime[node, vp, vv] - m.Q_plus[node, vp, vv]
        if node in child_nodes and getattr(m, "Q_minus", None) is not None:
            return balance == m.Q_prime[node, vp, vv] + m.Q_minus[node, vp, vv]
        return balance == m.Q_prime[node, vp, vv]

    model.reactive_balance = pyo.Constraint(
        model.Nodes, model.VertP, model.VertV, rule=reactive_balance_rule
    )

    def voltage_drop_rule(m, u, v, vp, vv):
        return (
            m.V_squared[u, vp, vv]
            - m.V_squared[v, vp, vv]
            == 2 * (m.R[u, v] * m.F[u, v, vp, vv] + m.X[u, v] * m.G[u, v, vp, vv])
            + m.Z2[u, v] * m.I_squared[u, v, vp, vv]
        )

    model.voltage_drop = pyo.Constraint(
        model.Lines, model.VertP, model.VertV, rule=voltage_drop_rule
    )

    def current_voltage_rule(m, u, v, vp, vv):
        return m.V_squared[u, vp, vv] * m.I_squared[u, v, vp, vv] >= (
            m.F[u, v, vp, vv] ** 2 + m.G[u, v, vp, vv] ** 2
        )

    model.current_voltage = pyo.Constraint(
        model.Lines, model.VertP, model.VertV, rule=current_voltage_rule
    )

    def voltage_magnitude_link_rule(m, node, vp, vv):
        return m.V_squared[node, vp, vv] == m.V[node, vp, vv] ** 2

    model.voltage_magnitude_link = pyo.Constraint(
        model.Nodes, model.VertP, model.VertV, rule=voltage_magnitude_link_rule
    )
