"""Pyomo model construction helpers.

All quantities are expressed in per-unit. Voltage angles are in radians.
Power sign convention: P < 0 for production, P > 0 for consumption.
The network graph is undirected but edges have a single canonical
orientation given by the tuple order (u, v).
"""

from typing import Dict, Optional
import math

import pyomo.environ as pyo
from graph import calculate_current_bounds


def build_sets(m, G, parent_nodes, children_nodes):
    """Create model sets."""
    m.Nodes = pyo.Set(initialize=list(G.nodes))
    m.Lines = pyo.Set(initialize=list(G.edges))
    m.VertP = pyo.Set(initialize=[0, 1])
    m.VertV = pyo.Set(initialize=[0, 1])
    m.parents = pyo.Set(initialize=parent_nodes)
    m.children = pyo.Set(initialize=children_nodes)


def build_params(m, G, info_DSO, alpha, beta):
    """Create model parameters."""
    m.P = pyo.Param(
        m.Nodes,
        initialize={n: G.nodes[n].get("P", 0.0) for n in G.nodes},
        domain=pyo.Reals,
        mutable=True,
    )
    m.PositiveNodes = pyo.Set(initialize=[n for n in m.Nodes if G.nodes[n].get("P", 0.0) >= 0])
    m.NegativeNodes = pyo.Set(initialize=[n for n in m.Nodes if G.nodes[n].get("P", 0.0) <= 0])
    m.info_DSO_param = pyo.Param(
        m.children,
        initialize={n: float(info_DSO.get(n, 0.0)) for n in m.children},
        domain=pyo.Reals,
    )
    m.V_min = pyo.Param(initialize=0.9)
    m.V_max = pyo.Param(initialize=1.1)
    m.V_P = pyo.Param(m.VertV, initialize={0: 0.9, 1: 1.1}, domain=pyo.NonNegativeReals)
    m.P_min = pyo.Param(initialize=-0.2)
    m.P_max = pyo.Param(initialize=0.2)
    m.theta_min = pyo.Param(initialize=-math.pi)
    m.theta_max = pyo.Param(initialize=math.pi)
    m.alpha = pyo.Param(initialize=alpha)
    m.beta = pyo.Param(initialize=beta)
    m.I_min = pyo.Param(
        m.Lines,
        initialize={
            (u, v): calculate_current_bounds(
                G, G[u][v].get("max_i_ka"), G.nodes[u]["vn_kv"]
            )[0]
            for (u, v) in m.Lines
        },
        domain=pyo.Reals,
    )
    m.I_max = pyo.Param(
        m.Lines,
        initialize={
            (u, v): calculate_current_bounds(
                G, G[u][v].get("max_i_ka"), G.nodes[u]["vn_kv"]
            )[1]
            for (u, v) in m.Lines
        },
        domain=pyo.Reals,
    )


def build_variables(m, G):
    """Create model variables."""
    m.F = pyo.Var(m.Lines, m.VertP, m.VertV, domain=pyo.Reals)
    m.I = pyo.Var(m.Lines, m.VertP, m.VertV, domain=pyo.Reals)
    m.theta = pyo.Var(m.Nodes, m.VertP, m.VertV, domain=pyo.Reals)
    m.V = pyo.Var(m.Nodes, m.VertP, m.VertV, domain=pyo.NonNegativeReals)
    m.E = pyo.Var(m.Nodes, m.VertP, m.VertV, domain=pyo.Reals)
    m.P_plus = pyo.Var(m.parents, m.VertP, m.VertV, domain=pyo.Reals)
    m.P_minus = pyo.Var(m.children, m.VertP, m.VertV, domain=pyo.Reals)
    m.P_C_set = pyo.Var(m.children, m.VertP, domain=pyo.Reals)
    m.z = pyo.Var(m.Nodes, m.VertP, m.VertV, domain=pyo.NonNegativeReals)
    m.curt = pyo.Var(m.Nodes, m.VertP, m.VertV, domain=pyo.Reals)
    m.aux = pyo.Var(m.children, domain=pyo.Reals)
    m.envelope_volume = pyo.Var(domain=pyo.Reals)
    m.curtailment_budget = pyo.Var(domain=pyo.NonNegativeReals)
    m.diff_DSO = pyo.Var(m.children, domain=pyo.NonNegativeReals)
    m.envelope_center_gap = pyo.Var(domain=pyo.Reals)


def build_expressions(m, G):
    """Placeholder for additional Pyomo expressions."""
    # Currently no additional expressions required.
    return


def create_pyo_env(
    graph,
    operational_nodes=None,
    parent_nodes=None,
    children_nodes=None,
    info_DSO: Optional[Dict[int, float]] = None,
    alpha: float = 1.0,
    beta: float = 1.0,
):
    """Create and populate a Pyomo model from a NetworkX graph."""

    G_full = graph
    if operational_nodes is None:
        operational_nodes = list(G_full.nodes)

    G = G_full.subgraph(operational_nodes).copy()

    if parent_nodes is None and children_nodes:
        raise ValueError("parent_nodes must be provided for DOE problems")

    m = pyo.ConcreteModel()
    build_sets(m, G, parent_nodes or [operational_nodes[0]], children_nodes or [])
    build_params(m, G, info_DSO or {}, alpha, beta)
    build_variables(m, G)
    build_expressions(m, G)

    return m, G


if __name__ == "__main__":
    pass
