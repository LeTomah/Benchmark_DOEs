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
    """Add DC power flow variables and constraints to ``model``.

    Parameters
    ----------
    model:
        Pyomo model to augment.
    graph:
        NetworkX graph describing the electrical network.
    """

    nodes = list(graph.nodes)
    lines = list(graph.edges)

    model.Nodes = pyo.Set(initialize=nodes)
    model.Lines = pyo.Set(initialize=lines, dimen=2)

    model.theta = pyo.Var(model.Nodes, bounds=(-math.pi, math.pi))
    model.F = pyo.Var(model.Lines)

    def dc_flow_rule(m, u, v):
        data = graph[u][v]
        b = float(data.get("b_pu", 0.0))
        return m.F[u, v] == b * (m.theta[u] - m.theta[v])

    model.DCPowerFlow = pyo.Constraint(model.Lines, rule=lambda m, u, v: dc_flow_rule(m, u, v))

    def balance_rule(m, n):
        inflow = sum(m.F[i, j] for (i, j) in m.Lines if j == n)
        outflow = sum(m.F[i, j] for (i, j) in m.Lines if i == n)
        P = float(graph.nodes[n].get("P", 0.0))
        return inflow - outflow == P

    model.NodalBalance = pyo.Constraint(model.Nodes, rule=balance_rule)
