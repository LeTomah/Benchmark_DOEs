import json
import math
import networkx as nx
from collections import deque
from typing import Any, Dict, Iterable, Set


def create_graph(net: Any) -> nx.Graph:
    """Create a NetworkX graph from a pandapower network.

    Parameters
    ----------
    net : Any
        ``pandapowerNet`` instance providing buses, lines and transformers.
    """
    G = nx.Graph()

    if "geo" in net.bus.columns:
        pos: Dict[int, tuple] = {}
        for idx, geo in net.bus["geo"].items():
            try:
                if isinstance(geo, str):
                    geo = json.loads(geo)
                coords = geo.get("coordinates") if isinstance(geo, dict) else None
                if isinstance(coords, (list, tuple)) and len(coords) == 2:
                    pos[idx] = (float(coords[0]), float(coords[1]))
            except Exception:
                continue
        if len(pos) != len(net.bus):
            raise ValueError("Impossible de déterminer des coordonnées pour tous les bus.")
    elif hasattr(net, "bus_geodata"):
        pos = {idx: (float(row["x"]), float(row["y"])) for idx, row in net.bus_geodata.iterrows()}
    else:
        raise AttributeError("Bus positions not available in network.")

    G.graph["s_base"] = 100  # MVA base for per-unit calculations

    # Ajouter les nœuds
    for idx, row in net.bus.iterrows():
        G.add_node(
            idx,
            label=row["name"],
            pos=pos[idx],
            vn_kv=row["vn_kv"],
        )

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
    s_base = G.graph["s_base"]
    for _, row in net.gen.iterrows():
        G.nodes[row["bus"]]["type"] = "gen"
        G.nodes[row["bus"]]["gen_name"] = row["name"]
        G.nodes[row["bus"]]["gen_power"] = row["p_mw"] / s_base

    for _, row in net.sgen.iterrows():
        G.nodes[row["bus"]]["type"] = "sgen"
        G.nodes[row["bus"]]["sgen_name"] = row["name"]
        G.nodes[row["bus"]]["sgen_power"] = row["p_mw"] / s_base

    for _, row in net.load.iterrows():
        G.nodes[row["bus"]]["type"] = "load"
        G.nodes[row["bus"]]["load_name"] = row["name"]
        G.nodes[row["bus"]]["load_power"] = row["p_mw"] / s_base

    for _, row in net.ext_grid.iterrows():
        G.nodes[row["bus"]]["type"] = "ext_grid"
        G.nodes[row["bus"]]["grid_name"] = row["name"]

    # -------------------------
    # 2. Ajout des puissances consommées et injectées aux nœuds (p.u.)
    # -------------------------
    nx.set_node_attributes(G, 0.0, 'P_load')
    nx.set_node_attributes(G, 0.0, 'P_gen')

    # Charges
    for _, row in net.load.iterrows():
        G.nodes[row["bus"]]["P_load"] += row["p_mw"] / s_base

    # Générateurs
    for _, row in net.gen.iterrows():
        G.nodes[row["bus"]]["P_gen"] += row["p_mw"] / s_base

    # Générateurs statiques (sgen)
    for _, row in net.sgen.iterrows():
        G.nodes[row["bus"]]["P_gen"] += row["p_mw"] / s_base

    # Source externe
    for _, row in net.ext_grid.iterrows():
        G.nodes[row["bus"]]["P_gen"] += 70.0 / s_base

    # Calcul de P (convention : P<0 production, P>0 consommation)
    for n in G.nodes:
        G.nodes[n]["P"] = G.nodes[n]["P_load"] - G.nodes[n]["P_gen"]

    # -------------------------
    # Donner accès à G
    # -------------------------
    node_attrs = {n: G.nodes[n] for n in G.nodes}
    return G

#Calcul des valeurs max de courant dans chaque ligne
def calculate_current_bounds(G, max_i_ka, v_base):
    """Compute current limits in per-unit from network data.

    The pandapower network provides the maximum current rating of each line
    in the ``max_i_ka`` column. This function converts that rating to per-unit
    using the system's base power and the line's voltage base.

    Args:
        max_current_kA (float): Maximum allowable current for the line in kA.
        v_base (float): Voltage base of the line in kV.

    Returns:
        tuple: (I_min_pu, I_max_pu, base_i_ka). When the maximum current is not
        specified, a wide default range is returned.
    """
    base_i_ka = G.graph["s_base"] / (math.sqrt(3) * v_base)  # kA

    if max_i_ka is not None and not math.isnan(max_i_ka):
        I_max = max_i_ka / base_i_ka
        I_min = -I_max
        return I_min, I_max, base_i_ka

    # If no current limit is provided, use large bounds
    return -1000, 1000, base_i_ka
# -------------------------
# 5. Fonction d'affichage
# -------------------------

def plot_network(G, labels=None, node_colors=None):
    """Plot a networkx graph with node power information."""

    import networkx as nx, matplotlib.pyplot as plt
    pos = nx.get_node_attributes(G, 'pos')

    # -------------------------
    # 3. Préparer les couleurs des nœuds en fonction de P
    # -------------------------
    node_colors = []
    for n, data in G.nodes(data=True):
        if data["P"] < 0:
            node_colors.append("green")  # producteur
        elif data["P"] > 0:
            node_colors.append("red")  # consommateur
        else:
            node_colors.append("gray")  # neutre

    # -------------------------
    # 4. Préparer les labels : Nom + P_net
    # -------------------------
    labels = {n: f"{data['label']}\nP={round(data['P'], 2)} p.u."
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

    plt.title("Réseau électrique avec puissances (P_net en p.u.)")
    plt.axis("equal")
    plt.show()

def op_graph(full_graph: nx.DiGraph, operational_nodes: Set[int]) -> nx.DiGraph:
    """Return the subgraph induced by ``operational_nodes``."""
    return full_graph.subgraph(operational_nodes).copy()

def compute_info_dso(
    G: nx.Graph,
    operational_nodes: Iterable[int],
    children_nodes: Iterable[int],
    p_attr: str = "P",
) -> Dict[int, float]:
    """Estimate power contribution of each child node outside the operation area."""
    op_set: Set[int] = set(operational_nodes)
    children_set: Set[int] = set(children_nodes)

    def node_power(n: int) -> float:
        return float(G.nodes[n].get(p_attr, 0.0))

    info: Dict[int, float] = {}
    for c in children_set:
        total = node_power(c)
        for v in G.neighbors(c):
            if v in op_set:
                continue
            seen = {c}
            q = deque([v])
            while q:
                u = q.popleft()
                if u in seen or u in op_set:
                    continue
                seen.add(u)
                total += node_power(u)
                for w in G.neighbors(u):
                    if w not in seen and w not in op_set:
                        q.append(w)
        info[c] = total
    return info

if __name__ == "__main__":
    # Petit test manuel pour vérifier l'extraction des positions
    from Data.Networks.example_multivoltage_adapted import build

    net = build()
    G = create_graph(net)
    pos = nx.get_node_attributes(G, "pos")
    assert len(pos) == len(G.nodes), "Toutes les positions de bus doivent être présentes."
    print(f"Graph created with {len(G.nodes)} buses; all positions disponibles.")
