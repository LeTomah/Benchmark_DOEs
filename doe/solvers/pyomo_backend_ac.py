#TODO: Créer l'environnement pyomo dans le cas AC.
#TODO: identifier les éléments communs AC/DC et les placer dans un fichier à part.

"""Pyomo model construction helpers.

All quantities are expressed in per-unit. Voltage angles are in radians.
Power sign convention: P < 0 for production, P > 0 for consumption.
The network graph is undirected but edges have a single canonical
orientation given by the tuple order (u, v).
"""

import math
from typing import Dict, Optional

import pyomo.environ as pyo

def build_sets(m, G, parent_nodes, children_nodes):  #TODO: simplifier les arguments des fonctions
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

def build_params(m, G, info_DSO, alpha, beta, P_min, P_max, Q_min, Q_max):
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
    m.PositivePNodes = pyo.Set(
        initialize=[n for n in m.Nodes if G.nodes[n].get("P", 0.0) > 0]
    )
    m.NegativePNodes = pyo.Set(
        initialize=[n for n in m.Nodes if G.nodes[n].get("P", 0.0) < 0]
    )
    m.Q = pyo.Param(
        m.Nodes,
        initialize={n: G.nodes[n].get("Q", 0.0) for n in G.nodes},
        domain=pyo.Reals,
        mutable=True,
    )
    m.PositiveQNodes = pyo.Set(
        initialize=[n for n in m.Nodes if G.nodes[n].get("Q", 0.0) > 0]
    )
    m.NegativeQNodes = pyo.Set(
        initialize=[n for n in m.Nodes if G.nodes[n].get("Q", 0.0) < 0]
    )
    m.info_P = pyo.Param(
        m.children,
        initialize={n: float(info_DSO.get(n, 0.0)) for n in m.children},
        domain=pyo.Reals,
    )
    m.positive_P_demand = pyo.Set(
        initialize=[n for n in m.children if pyo.value(m.info_P[n]) > 0]
    )
    m.negative_P_demand = pyo.Set(
        initialize=[n for n in m.children if pyo.value(m.info_P[n]) < 0]
    )
    m.info_Q = pyo.Param(
        m.children,
        initialize={n: float(info_DSO.get(n, 0.0)) for n in m.children},
        domain=pyo.Reals,
    )
    m.positive_Q_demand = pyo.Set(
        initialize=[n for n in m.children if pyo.value(m.info_Q[n]) > 0]
    )
    m.negative_Q_demand = pyo.Set(
        initialize=[n for n in m.children if pyo.value(m.info_Q[n]) < 0]
    )
    m.V_min = pyo.Param(initialize=0.9) #TODO: changer la définition de V_min et V_max
    m.V_max = pyo.Param(initialize=1.1)
    m.V_P = pyo.Param(m.VertV, initialize={0: 0.9, 1: 1.1}, domain=pyo.NonNegativeReals)
    m.I_max = pyo.Param(m.Lines,
                        initialize={(u, v): G[u][v].get("I_max_pu", 1) for (u, v) in m.Lines},
                        domain=pyo.Reals)
    m.P_min = pyo.Param(initialize=P_min)
    m.P_max = pyo.Param(initialize=P_max)
    m.Q_min = pyo.Param(initialize=Q_min)
    m.Q_max = pyo.param(initialize=Q_max)
    m.alpha = pyo.Param(initialize=alpha)
    m.beta = pyo.Param(initialize=beta)

def build_variables(m, G):
    """Declare decision variables shared by DOE and OPF models."""
    m.F = pyo.Var(m.Lines, m.VertP, m.VertV, domain=pyo.Reals)
    m.G = pyo.Var(m.Lines, m.VertP, m.VertV, domain=pyo.Reals) #TODO: trouver comment renommer F et G
    m.I = pyo.Var(m.Lines, m.VertP, m.VertV, domain=pyo.Reals)
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