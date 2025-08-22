from __future__ import annotations

"""Utility functions for plotting electrical networks."""

from pathlib import Path
import os
from typing import Dict, Hashable, Iterable, Optional, Tuple

import matplotlib.pyplot as plt
import networkx as nx
from matplotlib.patches import Patch

Pos = Dict[Hashable, Tuple[float, float]]


def get_or_compute_pos(G: nx.Graph, layout: str = "spring") -> Pos:
    """Return a dict mapping each node to an ``(x, y)`` position.

    Parameters
    ----------
    G : nx.Graph
        Graph whose node positions are required.
    layout : str, optional
        Name of the fallback layout to compute when positions are missing.
        Supported values are ``"spring"`` (default), ``"kamada"`` and
        ``"planar"``. ``"planar"`` falls back to ``"spring"`` if the graph is
        not planar.

    Returns
    -------
    Pos
        Mapping ``{node: (x, y)}`` for every node in ``G``.

    Raises
    ------
    ValueError
        If positions cannot be determined for all nodes.
    """

    pos: Pos = nx.get_node_attributes(G, "pos")
    if len(pos) != G.number_of_nodes() or any(len(v) != 2 for v in pos.values()):
        layout_funcs = {
            "spring": nx.spring_layout,
            "kamada": nx.kamada_kawai_layout,
            "planar": nx.planar_layout,
        }
        layout_func = layout_funcs.get(layout, nx.spring_layout)
        try:
            pos = layout_func(G)
        except Exception:
            pos = nx.spring_layout(G)

    if len(pos) != G.number_of_nodes():
        missing = set(G.nodes()) - set(pos)
        raise ValueError(f"Positions missing for nodes: {missing}")
    return pos


def classify_nodes(G: nx.Graph) -> Dict[str, Iterable[Hashable]]:
    """Classify nodes of ``G`` into producers and consumers.

    Parameters
    ----------
    G : nx.Graph
        Graph whose nodes are classified.

    Returns
    -------
    dict
        Dictionary with keys ``"producers"`` and ``"consumers"`` containing
        iterables of node identifiers.
    """

    producers = []
    consumers = []
    for n, data in G.nodes(data=True):
        if data.get("is_generator") is True:
            producers.append(n)
        elif data.get("type") in {"gen", "generator", "slack"}:
            producers.append(n)
        elif data.get("p_mw", 0) > 0:
            producers.append(n)
        elif data.get("p_mw", 0) < 0:
            consumers.append(n)
        else:
            consumers.append(n)
    return {"producers": producers, "consumers": consumers}


def draw_network(
    G: nx.Graph,
    pos: Optional[Pos] = None,
    node_size: int = 120,
    edge_width: float = 1.2,
    edge_alpha: float = 0.8,
    with_labels: bool = True,
    label_attr: str = "label",
) -> plt.Axes:
    """Draw ``G`` with producers in green and consumers in red.

    Parameters
    ----------
    G : nx.Graph
        Graph to draw.
    pos : dict, optional
        Mapping of node positions. If ``None`` or incomplete, a layout is
        computed via :func:`get_or_compute_pos`.
    node_size : int, optional
        Size of the nodes (default ``120``).
    edge_width : float, optional
        Width of the edges (default ``1.2``).
    edge_alpha : float, optional
        Transparency applied to edges (default ``0.8``).
    with_labels : bool, optional
        Whether to draw node labels (default ``True``).
    label_attr : str, optional
        Node attribute used for labels when available (default ``"label"``).

    Returns
    -------
    matplotlib.axes.Axes
        Axes on which the graph is drawn.
    """

    if pos is None or set(pos) != set(G.nodes()):
        pos = get_or_compute_pos(G)

    ax = plt.gca()

    classification = classify_nodes(G)
    arrows = G.is_directed()

    edge_kwargs = dict(width=edge_width, alpha=edge_alpha, arrows=arrows)
    if arrows:
        edge_kwargs.update(arrowstyle='-|>', arrowsize=10)
    edge_collection = nx.draw_networkx_edges(
        G,
        pos,
        ax=ax,
        **edge_kwargs,
    )
    if edge_collection is not None:
        edge_collection.set_zorder(1)

    producer_nodes = nx.draw_networkx_nodes(
        G,
        pos,
        nodelist=list(classification["producers"]),
        node_color="green",
        node_size=node_size,
        ax=ax,
    )
    if producer_nodes is not None:
        producer_nodes.set_zorder(2)

    consumer_nodes = nx.draw_networkx_nodes(
        G,
        pos,
        nodelist=list(classification["consumers"]),
        node_color="red",
        node_size=node_size,
        ax=ax,
    )
    if consumer_nodes is not None:
        consumer_nodes.set_zorder(2)

    if with_labels:
        labels = {n: G.nodes[n].get(label_attr, n) for n in G.nodes}
        nx.draw_networkx_labels(G, pos, labels=labels, font_size=8, ax=ax)

    handles = [
        Patch(color="green", label="Producer"),
        Patch(color="red", label="Consumer"),
    ]
    ax.legend(handles=handles)
    ax.set_axis_off()
    ax.figure.tight_layout()
    return ax


def draw_side_by_side(
    graphs: Dict[str, nx.Graph],
    layout: str = "spring",
    common_pos: bool = True,
) -> plt.Figure:
    """Display several graphs side by side.

    Parameters
    ----------
    graphs : dict
        Mapping ``{title: graph}`` of graphs to display.
    layout : str, optional
        Layout algorithm name used when computing positions.
    common_pos : bool, optional
        If ``True``, compute node positions on the union of nodes to stabilise
        the comparison (default ``True``).

    Returns
    -------
    matplotlib.figure.Figure
        Figure containing all subplots.
    """

    if not graphs:
        raise ValueError("No graphs provided")

    names = list(graphs.keys())
    fig, axes = plt.subplots(1, len(names), figsize=(5 * len(names), 4))
    if len(names) == 1:
        axes = [axes]

    if common_pos:
        base = nx.Graph() if not next(iter(graphs.values())).is_directed() else nx.DiGraph()
        for g in graphs.values():
            base.add_nodes_from(g.nodes())
            base.add_edges_from(g.edges())
        pos_all = get_or_compute_pos(base, layout=layout)
        positions = {name: {n: pos_all[n] for n in g.nodes()} for name, g in graphs.items()}
    else:
        positions = {name: get_or_compute_pos(g, layout=layout) for name, g in graphs.items()}

    for ax, name in zip(axes, names):
        plt.sca(ax)
        draw_network(graphs[name], pos=positions[name])
        ax.set_title(name)

    fig.tight_layout()
    return fig


def save_figure(fig: plt.Figure, path: str, dpi: int = 150) -> None:
    """Save ``fig`` to ``path`` creating parent directories if needed."""

    out_path = Path(path)
    if out_path.parent:
        os.makedirs(out_path.parent, exist_ok=True)
    fig.savefig(out_path, dpi=dpi)
