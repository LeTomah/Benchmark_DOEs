"""Pyomo model construction helpers.

All quantities are expressed in per-unit. Voltage angles are in radians.
Power sign convention: P < 0 for production, P > 0 for consumption.
The network graph is undirected but edges have a single canonical
orientation given by the tuple order (u, v).
"""

import math
from typing import Dict, Optional

import pyomo.environ as pyo


def build_sets(m, G, parent_nodes, children_nodes):
    """Initialise the Pyomo sets describing the operational network.

    Parameters
    ----------
    m : pyomo.ConcreteModel
        Model to populate with sets.
    G : networkx.Graph
        Graph representing the operational network.  Node and edge identifiers
        are copied into Pyomo sets.
    parent_nodes, children_nodes : Iterable[int]
        Boundary nodes exchanging power with the rest of the grid.
    """
    m.Nodes = pyo.Set(initialize=list(G.nodes))
    m.Lines = pyo.Set(initialize=list(G.edges))
    m.VertP = pyo.Set(initialize=[0, 1])
    m.VertV = pyo.Set(initialize=[0, 1])
    m.parents = pyo.Set(initialize=parent_nodes)
    m.children = pyo.Set(initialize=children_nodes)

def build_params(m, G, info_DSO, alpha, beta, P_min, P_max):
    """Create Pyomo parameters used by the DOE and OPF formulations.

    Parameters
    ----------
    m : pyomo.ConcreteModel
        Model on which the parameters are declared.
    G : networkx.Graph
        Operational graph providing nodal injections and line limits.
    info_DSO : Mapping[int, float]
        External demand estimates supplied by the DSO for child nodes.
    alpha, beta : float
        Weights used in the DOE objective for curtailment and DSO deviation.
    P_min, P_max : float
        Bounds applied to the power exchanged with parent nodes.
    """
    m.P = pyo.Param(
        m.Nodes,
        initialize={n: G.nodes[n].get("P", 0.0) for n in G.nodes},
        domain=pyo.Reals,
        mutable=True,
    )
    m.PositiveNodes = pyo.Set(
        initialize=[n for n in m.Nodes if G.nodes[n].get("P", 0.0) > 0]
    )
    m.NegativeNodes = pyo.Set(
        initialize=[n for n in m.Nodes if G.nodes[n].get("P", 0.0) < 0]
    )
    m.info_DSO_param = pyo.Param(
        m.children,
        initialize={n: float(info_DSO.get(n, 0.0)) for n in m.children},
        domain=pyo.Reals,
    )
    m.positive_demand = pyo.Set(
        initialize=[n for n in m.children if pyo.value(m.info_DSO_param[n]) > 0]
    )
    m.negative_demand = pyo.Set(
        initialize=[n for n in m.children if pyo.value(m.info_DSO_param[n]) < 0]
    )
    m.V_min = pyo.Param(initialize=0.9)
    m.V_max = pyo.Param(initialize=1.1)
    m.V_P = pyo.Param(m.VertV, initialize={0: 0.9, 1: 1.1}, domain=pyo.NonNegativeReals)
    m.P_min = pyo.Param(initialize=P_min)
    m.P_max = pyo.Param(initialize=P_max)
    m.theta_min = pyo.Param(initialize=-0.25)
    m.theta_max = pyo.Param(initialize=0.25)
    m.alpha = pyo.Param(initialize=alpha)
    m.beta = pyo.Param(initialize=beta)
    m.I_min = pyo.Param(
        m.Lines,
        initialize={
            (u, v): G[u][v].get("I_min_pu", -1) for (u, v) in m.Lines
        },
        domain=pyo.Reals,
    )
    m.I_max = pyo.Param(
        m.Lines,
        initialize={
            (u, v): G[u][v].get("I_max_pu", 1) for (u, v) in m.Lines
        },
        domain=pyo.Reals,
    )


def build_variables(m, G):
    """Declare decision variables shared by DOE and OPF models."""
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

    #Curtailment budget
    total_p_abs = sum(abs(pyo.value(m.P[n])) for n in m.Nodes)
    m.curtailment_budget = pyo.Var(domain=pyo.NonNegativeReals, bounds=(-total_p_abs, total_p_abs))

    m.diff_DSO = pyo.Var(m.children, domain=pyo.NonNegativeReals)
    m.envelope_center_gap = pyo.Var(domain=pyo.Reals)


def build_expressions(m, G):
    """Create auxiliary Pyomo expressions if required.

    The current implementation does not introduce additional expressions, but
    the helper keeps a consistent API with other modules.
    """
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
    P_min: float = -1.0,
    P_max: float = 1.0,
):
    """Create and populate a Pyomo model from a NetworkX graph.

    Parameters
    ----------
    graph : networkx.Graph
        Complete network graph, typically produced by
        :func:`archive.graph.create_graph`.
    operational_nodes : Iterable[int], optional
        Subset of nodes forming the operational perimeter.  When ``None`` the
        full graph is used.
    parent_nodes, children_nodes : Iterable[int], optional
        Boundary nodes used to exchange power with the outside grid.
    info_DSO : Mapping[int, float], optional
        External demand estimates for child nodes.
    alpha, beta : float, optional
        Objective weights used by DOE formulations.
    P_min, P_max : float, optional
        Bounds on the power injected at parent nodes.

    Returns
    -------
    tuple
        ``(model, graph)`` where ``model`` is a populated
        :class:`pyomo.ConcreteModel` and ``graph`` the induced operational
        subgraph.
    """

    G_full = graph
    if operational_nodes is None:
        operational_nodes = list(G_full.nodes)

    G = G_full.subgraph(operational_nodes).copy()

    if parent_nodes is None and children_nodes:
        raise ValueError("parent_nodes must be provided for DOE problems")

    m = pyo.ConcreteModel()
    build_sets(m, G, parent_nodes or [operational_nodes[0]], children_nodes or [])
    build_params(m, G, info_DSO or {}, alpha, beta, P_min, P_max)
    build_variables(m, G)
    build_expressions(m, G)

    return m, G


if __name__ == "__main__":
    pass
