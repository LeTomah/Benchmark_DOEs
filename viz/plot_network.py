"""Visualization utilities for network graphs."""

import matplotlib.pyplot as plt
import networkx as nx


def plot_network(
    G,
    labels=None,
    node_colors=None,
    filename="Figures/Full_network.pdf",
    dpi: int = 300,
):
    """Plot a networkx graph with node power information.

    Parameters
    ----------
    G : networkx.Graph
        Graph to plot. Nodes are expected to contain ``P`` (net power)
        attributes and ``pos`` (position) for layout.
    labels : dict, optional
        Unused, maintained for backward compatibility.
    node_colors : list, optional
        Unused, maintained for backward compatibility.
    filename : str, optional
        Path where the figure will be saved.
    dpi : int, optional
        Resolution of the generated figure.
    """

    pos = nx.get_node_attributes(G, "pos")

    # Node colours based on net power
    node_colors = []
    for _, data in G.nodes(data=True):
        if data.get("P", 0) < 0:
            node_colors.append("green")  # producer
        elif data.get("P", 0) > 0:
            node_colors.append("red")  # consumer
        else:
            node_colors.append("gray")  # neutral

    labels = {
        n: f"{n}\nP={round(data.get('P', 0), 2)} p.u."
        for n, data in G.nodes(data=True)
    }

    plt.figure(figsize=(12, 8), dpi=dpi)

    nx.draw(
        G,
        pos,
        with_labels=True,
        labels=labels,
        node_size=1200,
        node_color=node_colors,
        edgecolors="black",
        font_size=8,
        alpha=0.85,
    )

    edge_labels = nx.get_edge_attributes(G, "type")
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=7)

    plt.title("Réseau électrique avec puissances (P_net en p.u.)")
    plt.axis("equal")
    plt.tight_layout()
    plt.savefig(filename, dpi=dpi)
    plt.show()
