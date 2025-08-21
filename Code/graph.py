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
        geo_data = row["geo"]
        if isinstance(geo_data, str):
            try:
                geo_dict = json.loads(geo_data)
                coordinates = geo_dict["coordinates"]
                pos[idx] = tuple(coordinates)
                continue
            except (json.JSONDecodeError, KeyError, TypeError):
                pass

    G.graph["s_base"] = 100 #MVA

    # Ajouter les nœuds
    for idx, row in net.bus.iterrows():
        G.add_node(idx,
                   label=row["name"],
                   pos=pos[idx],
                   vn_kv=row["vn_kv"])

    # Ajouter les arêtes pour les lignes
    for _, row in net.line.iterrows():
        G.add_edge(
            row["from_bus"],
            row["to_bus"],
            type="line",
            name=row["name"],
            length=row["length_km"],
            std_type=row["std_type"],
            x_ohm=row["x_ohm_per_km"] * row["length_km"],
            max_i_ka=row.get("max_i_ka"),
        )
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



    # Ajouter les générateurs, sgens et les charges comme attributs aux nœuds
    for _, row in net.gen.iterrows():
        G.nodes[row["bus"]]["type"] = "gen"
        G.nodes[row["bus"]]["gen_name"] = row["name"]
        G.nodes[row["bus"]]["gen_power"] = row["p_mw"]

    for _, row in net.sgen.iterrows():
        G.nodes[row["bus"]]["type"] = "sgen"
        G.nodes[row["bus"]]["sgen_name"] = row["name"]
        G.nodes[row["bus"]]["sgen_power"] = row["p_mw"]

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

    # Générateurs statiques (sgen)
    for _, row in net.sgen.iterrows():
        G.nodes[row["bus"]]["P_gen"] += row["p_mw"]

    # Source externe
    for _, row in net.ext_grid.iterrows():
        G.nodes[row["bus"]]["P_gen"] += 70.0

    # Calcul de P
    for n in G.nodes:
        G.nodes[n]["P"] = G.nodes[n]["P_gen"] - G.nodes[n]["P_load"]

    # -------------------------
    # Donner accès à G
    # -------------------------
    node_attrs = {n: G.nodes[n] for n in G.nodes}
    return G

#Calcul des valeurs max de courant dans chaque ligne
def calculate_current_bounds(G, max_current_kA, v_base):
    """Compute current limits in per-unit from network data.

    The pandapower network provides the maximum current rating of each line
    in the ``max_i_ka`` column. This function converts that rating to per-unit
    using the system's base power and the line's voltage base.

    Args:
        max_current_kA (float): Maximum allowable current for the line in kA.
        v_base (float): Voltage base of the line in kV.

    Returns:
        tuple: (I_min_pu, I_max_pu, i_base_kA). When the maximum current is not
        specified, a wide default range is returned.
    """
    i_base_kA = G.graph["s_base"] / (math.sqrt(3) * v_base)  # kA

    if max_current_kA is not None and not math.isnan(max_current_kA):
        I_max = max_current_kA / i_base_kA
        I_min = -I_max
        return I_min, I_max, i_base_kA

    # If no current limit is provided, use large bounds
    return -1000, 1000, i_base_kA
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