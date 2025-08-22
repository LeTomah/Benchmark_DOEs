from __future__ import annotations

"""Utility functions for plotting electrical networks."""

from pathlib import Path
from typing import Dict, Hashable, Optional, Tuple

import matplotlib.pyplot as plt
import networkx as nx

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


def draw_network(
    G: nx.Graph,
    pos: Optional[Pos] = None,
    node_size: int = 120,
    edge_width: float = 1.2,
    edge_alpha: float = 0.8,
    with_labels: bool = True,
    label_attr: str = "label",
) -> plt.Axes:
    """Draw ``G`` with visible edges and node labels.

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

    arrows = G.is_directed()

    edge_kwargs = dict(width=edge_width, alpha=edge_alpha, arrows=arrows)
    if arrows:
        edge_kwargs.update(arrowstyle="-|>", arrowsize=10)
    edge_collection = nx.draw_networkx_edges(
        G,
        pos,
        ax=ax,
        **edge_kwargs,
    )
    if edge_collection is not None:
        if isinstance(edge_collection, list):
            for collection in edge_collection:
                collection.set_zorder(1)
        else:
            edge_collection.set_zorder(1)

    node_collection = nx.draw_networkx_nodes(
        G,
        pos,
        node_size=node_size,
        ax=ax,
    )
    if node_collection is not None:
        node_collection.set_zorder(2)

    if with_labels:
        labels = {n: G.nodes[n].get(label_attr, n) for n in G.nodes}
        nx.draw_networkx_labels(G, pos, labels=labels, font_size=8, ax=ax)

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
        graph_list = list(graphs.values())
        base = graph_list[0].copy()
        for g in graph_list[1:]:
            base = nx.compose(base, g)
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
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=dpi)
