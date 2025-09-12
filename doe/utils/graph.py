"""Utilities for building NetworkX graphs from pandapower networks."""

from __future__ import annotations

from typing import Any
import networkx as nx


def build_nx_from_pandapower(net: Any) -> nx.Graph:
    """Return a :class:`networkx.Graph` representation of a pandapower network.

    The function expects a ``pandapowerNet`` and extracts the buses and lines
    into a simple undirected graph. Only a subset of fields is kept: bus voltage
    levels (``vn_kv``) and per-unit active power ``P`` (positive for demand,
    negative for generation). Line data keeps the per-unit susceptance
    ``b_pu`` and current limits ``I_min_pu``/``I_max_pu`` when available.

    Parameters
    ----------
    net:
        Pandapower network to convert. The object must provide the standard
        ``bus``, ``line``, ``load`` and ``gen`` tables from pandapower.

    Returns
    -------
    networkx.Graph
        Undirected graph matching the electric topology of ``net``.
    """

    if not hasattr(net, "bus") or not hasattr(net, "line"):
        raise TypeError("Only pandapowerNet is supported")

    s_base = getattr(net, "sn_mva", 100.0)
    G = nx.Graph()

    # Nodes with aggregated power injection
    P = {idx: 0.0 for idx in net.bus.index}
    for _, row in getattr(net, "load", []).iterrows():
        P[row["bus"]] += row.get("p_mw", 0.0) / s_base
    for _, row in getattr(net, "gen", []).iterrows():
        P[row["bus"]] += -row.get("p_mw", 0.0) / s_base
    for _, row in getattr(net, "sgen", []).iterrows():
        P[row["bus"]] += -row.get("p_mw", 0.0) / s_base
    for _, row in getattr(net, "ext_grid", []).iterrows():
        P[row["bus"]] += -row.get("p_mw", 0.0) / s_base

    for idx, row in net.bus.iterrows():
        G.add_node(idx, vn_kv=float(row["vn_kv"]), P=P[idx])

    # Lines with approximate susceptance and current limits
    for _, row in net.line.iterrows():
        u, v = int(row["from_bus"]), int(row["to_bus"])
        x_ohm = float(row.get("x_ohm_per_km", 0.0)) * float(row.get("length_km", 0.0))
        vn_kv = float(net.bus.at[u, "vn_kv"]) if x_ohm else 1.0
        b_pu = vn_kv ** 2 / (x_ohm * s_base) if x_ohm else 0.0
        max_i_ka = row.get("max_i_ka")
        if max_i_ka is not None:
            base_i_ka = s_base / (3 ** 0.5 * vn_kv)
            I_max_pu = max_i_ka / base_i_ka
        else:
            I_max_pu = 1e3
        G.add_edge(u, v, type="line", b_pu=b_pu, I_min_pu=-I_max_pu, I_max_pu=I_max_pu)

    return G
