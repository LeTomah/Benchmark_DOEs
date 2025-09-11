"""Plot power flows and nodal bounds for a given scenario."""

import matplotlib.pyplot as plt
import networkx as nx
import scienceplots  # noqa: F401

plt.style.use(["science", "no-latex"])


def plot_power_flow(m, G, i, j, filename="Figures/Powerflow.pdf"):
    """Visualise power flows and nodal bounds for a given scenario."""

    pos = nx.get_node_attributes(G, "pos")
    labels = {}
    node_colors = []
    for n in G.nodes():
        label_text = f"{n}"
        if n in m.parents:
            label_text += f"\n[{m.P_min.value}, {m.P_max.value}]"
            node_colors.append("steelblue")
        elif n in m.children:
            p_c_values = [m.P_C_set[n, 0].value, m.P_C_set[n, 1].value]
            label_text += f"\n[{round(min(p_c_values), 4)}, {round(max(p_c_values), 4)}]"
            node_colors.append("steelblue")
        else:
            node_colors.append("steelblue")
        labels[n] = label_text

    plt.figure(figsize=(12, 8))

    edge_colors = []
    edge_labels = {}
    for u, v in G.edges():
        flow_value = None
        if (u, v) in m.Lines:
            flow_value = m.F[u, v, i, j].value
        elif (v, u) in m.Lines:
            flow_value = -m.F[v, u, i, j].value
        if flow_value is None:
            raise KeyError(f"Missing flow for edge ({u}, {v})")
        edge_labels[(u, v)] = f"{round(flow_value, 4)}"
        if flow_value > 0:
            edge_colors.append("blue")
        elif flow_value < 0:
            edge_colors.append("red")
        else:
            edge_colors.append("gray")

    nx.draw(
        G,
        pos,
        with_labels=False,
        node_size=1200,
        edge_color=edge_colors,
        edgecolors="black",
        font_size=8,
        alpha=0.85,
        node_color=node_colors,
    )

    for n in G.nodes():
        x, y = pos[n]
        text = labels[n]
        if n in m.children:
            plt.text(x, y - 0.1, text, fontsize=10, ha="center", va="top", color="red")
        elif n in m.parents:
            plt.text(x, y + 0.1, text, fontsize=10, ha="center", va="bottom", color="black")
        else:
            plt.text(x, y, text, fontsize=8, ha="center", va="center", color="black")

    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=7, label_pos=0.5)

    plt.title(f"Power Flow [p.u.] for i={i}, j={j}")
    plt.axis("equal")
    plt.savefig(filename)
    plt.show()
