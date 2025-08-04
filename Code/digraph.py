def create_digraph():
    import test_network
    net = test_network.create_network()
    
    import json
    import networkx as nx
    import matplotlib.pyplot as plt
# 1. Conversion du réseau Pandapower en DiGraph
# ================================
    G = nx.DiGraph()

# Créer les positions à partir de la colonne "geo"
    pos = {}
    for idx, row in net.bus.iterrows():
    # Extraire le champ 'geo' qui est une chaîne de caractères représentant un dictionnaire JSON
        geo_data = row['geo']
    
    # Convertir la chaîne JSON en un dictionnaire Python
        geo_dict = json.loads(geo_data)
    
    # Extraire la liste des coordonnées
        coordinates = geo_dict["coordinates"]
    
    # Ajouter les coordonnées dans le dictionnaire pos
        pos[idx] = tuple(coordinates)  # Assigner les coordonnées sous forme de tuple

# Ajouter les nœuds (avec le nom comme label)
    for idx, row in net.bus.iterrows():
        G.add_node(idx, label=row["name"], pos=pos[idx])

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
    
# 2. Ajout des puissances consommées et injectées aux nœuds
# ================================
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
        G.nodes[row["bus"]]["P_gen"] += 999.0  # grande valeur symbolique

# Calcul de P_net
    for n in G.nodes:
        G.nodes[n]["P_net"] = G.nodes[n]["P_gen"] - G.nodes[n]["P_load"]

# 3. Préparer les couleurs des nœuds en fonction de P_net
# ================================
    node_colors = []
    for n, data in G.nodes(data=True):
        if data["P_net"] > 0:
            node_colors.append("green")   # producteur
        elif data["P_net"] < 0:
            node_colors.append("red")     # consommateur
        else:
            node_colors.append("gray")    # neutre
        
# 4. Préparer les labels : Nom + P_net
# ================================
    labels = {n: f"{data['label']}\nP={round(data['P_net'],2)}MW"
              for n, data in G.nodes(data=True)}

# 5. Fonction d'affichage
# ================================
    def plot_network():
        pos = nx.get_node_attributes(G, 'pos')

        plt.figure(figsize=(12, 8))
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
    
    plot_network()
