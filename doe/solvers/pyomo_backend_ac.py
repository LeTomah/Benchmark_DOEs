#TODO: Créer l'environnement pyomo dans le cas AC.

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

    #TODO: build_sets() est commune au module AC et DC: à déplacer dans un fichier commun

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
    m.V_min = pyo.Param(initialize=0.9) #TODO: changer la définition de V_min et V_max
    m.V_max = pyo.Param(initialize=1.1)
    m.V_P = pyo.Param(m.VertV, initialize={0: 0.9, 1: 1.1}, domain=pyo.NonNegativeReals)
    m.P_min = pyo.Param(initialize=P_min)
    m.P_max = pyo.Param(initialize=P_max)
    m.alpha = pyo.Param(initialize=alpha)
    m.beta = pyo.Param(initialize=beta)
    m.I_max = pyo.Param(
        m.Lines,
        initialize={
            (u, v): G[u][v].get("I_max_pu", 1) for (u, v) in m.Lines
        },
        domain=pyo.Reals,
    )
