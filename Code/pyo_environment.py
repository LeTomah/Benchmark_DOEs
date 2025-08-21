def create_pyo_environ(test_case,
                       operational_nodes=None,
                       parent_nodes=None,
                       children_nodes=None):
    import digraph
    import pyomo.environ as pyo
    import numpy as np

    # Charger le graphe complet
    G_full = digraph.create_digraph(test_case)

    # Si l'utilisateur ne donne rien, on prend tous les nœuds
    if operational_nodes is None:
        operational_nodes = list(G_full.nodes)

    # --- Définition du graphe opérationnel ---
    G = G_full.subgraph(operational_nodes).copy()

    # Création du modèle
    m = pyo.ConcreteModel()

    s_base = 100  # MVA
    v_base_high = 110  # kV

    m.Nodes = pyo.Set(initialize=[b for b in G.nodes])
    m.Lines = pyo.Set(initialize=[l for l in G.edges])
    m.i = pyo.Set(initialize=[0, 1])  # Initialize m.i with two generic elements
    m.j = pyo.Set(initialize=[0, 1])
    m.children = pyo.Set(initialize=[1, 2])
    m.parents = pyo.Set(initialize=[0])

    # Net power at each node is stored in the ``P_net`` attribute of the
    # NetworkX graph.  Some nodes might not have this attribute explicitly
    # defined, so ``get`` is used with a default value of ``0.0`` to avoid
    # returning ``None`` which cannot be negated.  ``m.P`` represents the
    # opposite of this net power (positive for loads, negative for generation).
    m.P = pyo.Param(
        m.Nodes,
        initialize={n: -G.nodes[n].get('P_net', 0.0) for n in G.nodes},
        domain=pyo.Reals,
        mutable=True,
    )

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

    # m.P_C_min = pyo.Var(m.children, m.i, m.j, domain=pyo.Reals)
    # m.P_C_max = pyo.Var(m.children, m.i, m.j,  domain=pyo.Reals)

    m.V_P = pyo.Param(m.j, initialize={0: 0.9, 1: 1.1}, domain=pyo.NonNegativeReals)

    m.O = pyo.Var(domain=pyo.NonNegativeReals)

    # Parameters definition
    I_min = pyo.Param(initialize=0.8)
    I_max = pyo.Param(initialize=1.2)



    def get_node_voltage_kv(node_index):
        """
        Returns the voltage (vn_kv) for a given node index from the graph.

        Args:
          node_index: The index of the node in the graph.

        Returns:
          The voltage in kV for the specified node.
        """
        # Assuming 'G' is the NetworkX DiGraph object created earlier
        # Access the 'vn_kv' attribute for the given node_index
        return G.nodes[node_index]['vn_kv']

    # Calculate the susceptance of each line in Siemens per km
    for u, v, data in G.edges(data=True):
        if "length" in data:  # Vérifie que l'arête a bien une longueur
            L = data["length"]  # Récupère la longueur en km
            G[u][v]['b'] = L * 200e-6  # Calcule et stocke 'b'

    # u, v = 0, 1  # identifiants des nœuds
    # print("b de l'arête (0 → 1) :", G[u][v].get("b", "non défini"))

    # Convert susceptance 'b' on edges to per-unit
    for u, v in G.edges():
        # Assuming 'b' is in Siemens/km, convert to per-unit
        # b_pu = b_actual * (V_base^2 / S_base)
        # V_base is assumed to be v_base_high (110 kV)
        G[u][v]['b_pu'] = G[u][v].get('b', 0.0) * (get_node_voltage_kv(u) ** 2 / s_base)
    print(m.P[11].value)
    print("Converted power values (P) in G and m.P to per-unit.")
    print("Converted susceptance values (b) in G edges to per-unit.")
    print("Voltage and Current bounds assumed to be already in per-unit.")

# Donner accès à m :
    return m
