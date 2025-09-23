"""Graph utilities for power network optimisation.

The graph is undirected but each edge (u, v) has a unique orientation
based on tuple order. Power sign convention: P < 0 production,
P > 0 consumption.
"""

import json
import math
from typing import Any, Dict, Iterable, Optional, Set
from collections import deque
import networkx as nx


def _maybe_float(value: Any) -> Optional[float]:
    """Return ``value`` converted to ``float`` when possible.

    Invalid entries such as ``None`` or ``NaN`` are mapped to ``None`` so that
    downstream callers can fall back to default values instead of propagating
    ``NaN`` in computations.
    """

    try:
        val = float(value)
    except (TypeError, ValueError):  # pragma: no cover - defensive path
        return None
    if math.isnan(val):
        return None
    return val


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

    s_base = float(getattr(net, "sn_mva", 100.0) or 100.0)

    # Gather nodal powers in MW / MVAr (per-unit conversion done later)
    P_load = {idx: 0.0 for idx in net.bus.index}
    P_gen = {idx: 0.0 for idx in net.bus.index}
    Q_load = {idx: 0.0 for idx in net.bus.index}
    Q_gen = {idx: 0.0 for idx in net.bus.index}
    for _, row in net.load.iterrows():
        bus = row["bus"]
        P_load[bus] += float(row.get("p_mw", 0.0))
        Q_load[bus] += float(row.get("q_mvar", 0.0))
    for _, row in net.gen.iterrows():
        bus = row["bus"]
        P_gen[bus] += -float(row.get("p_mw", 0.0))
        Q_gen[bus] += -float(row.get("q_mvar", 0.0))
    for _, row in net.sgen.iterrows():
        bus = row["bus"]
        P_gen[bus] += -float(row.get("p_mw", 0.0))
        Q_gen[bus] += -float(row.get("q_mvar", 0.0))
    for _, row in net.ext_grid.iterrows():
        bus = row["bus"]
        P_gen[bus] += -float(row.get("p_mw", 0.0))
        Q_gen[bus] += -float(row.get("q_mvar", 0.0))

    # Net nodal power: positive = consumption, negative = production
    P = {idx: P_load[idx] + P_gen[idx] for idx in net.bus.index}
    Q = {idx: Q_load[idx] + Q_gen[idx] for idx in net.bus.index}

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
        "Q_load": Q_load,
        "Q_gen": Q_gen,
        "Q": Q,
    }


