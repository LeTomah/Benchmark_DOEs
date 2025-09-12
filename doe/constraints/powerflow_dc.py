"""Simple DC power flow constraints used in DOE models."""

from __future__ import annotations

from typing import Any
import pyomo.environ as pyo


def build(model: pyo.ConcreteModel, graph: Any) -> None:
    """Attach a basic DC power flow formulation to ``model``.

    The model considers a flat voltage profile and small angle differences so
    that the active power flow on a line ``(u, v)`` is approximated by::

        F[u, v] = b_pu * (theta[u] - theta[v])

    where ``b_pu`` is the per-unit susceptance provided as an edge attribute.
    Nodal active power balance is enforced for every bus.
    """

    nodes = list(graph.nodes)
    lines = list(graph.edges)

    model.Nodes = pyo.Set(initialize=nodes)
    model.Lines = pyo.Set(initialize=lines, dimen=2)

    model.theta = pyo.Var(model.Nodes, bounds=(-0.1, 0.1))
    model.F = pyo.Var(model.Lines, domain=pyo.Reals)
    model.E = pyo.Var(model.Nodes, domain=pyo.Reals)

    def dc_flow_rule(m, u, v):
        b_pu = float(graph[u][v].get("b_pu", 0.0))
        return m.F[u, v] == b_pu * (m.theta[u] - m.theta[v])

    model.DCPowerFlow = pyo.Constraint(model.Lines, rule=dc_flow_rule)

    def power_balance_rule(m, n):
        inflow = sum(m.F[i, j] for (i, j) in m.Lines if j == n)
        outflow = sum(m.F[i, j] for (i, j) in m.Lines if i == n)
        return m.E[n] == inflow - outflow

    model.power_balance = pyo.Constraint(model.Nodes, rule=power_balance_rule)
