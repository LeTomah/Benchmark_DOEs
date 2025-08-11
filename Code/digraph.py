def create_digraph(test_case):
    from loader import load_network
    net = load_network(test_case)

    import json
    import networkx as nx
    import matplotlib.pyplot as plt

    # -------------------------
    # 1. Conversion du réseau Pandapower en DiGraph
    # -------------------------
    G = nx.DiGraph()

    # 2. Récupération des positions à partir de la colonne 'geo'
    pos = {}
    for idx, row in net.bus.iterrows():
        geo_data = row['geo']
        if geo_data is None:
            raise ValueError(f"Le bus '{row['name']}' (index {idx}) n'a pas de coordonnées 'geo'.")
        geo_dict = json.loads(geo_data)
        coordinates = geo_dict["coordinates"]
        pos[idx] = tuple(coordinates)

    #Ajouter une puissance de base
    G.graph["s_base"] = 100.0 # MVA

    # Ajouter les nœuds
    for idx, row in net.bus.iterrows():
        G.add_node(idx, label=row["name"], pos=pos[idx], vn_kv=row["vn_kv"])

    # Ajouter les arêtes pour les lignes
    for _, row in net.line.iterrows():
        G.add_edge(row["from_bus"], row["to_bus"], type="line", name=row["name"], length=row["length_km"])

    # Ajouter les arêtes pour les transformateurs
    for _, row in net.trafo.iterrows():
        G.add_edge(row["hv_bus"], row["lv_bus"], type="trafo", name=row["name"])

    # Ajouter les générateurs et les charges comme attributs aux nœuds
    for _, row in net.gen.iterrows():
        G.nodes[row["bus"]]["type"] = "gen"
        G.nodes[row["bus"]]["gen_name"] = row["name"]
        G.nodes[row["bus"]]["gen_power"] = row["p_mw"]

    for _, row in net.load.iterrows():
        G.nodes[row["bus"]]["type"] = "load"
        G.nodes[row["bus"]]["load_name"] = row["name"]
        G.nodes[row["bus"]]["load_power"] = row["p_mw"]

    for _, row in net.ext_grid.iterrows():
        G.nodes[row["bus"]]["type"] = "ext_grid"
        G.nodes[row["bus"]]["grid_name"] = row["name"]

    # -------------------------
    # 2. Ajout des puissances consommées et injectées aux nœuds
    # -------------------------
    nx.set_node_attributes(G, 0.0, "P_load")
    nx.set_node_attributes(G, 0.0, "P_gen")

    # Charges
    for _, row in net.load.iterrows():
        G.nodes[row["bus"]]["P_load"] += row["p_mw"]

    # Générateurs
    for _, row in net.gen.iterrows():
        G.nodes[row["bus"]]["P_gen"] += row["p_mw"]

    # Source externe
    for _, row in net.ext_grid.iterrows():
        G.nodes[row["bus"]]["P_gen"] += 70.0

    # Calcul de P
    for n in G.nodes:
        G.nodes[n]["P"] = G.nodes[n]["P_gen"] - G.nodes[n]["P_load"]



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

    # Convert susceptance 'b' on edges to per-unit
    for u, v in G.edges():
        """
        Assuming 'b' is in Siemens/km, convert to per-unit
        b_pu = b_actual * (V_base^2 / S_base)
        V_base is assumed to be v_base_high (110 kV)
        """
        G[u][v]['b_pu'] = G[u][v].get('b', 0.0) * (get_node_voltage_kv(u) ** 2 / G.graph["s_base"])

    # -------------------------
    # 3. Préparer les couleurs des nœuds en fonction de P
    # -------------------------
    node_colors = []
    for n, data in G.nodes(data=True):
        if data["P"] > 0:
            node_colors.append("green")  # producteur
        elif data["P"] < 0:
            node_colors.append("red")  # consommateur
        else:
            node_colors.append("gray")  # neutre

    # -------------------------
    # 4. Préparer les labels : Nom + P_net
    # -------------------------
    labels = {n: f"{data['label']}\nP={round(data['P'], 2)}MW"
              for n, data in G.nodes(data=True)}

    # -------------------------
    # Donner accès à G
    # -------------------------
    return G


# -------------------------
# 5. Fonction d'affichage
# -------------------------
def plot_network(G):
    import networkx as nx, matplotlib.pyplot as plt
    pos = nx.get_node_attributes(G, 'pos')

    # Couleurs des nœuds selon P_net
    node_colors = [
        "green" if d.get("P_net", 0) > 0 else
        "red" if d.get("P_net", 0) < 0 else
        "gray"
        for _, d in G.nodes(data=True)
    ]

    plt.figure(figsize=(12, 8))
    labels = {n: f"{d['label']}\nP={round(d['P'], 2)} MW"
              for n, d in G.nodes(data=True)}
    nx.draw(
        G, pos,
        with_labels=True, labels=labels,
        node_size=1200, node_color=node_colors,
        edgecolors="black", font_size=8,
        alpha=0.85
    )

    # Labels des arêtes (type ligne ou trafo)
    edge_labels = nx.get_edge_attributes(G, 'type')
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=7)

    plt.title("Réseau électrique avec puissances (P_net)")
    plt.axis("equal")
    plt.show()


if __name__ == "__main__":
    create_digraph("network_test.py")