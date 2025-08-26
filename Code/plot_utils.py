# plot_utils.py
import networkx as nx
import matplotlib.pyplot as plt
import numpy as np


def plot_network(G, labels=None, node_colors=None):
    """Plot a networkx graph with node power information."""

    pos = nx.get_node_attributes(G, 'pos')

    # Couleurs des nœuds selon la puissance nette
    node_colors = []
    for n, data in G.nodes(data=True):
        if data.get("P", 0) < 0:
            node_colors.append("green")  # producteur
        elif data.get("P", 0) > 0:
            node_colors.append("red")  # consommateur
        else:
            node_colors.append("gray")  # neutre

    # Labels avec nom et puissance nette
    labels = {n: f"{data['label']}\nP={round(data.get('P', 0), 2)} p.u."
              for n, data in G.nodes(data=True)}

    plt.figure(figsize=(12, 8))

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

    edge_labels = nx.get_edge_attributes(G, 'type')
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=7)

    plt.title("Réseau électrique avec puissances (P_net en p.u.)")
    plt.axis("equal")
    plt.show()


def plot_power_flow(m, G, i, j):
    """Visualise power flows and nodal bounds for a given scenario."""

    pos = nx.get_node_attributes(G, 'pos')
    # Use node indices as labels
    labels = {}
    label_colors = [] # This is for node colors, will remove this later if needed or set to default
    for n in G.nodes():
        label_text = f"{n}"
        if n in m.parents:
            # Display parent bounds using the global P_min and P_max parameters
            label_text += f"\n[{m.P_min.value}, {m.P_max.value}]"
            # No specific color for label text here, use default
            label_colors.append('steelblue') # Default node color based on previous plots
        elif n in m.children:
            # Display children interval with smaller value first
            p_c_values = [m.P_C_set[n, 0].value, m.P_C_set[n, 1].value]
            label_text += f"\n[{round(min(p_c_values), 4)}, {round(max(p_c_values), 4)}]"
            # We will try to color this text red when drawing labels
            label_colors.append('steelblue') # Default node color
        else:
            label_colors.append('steelblue') # Default node color
        labels[n] = label_text


    plt.figure(figsize=(12, 8))

    edge_colors = []
    edge_labels = {}

    for u, v in G.edges():
        try:
            # Correct the sign of the flow value for plotting
            flow_value = m.F[u, v, i, j].value
            if flow_value is not None:
                edge_labels[(u, v)] = f"{round(flow_value, 4)}"
                if flow_value > 0:
                    edge_colors.append('blue')  # Positive flow (now correctly represents flow from u to v)
                elif flow_value < 0:
                    edge_colors.append('red')  # Negative (reverse) flow (now correctly represents flow from v to u)
                else:
                    edge_colors.append('gray') # No flow
            else:
                edge_colors.append('gray') # No flow value
        except:
            edge_colors.append('gray') # Handle cases where edge might not be in m.F

    # Draw the network
    nx.draw(
        G, pos,
        with_labels=False, # Draw labels separately for color control
        node_size=1200,
        edge_color=edge_colors, # Use the calculated edge colors
        edgecolors="black", font_size=8,
        alpha=0.85,
        node_color = label_colors # Apply node colors
    )

    # Draw labels with different colors
    for n in G.nodes():
        x, y = pos[n]
        text = labels[n]
        if n in m.children:
            plt.text(x, y - 0.1, text, fontsize=10, ha='center', va='top', color='red') # Color children interval red
        elif n in m.parents:
             plt.text(x, y + 0.1, text, fontsize=10, ha='center', va='bottom', color='black') # Color parent bounds black
        else:
             plt.text(x, y, text, fontsize=8, ha='center', va='center', color='black') # Default color for other labels


    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=7, label_pos=0.3)

    plt.title(f"Power Flow (per-unit) for i={i}, j={j}")
    plt.axis("equal")
    plt.show()


