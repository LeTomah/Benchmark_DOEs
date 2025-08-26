"""Graph utilities for power network optimisation.

The graph is undirected but each edge (u, v) has a unique orientation
based on tuple order. Power sign convention: P < 0 production,
P > 0 consumption.
"""

import json
import math
from typing import Any, Dict, Iterable, Set

import networkx as nx


def extract_network_data(net: Any) -> Dict[str, Any]:
    """Extract and validate raw data from a pandapower network."""

    if "geo" in net.bus.columns:
        pos: Dict[int, tuple] = {}
        for idx, geo in net.bus["geo"].items():
            try:
                if isinstance(geo, str):
                    geo = json.loads(geo)
                coords = geo.get("coordinates") if isinstance(geo, dict) else None
                if isinstance(coords, (list, tuple)) and len(coords) == 2:
                    pos[idx] = (float(coords[0]), float(coords[1]))
            except Exception as exc:  # pragma: no cover - validation path
                raise ValueError(f"Invalid geo data for bus {idx}") from exc
        if len(pos) != len(net.bus):
            raise ValueError("Bus coordinates missing for some nodes")
    elif hasattr(net, "bus_geodata"):
        pos = {
            idx: (float(row["x"]), float(row["y"]))
            for idx, row in net.bus_geodata.iterrows()
        }
        if len(pos) != len(net.bus):
            raise ValueError("Incomplete bus_geodata for all buses")
    else:
        raise AttributeError("Bus positions not available in network.")

    s_base = getattr(net, "sn_mva", 100.0)

    # Gather nodal powers
    P_load = {idx: 0.0 for idx in net.bus.index}
    P_gen = {idx: 0.0 for idx in net.bus.index}
    for _, row in net.load.iterrows():
        P_load[row["bus"]] += row["p_mw"] / s_base
    for _, row in net.gen.iterrows():
        P_gen[row["bus"]] += row["p_mw"] / s_base
    for _, row in net.sgen.iterrows():
        P_gen[row["bus"]] += row["p_mw"] / s_base
    for _, row in net.ext_grid.iterrows():
        P_gen[row["bus"]] += 70.0 / s_base
    P = {idx: P_load[idx] - P_gen[idx] for idx in net.bus.index}

    return {
        "pos": pos,
        "s_base": s_base,
        "bus": net.bus.copy(),
        "line": net.line.copy(),
        "trafo": net.trafo.copy(),
        "trafo3w": getattr(net, "trafo3w", None),
        "P_load": P_load,
        "P_gen": P_gen,
        "P": P,
    }


def build_graph_from_data(data: Dict[str, Any]) -> nx.Graph:
    """Build a ``networkx.Graph`` from extracted data.

    Line reactances are given in ohms, base power in MVA, voltage base in kV.
    Susceptance in per-unit is computed as ``b_pu = V_base^2 / (S_base * X_ohm)``.
    """

    G = nx.Graph()
    G.graph["s_base"] = data["s_base"]

    # Nodes
    for idx, row in data["bus"].iterrows():
        G.add_node(
            idx,
            label=row["name"],
            pos=data["pos"][idx],
            vn_kv=row["vn_kv"],
            P_load=data["P_load"][idx],
            P_gen=data["P_gen"][idx],
            P=data["P"][idx],
        )

    # Lines
    for _, row in data["line"].iterrows():
        u, v = row["from_bus"], row["to_bus"]
        x_ohm = row["x_ohm_per_km"] * row["length_km"]
        V_kv = data["bus"].at[u, "vn_kv"]
        b_pu = V_kv**2 / (x_ohm * data["s_base"])
        G.add_edge(
            u,
            v,
            type="line",
            name=row.get("name"),
            length=row["length_km"],
            std_type=row.get("std_type"),
            x_ohm=x_ohm,
            max_i_ka=row.get("max_i_ka"),
            b_pu=b_pu,
        )

    # Transformers
    for _, row in data["trafo"].iterrows():
        u, v = row["hv_bus"], row["lv_bus"]
        G.add_edge(
            u,
            v,
            type="trafo",
            name=row.get("name"),
            std_type=None,
            b_pu=None,
            max_i_ka=None,
        )

    trafo3w = data.get("trafo3w")
    if trafo3w is not None and len(trafo3w):
        for _, row in trafo3w.iterrows():
            hv, mv, lv = row["hv_bus"], row["mv_bus"], row["lv_bus"]
            name = row.get("name", "trafo3w")
            for a, b, suffix in [(hv, mv, "hv_mv"), (hv, lv, "hv_lv")]:
                G.add_edge(
                    a,
                    b,
                    type="trafo3w",
                    name=f"{name}_{suffix}",
                    std_type=None,
                    b_pu=None,
                    max_i_ka=None,
                )
    return G


def create_graph(net: Any) -> nx.Graph:
    """Facade creating a graph from a pandapower network."""
    data = extract_network_data(net)
    return build_graph_from_data(data)


# Existing helpers remain unchanged

def calculate_current_bounds(G, max_i_ka, v_base):
    """Compute current limits in per-unit from network data."""
    base_i_ka = G.graph["s_base"] / (math.sqrt(3) * v_base)
    if max_i_ka is not None and not math.isnan(max_i_ka):
        I_max = max_i_ka / base_i_ka
        I_min = -I_max
        return I_min, I_max
    return -1000, 1000, base_i_ka


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
            if v not in op_set:
                total += node_power(v)
        info[c] = total
    return info

