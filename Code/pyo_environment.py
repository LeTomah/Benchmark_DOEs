# pyo_environment.py
"""Pyomo model construction helpers."""

from typing import Dict, Optional

import pyomo.environ as pyo

from graph import calculate_current_bounds


def create_pyo_env(
    graph,
    operational_nodes=None,
    parent_nodes=None,
    children_nodes=None,
    info_DSO: Optional[Dict[int, float]] = None,
    alpha: float = 1.0,
    beta: float = 1.0,
):
    """Create a Pyomo model from a networkx graph.

    Parameters
    ----------
    graph:
        NetworkX graph describing the electrical network.
    operational_nodes:
        Nodes kept in the operational sub-graph.
    parent_nodes:
        Boundary nodes injecting power into the operational area.
    children_nodes:
        Boundary nodes consuming power from the operational area.
    info_DSO:
        Mapping of child node to DSO power estimation.
    alpha, beta:
        Weights used in the objective function. They are defined here so the
        user can tune them from the entry point of the application.
    """

    # Charger le graphe complet
    G_full = graph

    # Si l'utilisateur ne donne rien, on prend tous les nœuds
    if operational_nodes is None:
        operational_nodes = list(G_full.nodes)

    # --- Définition du graphe opérationnel ---
    G = G_full.subgraph(operational_nodes)

    # Création du modèle
    m = pyo.ConcreteModel()

    m.Nodes = pyo.Set(initialize=[b for b in G.nodes])
    m.Lines = pyo.Set(initialize=[l for l in G.edges])
    m.i = pyo.Set(initialize=[0, 1])  # Initialize m.i with two generic elements
    m.j = pyo.Set(initialize=[0, 1])

    m.P = pyo.Param(m.Nodes,
                    initialize={n: - G.nodes[n].get('P') for n in G.nodes},
                    domain=pyo.Reals, mutable=True)

    # --- Définir parents/enfants dynamiquement ---
    if parent_nodes is None:
        parent_nodes = [operational_nodes[0]]  # par défaut, premier nœud comme parent
    if children_nodes is None:
        children_nodes = [n for n in operational_nodes if n not in parent_nodes]
    m.children = pyo.Set(initialize=children_nodes)
    m.parents = pyo.Set(initialize=parent_nodes)

    # Build sets based on sign of parameter P
    m.PositiveNodes = pyo.Set(initialize=[n for n in m.Nodes if pyo.value(m.P[n]) >= 0])
    m.NegativeNodes = pyo.Set(initialize=[n for n in m.Nodes if pyo.value(m.P[n]) <= 0])

    # Variables principales
    m.F = pyo.Var(m.Lines, m.i, m.j, domain=pyo.Reals)  # active power flow through lines
    m.I = pyo.Var(m.Lines, m.i, m.j, domain=pyo.Reals)  # current flowing through lines
    m.theta = pyo.Var(m.Nodes, m.i, m.j, domain=pyo.Reals)  # phase angle of the voltage
    m.V = pyo.Var(m.Nodes, m.i, m.j, domain=pyo.NonNegativeReals)  # voltage magnitude at each node
    m.E = pyo.Var(m.Nodes, m.i, m.j, domain=pyo.Reals)  # net power injection/consumption
    m.P_plus = pyo.Var(m.parents, m.i, m.j, domain=pyo.Reals)  # power entering the operational graph
    m.P_minus = pyo.Var(m.children, m.i, m.j, domain=pyo.Reals)  # power leaving the operational graph
    m.P_C_set = pyo.Var(m.children, m.i, domain=pyo.Reals)  # vertices of the power envelope at each child node
    m.z = pyo.Var(m.Nodes, m.i, m.j, domain=pyo.NonNegativeReals)
    m.curt = pyo.Var(m.Nodes, m.i, m.j, domain=pyo.Reals)
    m.aux = pyo.Var(m.children, domain=pyo.Reals)
    m.tot_P = pyo.Var(domain= pyo.Reals)
    m.O = pyo.Var(domain=pyo.NonNegativeReals)
    m.diff_DSO = pyo.Var(m.children, domain=pyo.NonNegativeReals)

    #Paramètres du modèle
    info_DSO = info_DSO or {}
    m.info_DSO_param = pyo.Param(
        m.children,
        initialize={n: float(info_DSO.get(n, 0.0)) for n in m.children},
        domain=pyo.Reals
    )
    # Constant definition
    m.V_min = pyo.Param(initialize= 0.9)
    m.V_max = pyo.Param(initialize= 1.1)
    m.V_P = pyo.Param(m.j, initialize={0: 0.9, 1: 1.1}, domain=pyo.NonNegativeReals)
    m.P_min = pyo.Param(initialize=-0.2)
    m.P_max = pyo.Param(initialize= 0.2)
    m.theta_min = pyo.Param(initialize=-180.0)
    m.theta_max = pyo.Param(initialize=180.0)
    m.alpha = pyo.Param(initialize=alpha)
    m.beta = pyo.Param(initialize=beta)
    m.I_min = pyo.Param(
        m.Lines,
        initialize={
            (u, v): calculate_current_bounds(
                G,
                G[u][v].get("max_i_ka"),
                G.nodes[u]["vn_kv"],
            )[0]
            for (u, v) in m.Lines
        },
        domain=pyo.Reals,
    )
    m.I_max = pyo.Param(
        m.Lines,
        initialize={
            (u, v): calculate_current_bounds(
                G,
                G[u][v].get("max_i_ka"),
                G.nodes[u]["vn_kv"],
            )[1]
            for (u, v) in m.Lines
        },
        domain=pyo.Reals,
    )


    # Les puissances sont déjà stockées en per unit dans le graphe

    # Donner accès à m :
    return m, G

if __name__ == "__main__":
    create_pyo_env("Data/Networks/network_test.py")
