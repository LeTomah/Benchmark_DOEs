"""Utilities to load pandapower networks from disk."""
from __future__ import annotations

from dataclasses import dataclass
from importlib import util as importlib_util
from pathlib import Path
from typing import Iterable, Any, Dict

import networkx as nx
import pandapower as pp

from ..utils.logging import get_logger


NETWORKS_DIR = Path(__file__).resolve().parents[2] / "networks"


@dataclass
class NetworkData:
    """Container for network information used by the optimisation model."""

    graph: nx.Graph
    parents: Iterable[int]
    children: Iterable[int]
    operational_nodes: Iterable[int]
    info_dso: Dict[int, float]


def _pp_to_nx(net: pp.pandapowerNet) -> nx.Graph:
    """Convert a pandapower network to a simple :class:`networkx.Graph`.

    The graph contains buses as nodes and lines as edges with minimal attributes
    required by the rest of the library.
    """

    G = nx.Graph()
    for bus in net.bus.itertuples():
        G.add_node(bus.Index, P=float(getattr(bus, "P", 0.0)))

    for line in net.line.itertuples():
        G.add_edge(
            int(line.from_bus),
            int(line.to_bus),
            b_pu=1.0,  # placeholder susceptance
            I_min_pu=-1.0,
            I_max_pu=1.0,
            type="line",
        )
    return G


def load(
    network: Any,
    *,
    parents: Iterable[int] | None = None,
    children: Iterable[int] | None = None,
    operational_nodes: Iterable[int] | None = None,
    logger=None,
) -> NetworkData:
    """Load a pandapower network from an object or file name.

    Args:
        network: Either a ``pandapowerNet`` instance or the name of a file stored
            in the repository level ``networks`` directory. JSON files are loaded
            via :func:`pandapower.from_json` while Python modules must provide a
            ``load()`` function returning a network.
        parents: Optional iterable of parent node indices.
        children: Optional iterable of child node indices.
        operational_nodes: Optional iterable of operational node indices.
        logger: Optional logger instance.

    Returns:
        :class:`NetworkData` object describing the network.

    Raises:
        ValueError: If the network specification is unsupported or the file is
            missing.
    """

    logger = logger or get_logger()

    if isinstance(network, pp.pandapowerNet):
        net = network
    elif isinstance(network, str):
        path = NETWORKS_DIR / network
        if not path.exists():
            raise ValueError(f"Network file '{network}' not found in {NETWORKS_DIR}")
        if path.suffix == ".json":
            net = pp.from_json(path.as_posix())
        elif path.suffix == ".py":
            spec = importlib_util.spec_from_file_location(path.stem, path)
            module = importlib_util.module_from_spec(spec)
            assert spec.loader is not None
            spec.loader.exec_module(module)
            if not hasattr(module, "load"):
                raise ValueError("Network module must define a load() function")
            net = module.load()
        else:
            raise ValueError("Unsupported network file type")
    else:  # pragma: no cover - defensive
        raise ValueError("Unsupported network specification")

    G = _pp_to_nx(net)
    all_nodes = list(G.nodes)
    parents = list(parents) if parents is not None else ([all_nodes[0]] if all_nodes else [])
    children = list(children) if children is not None else [n for n in all_nodes if n not in parents]
    operational_nodes = list(operational_nodes) if operational_nodes is not None else all_nodes

    info = {n: float(net.bus.at[n, "info_DSO"]) if "info_DSO" in net.bus.columns else 0.0 for n in children}

    logger.info("Loaded network with %d nodes and %d lines", len(all_nodes), len(net.line))
    return NetworkData(G, parents, children, operational_nodes, info)

