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

    m.Nodes = pyo.Set(initialize=operational_nodes)
    m.Lines = pyo.Set(initialize=[l for l in G.edges])
    m.i = pyo.Set(initialize=[b for b in range(2)])
    m.j = pyo.Set(initialize=[b for b in range(2)])

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

    m.P_C_set = pyo.Var(m.children, m.i, domain=pyo.Reals)  # vertices of the power envelope at each child node
    m.P_plus = pyo.Var(m.parents, m.i, m.j, domain=pyo.Reals)  # power entering the operational graph
    m.P_minus = pyo.Var(m.children, m.i, m.j, domain=pyo.Reals)  # power leaving the operational graph
    m.P_C_min = pyo.Var(m.children, m.i, m.j, domain=pyo.Reals)
    m.P_C_max = pyo.Var(m.children, m.i, m.j, domain=pyo.Reals)

    m.O = pyo.Var(domain=pyo.Reals)

    # Parameters definition
    I_min = pyo.Param(initialize=0.8)
    I_max = pyo.Param(initialize=1.2)

    m.V_P = pyo.Param(m.j, default=1, domain=pyo.NonNegativeReals)
    m.P = pyo.Param(m.Nodes, default=1, domain=pyo.Reals)

    # Calculate the susceptance of each line in Siemens per km
    for u, v, data in G.edges(data=True):
        if "length" in data:  # Vérifie que l'arête a bien une longueur
            L = data["length"]  # Récupère la longueur en km
            G[u][v]['b'] = L * 200e-6  # Calcule et stocke 'b'

    # u, v = 0, 1  # identifiants des nœuds
    # print("b de l'arête (0 → 1) :", G[u][v].get("b", "non défini"))

    # Compute the PTDF matrix using branch susceptance diagonal and incidence matrix.
    def compute_PTDF(G, ref_bus=None):
        """
    Parameters:
        G (networkx.DiGraph): Graph with 'b' (susceptance) on edges.
        ref_bus (str): Slack bus node label. If None, first node is slack.

    Returns:
        PTDF (np.ndarray): PTDF matrix of shape (num_branches, num_buses)
        node_list (List[str]): Ordered list of nodes
        edge_list (List[tuple]): Ordered list of edges
    """

        # Get nodes and edges
        edge_list = list(G.edges())
        node_list = list(G.nodes())
        m = len(edge_list)
        n = len(node_list)

        # Build incidence matrix (rows: edges, columns: nodes)
        A = np.zeros((m, n))
        node_index = {node: i for i, node in enumerate(node_list)}

        for idx, (u, v) in enumerate(edge_list):
            A[idx, node_index[u]] = 1
            A[idx, node_index[v]] = -1

        # Slack bus
        if ref_bus is None:
            ref_bus = node_list[0]
            slack_idx = node_index[ref_bus]
        else:
            slack_idx = node_index[ref_bus]
        # Remove slack bus column from A
        A_red = np.delete(A, slack_idx, axis=1)  # shape (m, n-1)

        # Branch susceptance diagonal matrix Bd
        b_values = np.array([G[u][v].get('b', 1.0) for u, v in edge_list])
        Bd = np.diag(b_values)  # shape (m, m)

        # Compute PTDF
        At = A_red.T  # (n-1, m)
        AtBd = At @ Bd  # (n-1, m)
        AtBdA = AtBd @ A_red  # (n-1, n-1)

        AtBdA_inv = np.linalg.inv(AtBdA)  # (n-1, n-1)

        PTDF_red = Bd @ A_red @ AtBdA_inv  # (m, n-1)

        # Insert zero column for slack bus back into PTDF matrix
        PTDF = np.insert(PTDF_red, slack_idx, 0, axis=1)  # shape (m, n)

        return PTDF, node_list, edge_list

    PTDF, node_list, edge_list = compute_PTDF(G, ref_bus=0)
    node_to_idx = {node: i for i, node in enumerate(node_list)}
    edge_to_idx = {edge: i for i, edge in enumerate(edge_list)}

    print(PTDF)

# Donner accès à m :
    return m, PTDF, node_to_idx, edge_to_idx