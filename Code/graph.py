import json
import networkx as nx
from typing import Dict, Any, Set
import math
from app_types import GraphBundle

def create_graph(net: Any) -> nx.Graph:
    # -------------------------
    # 1. Conversion du réseau Pandapower en DiGraph
    # -------------------------
    G = nx.Graph()

    # 2. Récupération des positions à partir de la colonne 'geo'
    pos = {}
    for idx, row in net.bus.iterrows():
        geo_data = row['geo']
        if geo_data is None:
            raise ValueError(f"Le bus '{row['name']}' (index {idx}) n'a pas de coordonnées 'geo'.")
        geo_dict = json.loads(geo_data)
        coordinates = geo_dict["coordinates"]
        pos[idx] = tuple(coordinates)

    G.graph["s_base"] = 100 #MVA

    # Ajouter les nœuds
    for idx, row in net.bus.iterrows():
        G.add_node(idx,
                   label=row["name"],
                   pos=pos[idx],
                   vn_kv=row["vn_kv"])

    # Ajouter les arêtes pour les lignes
    for _, row in net.line.iterrows():
        G.add_edge(row["from_bus"], row["to_bus"],
                   type = "line",
                   name = row["name"],
                   length = row["length_km"],
                   std_type = row["std_type"],
                   x_ohm = row["x_ohm_per_km"]*row["length_km"])
        u, v = row["from_bus"], row["to_bus"]
        V_kv = G.nodes[u]["vn_kv"]
        G[u][v]["b_pu"] = (V_kv ** 2) / (G[u][v]["x_ohm"] * G.graph["s_base"])

    # Ajouter les arêtes pour les transformateurs
    for _, row in net.trafo.iterrows():
        G.add_edge(row["hv_bus"], row["lv_bus"],
                   type="trafo",
                   name=row["name"],
                   std_type = None,
                   b_pu = None)
        u, v = row["hv_bus"], row["lv_bus"]
        G[u][v]["b_pu"] = None

    for u, v, data in G.edges(data=True):
        if 'x_ohm' in data and data['x_ohm'] > 0:
            # G[u][v]['b_pu'] = (G.nodes[u]["vn_kv"]**2 / (data['x_ohm'] * G.nodes["s_base"]))  # Calcule et stocke B_ij per unit
            print(f"Ligne {u}->{v}: b_pu = {G[u][v]['b_pu']} pu")


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
    nx.set_node_attributes(G, 0.0, 'P_load')
    nx.set_node_attributes(G, 0.0, 'P_gen')

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

    print(net.line.columns)



    # -------------------------
    # Donner accès à G
    # -------------------------
    node_attrs = {n: G.nodes[n] for n in G.nodes}
    return G

#Calcul des valeurs max de courant dans chaque ligne
def calculate_current_bounds(G, line_type, v_base):
    """
    Calculates the upper and lower bounds for current in per-unit
    based on the line type's maximum current capacity.

    Args:
        line_type (str): The type of the transmission line.
        i_base_kA (float): The base current in kA for the system.

    Returns:
        tuple: A tuple containing (I_min_pu, I_max_pu).
               Returns (None, None) if the line type is not found.
    """
    # Define a dictionary mapping line types to their maximum current capacity in kA
    # NOTE: This is a placeholder. You should populate this dictionary
    # with the actual maximum current capacities for your line types.
    i_base_kA = G.graph["s_base"] / (math.sqrt(3) * v_base)  # kA

    line_type_max_current_kA = {
        '149-AL1/24-ST1A 110.0': 0.47,  # Example value for 110 kV lines
        'NA2XS2Y 1x185 RM/25 12/20 kV': 0.3,  # Example value for 20 kV lines
        '94-AL1/15-ST1A 0.4': 0.15  # Example value for 0.4 kV lines
    }

    if line_type in line_type_max_current_kA:
        I_max_kA = line_type_max_current_kA[line_type]

        # Calculate the upper bound for current in per-unit
        I_max = I_max_kA / i_base_kA

        # The lower bound for current is the negative of the upper bound
        I_min = -I_max

        return I_min, I_max, i_base_kA

    elif line_type == None:
        return -1000, 1000
    else:
        return None, None
# -------------------------
# 5. Fonction d'affichage
# -------------------------

def plot_network(G, labels=None, node_colors=None):
    import networkx as nx, matplotlib.pyplot as plt
    pos = nx.get_node_attributes(G, 'pos')

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

def op_graph(full_graph: nx.DiGraph, operational_nodes: Set[int]) -> nx.DiGraph:
    """
    Retourne le sous-graphe induit par 'operational_nodes'.
    On filtre aussi les arêtes sortantes/entrantes.
    """
    return full_graph.subgraph(operational_nodes).copy()

if __name__ == "__main__":
    create_graph("Networks/network_test.py")