def build_graph_from_data(data: Dict[str, Any]) -> nx.Graph:
    """Build a ``networkx.Graph`` from extracted data.

    Nodal powers provided in ``data`` are in MW and converted to per-unit here.
    Line reactances are given in ohms, base power in MVA, voltage base in kV.
    Susceptance in per-unit is computed as ``b_pu = V_base^2 / (S_base * X_ohm)``.
    """

    G = nx.Graph()

    # Nodes (powers converted to per-unit)
    s_base = data["s_base"]
    for idx, row in data["bus"].iterrows():
        vmin = _maybe_float(row.get("min_vm_pu"))
        vmax = _maybe_float(row.get("max_vm_pu"))
        G.add_node(
            idx,
            label=row["name"],
            pos=data["pos"][idx],
            vn_kv=row["vn_kv"],
            P_load=data["P_load"][idx] / s_base,
            P_gen=data["P_gen"][idx] / s_base,
            P=data["P"][idx] / s_base,
            Q_load=data["Q_load"][idx] / s_base,
            Q_gen=data["Q_gen"][idx] / s_base,
            Q=data["Q"][idx] / s_base,
            V_min_pu=vmin,
            V_max_pu=vmax,
        )

    # Lines
    for _, row in data["line"].iterrows():
        u, v = row["from_bus"], row["to_bus"]
        length = float(row.get("length_km", 0.0))
        x_ohm = float(row.get("x_ohm_per_km", 0.0)) * length
        r_ohm = float(row.get("r_ohm_per_km", 0.0)) * length
        V_kv = float(data["bus"].at[u, "vn_kv"])
        if math.isclose(x_ohm, 0.0):
            raise ValueError(f"Line ({u},{v}) has zero reactance")
        z_base = V_kv**2 / s_base if s_base else 0.0
        R_pu = r_ohm / z_base if z_base else 0.0
        X_pu = x_ohm / z_base if z_base else 0.0
        b_pu = V_kv**2 / (x_ohm * s_base)
        max_i_ka = row.get("max_i_ka")
        base_i_ka = s_base / (math.sqrt(3) * V_kv)
        if max_i_ka is not None and not math.isnan(max_i_ka):
            I_max_pu = max_i_ka / base_i_ka
        else:
            I_max_pu = 10

        I_min_pu = -I_max_pu
        G.add_edge(
            u,
            v,
            type="line",
            name=row.get("name"),
            length=row["length_km"],
            std_type=row.get("std_type"),
            x_ohm=x_ohm,
            r_ohm=r_ohm,
            max_i_ka=max_i_ka,
            b_pu=b_pu,
            I_min_pu=I_min_pu,
            I_max_pu=I_max_pu,
            R=R_pu,
            X=X_pu,
        )

    # Transformers
    for _, row in data["trafo"].iterrows():
        u, v = row["hv_bus"], row["lv_bus"]
        name = row.get("name")
        sn_mva = _maybe_float(row.get("sn_mva"))
        vn_hv = _maybe_float(row.get("vn_hv_kv", data["bus"].at[u, "vn_kv"]))
        vk_percent = _maybe_float(row.get("vk_percent"))
        vkr_percent = _maybe_float(row.get("vkr_percent"))

        R_pu = None
        X_pu = None
        if sn_mva and vn_hv and vk_percent:
            z_trafobase = (vn_hv**2) / sn_mva
            r_ohm = (vkr_percent or 0.0) / 100.0 * z_trafobase
            z_ohm = vk_percent / 100.0 * z_trafobase
            x_ohm_sq = max(z_ohm**2 - r_ohm**2, 0.0)
            x_ohm = math.sqrt(x_ohm_sq)
            z_base = (vn_hv**2) / s_base if s_base else 0.0
            if z_base:
                R_pu = r_ohm / z_base
                X_pu = x_ohm / z_base

        G.add_edge(
            u,
            v,
            type="trafo",
            name=name,
            std_type=None,
            b_pu=None,
            max_i_ka=None,
            R=R_pu,
            X=X_pu,
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
                    R=None,
                    X=None,
                )
    return G


def create_graph(net: Any) -> nx.Graph:
    """Facade creating a graph from a pandapower network."""
    data = extract_network_data(net)
    return build_graph_from_data(data)


def build_nx_from_pandapower(net: Any) -> nx.Graph:
    """Backward compatible alias returning :func:`create_graph`."""

    return create_graph(net)


# Existing helpers remain unchanged

def op_graph(full_graph: nx.Graph, operational_nodes: Set[int]) -> nx.Graph:
    """Return the subgraph induced by ``operational_nodes``."""
    return full_graph.subgraph(operational_nodes).copy()


def compute_info_dso(
    G: nx.Graph,
    operational_nodes: Iterable[int],
    children_nodes: Iterable[int],
    p_attr: str = "P",
) -> Dict[int, float]:
    """
    Calcule info_DSO[c] pour chaque enfant c du sous-réseau opérationnel.

    Règle: info_DSO[c] = P(c) + somme des P des noeuds externes
           atteignables depuis c via des arêtes qui sortent du sous-réseau,
           en restant en dehors du sous-réseau lors de l'exploration.

    Paramètres
    ----------
    G : nx.Graph
        Graphe électrique (avec G.nodes[n][p_attr] disponible).
    operational_nodes : Iterable[int]
        Nœuds du sous-réseau opérationnel (contrôlé).
    children_nodes : Iterable[int]
        Nœuds enfants à la frontière du sous-réseau.
    p_attr : str
        Nom de l’attribut puissance sur les nœuds (par défaut "P").

    Retour
    ------
    Dict[int, float]
        Dictionnaire {enfant -> demande/injection agrégée}.
    """
    op_set: Set[int] = set(operational_nodes)
    children_set: Set[int] = set(children_nodes)

    def node_power(n: int) -> float:
        # Par sûreté: 0.0 si l'attribut n'est pas présent
        return float(G.nodes[n].get(p_attr, 0.0))

    info: Dict[int, float] = {}

    for c in children_set:
        total = node_power(c)
        seen = {c}

        # Pour chaque voisin hors sous-réseau, explorer UNIQUEMENT hors sous-réseau
        for v in G.neighbors(c):
            if v in op_set or v in seen:
                continue  # reste dans le périmètre ou déjà exploré

            # BFS sur la composante externe atteignable depuis v sans
            # re-rentrer dans le sous-réseau
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