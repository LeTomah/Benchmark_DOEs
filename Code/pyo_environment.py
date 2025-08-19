# pyo_environment.py
from typing import Dict, Any, Set, Optional
import networkx as nx
from app_types import EnvPyo

def create_pyo_env(graph,
               operational_nodes=None,
               parent_nodes=None,
               children_nodes=None,
               info_DSO: Optional[Dict[int, float]] = None):

#def create_pyo_environ(test_case, operational_nodes=None, parent_nodes=None, children_nodes=None):
    import graph
    import pyomo.environ as pyo
    # Charger le graphe complet
    G_full = graph
    s_base = G_full.graph["s_base"]

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

    m.P = pyo.Param(m.Nodes, initialize={n: - G.nodes[n].get('P') for n in G.nodes}, domain=pyo.Reals, mutable=True)

    # --- Définir parents/enfants dynamiquement ---
    if parent_nodes is None:
        parent_nodes = [operational_nodes[0]]  # par défaut, premier nœud comme parent
    if children_nodes is None:
        children_nodes = [n for n in operational_nodes if n not in parent_nodes]
    m.children = pyo.Set(initialize=children_nodes)
    m.parents = pyo.Set(initialize=parent_nodes)

    # Variables principales
    m.F = pyo.Var(m.Lines, m.i, m.j, domain=pyo.Reals)  # active power flow through lines
    m.I = pyo.Var(m.Lines, m.i, m.j, domain=pyo.Reals)  # current flowing through lines
    m.theta = pyo.Var(m.Nodes, m.i, m.j, domain=pyo.Reals)  # phase angle of the voltage
    m.V = pyo.Var(m.Nodes, m.i, m.j, domain=pyo.NonNegativeReals)  # voltage magnitude at each node
    m.E = pyo.Var(m.Nodes, m.i, m.j, domain=pyo.Reals)  # net power injection/consumption
    m.P_plus = pyo.Var(m.parents, m.i, m.j, domain=pyo.Reals)  # power entering the operational graph
    m.P_minus = pyo.Var(m.children, m.i, m.j, domain=pyo.Reals)  # power leaving the operational graph
    m.P_C_set = pyo.Var(m.children, m.i, domain=pyo.Reals)  # vertices of the power envelope at each child node
    m.aux = pyo.Var(m.children, domain=pyo.Reals)

    #Paramètres du modèle
    m.info_DSO_param = pyo.Param(m.children, initialize = {n: info_DSO[n-1] for n in m.children}, domain = pyo.Reals) # Renamed parameter and adjusted index for list

    m.I_min = pyo.Param(m.Lines, initialize = {(u,v): calculate_current_bounds(G.edges[u,v]["std_type"], G.nodes[u]['vn_kv'])[0] for (u,v) in m.Lines}, domain = pyo.Reals)
    m.I_max = pyo.Param(m.Lines, initialize = {(u,v): calculate_current_bounds(G.edges[u,v]["std_type"], G.nodes[u]['vn_kv'])[1] for (u,v) in m.Lines}, domain = pyo.Reals)

    m.V_P = pyo.Param(m.j, initialize={0: 0.9, 1: 1.1}, domain=pyo.NonNegativeReals)

    m.O = pyo.Var(domain=pyo.NonNegativeReals)

    # Calcul du per unit
    for u in G.nodes():
        if G.nodes[u].get('P', 0.0) / s_base == 0:
            m.P[u] = 0
        else:
            G.nodes[u]['P_pu'] = G.nodes[u].get('P', 0.0) / s_base
            m.P[u] = - G.nodes[u]['P_pu']

    # Donner accès à m :
    return m, G

if __name__ == "__main__":
    create_pyo_environ("Networks/network_test.py")