def plot_DOE(m, filename="Figures/Child_nodes_envelopes.pdf"):
    """Plot power envelope and DSO estimation for child nodes."""
    children = list(m.children)
    p0 = [getattr(m.P_C_set[n, 0], "value", m.P_C_set[n, 0]) for n in children]
    p1 = [getattr(m.P_C_set[n, 1], "value", m.P_C_set[n, 1]) for n in children]
    info = [getattr(m.info_DSO_param[n], "value", m.info_DSO_param[n]) for n in children]
    x = np.arange(len(children)) * 5e-4
    plt.figure(figsize=(5, 6))
    for xs, hi, lo in zip(x, p0, p1):
        plt.plot([xs, xs], [lo, hi], "o-", color="blue")
    plt.plot(x, info, "s", label="DSO power demand estimation")
    alpha = getattr(m, "alpha", None)
    beta = getattr(m, "beta", None)
    alpha_val = getattr(alpha, "value", alpha) if alpha is not None else None
    beta_val = getattr(beta, "value", beta) if beta is not None else None
    plt.plot([], [], "o-", color="blue",
             label=f"Power envelope ($\\alpha$={alpha_val}, $\\beta$={beta_val})")
    plt.xticks(x, children)
    plt.xlabel("Child Node Index")
    plt.ylabel("Power (in per-unit)")
    plt.legend(loc="upper left")
    plt.grid(True)
    plt.savefig(filename)
    plt.show()


def plot_alloc_alpha(
    test_case,
    operational_nodes=None,
    parent_nodes=None,
    children_nodes=None,
    beta: float = 1.0,
    alpha_min: float = 0.0,
    alpha_max: float = 1.0,
    alpha_step: float = 0.1,
    show: bool = True,
    filename: str = "Figures/DOE_alloc_alpha.pdf",
):
    """Run the optimisation for several ``alpha`` values and optionally plot the
    evolution of key metrics.

    The function repeatedly calls :func:`optimization.optim_problem` for
    ``alpha`` ranging from ``alpha_min`` to ``alpha_max`` (inclusive) with the
    provided step.  For each run, the envelope volume, the global curtailment
    and the deviation from the DSO estimation are recorded.  If ``show`` is
    ``True`` these metrics are plotted against ``alpha``.

    Parameters
    ----------
    test_case : str or pandapowerNet
        Network description passed to :func:`optimization.optim_problem`.
    operational_nodes, parent_nodes, children_nodes : iterable, optional
        Definition of the operational perimeter and boundary nodes used for the
        optimisation.
    beta : float, optional
        Fixed ``beta`` parameter for all optimisation runs.
    alpha_min, alpha_max : float, optional
        Bounds of the ``alpha`` sweep.
    alpha_step : float, optional
        Increment of ``alpha`` between two optimisation runs.
    show : bool, optional
        If ``True`` the resulting graph is displayed.  When ``False`` the
        function simply returns the collected metrics.
    filename : str, optional
        Name of the PDF file used when saving the plot.

    Returns
    -------
    dict
        A dictionary containing the list of ``alpha`` values and the
        corresponding metrics.
    """

    from optimization import optim_problem  # local import to avoid cycle

    alpha_values = np.arange(alpha_min, alpha_max + alpha_step, alpha_step)
    envelope, curtail, deviation, total = [], [], [], []

    for alpha in alpha_values:
        res = optim_problem(
            test_case,
            operational_nodes=operational_nodes,
            parent_nodes=parent_nodes,
            children_nodes=children_nodes,
            alpha=float(alpha),
            beta=beta,
            plot_doe=False,
        )["operational"]
        m = res["model"]
        # Extract the relevant metrics from the solved model
        envelope.append(float(m.tot_P.value))
        curtail.append(float(m.O.value))
        deviation.append(float(m.tot_diff_DSO.value))
        total.append(curtail[-1] + deviation[-1])

    if show:
        plt.figure(figsize=(10, 6))
        plt.plot(alpha_values, envelope, marker="o", linestyle="-", label="Envelope Volume")
        plt.plot(alpha_values, curtail, marker="x", linestyle="--", label="Curtailment")
        plt.plot(
            alpha_values,
            deviation,
            marker="s",
            linestyle="--",
            color="blue",
            label="Deviation of the center of the envelope from DSO estimation",
        )
        plt.plot(
            alpha_values,
            total,
            marker="^",
            linestyle=":",
            color="red",
            label="Deviation of the center of the envelope from DSO estimation + Envelope Volume",
        )
        plt.xlabel("$\\alpha$")
        plt.ylabel("Power (per-unit)")
        plt.title(
            "Evolution of the volume of the envelope, curtailment and closeness to DSO estimation as a function of parameter Alpha (beta={})".format(
                beta
            )
        )
        plt.legend()
        plt.grid(True)
        plt.savefig(filename)
        plt.show()

    return {
        "alpha": alpha_values.tolist(),
        "envelope": envelope,
        "curtailment": curtail,
        "deviation": deviation,
        "total": total,
    }
