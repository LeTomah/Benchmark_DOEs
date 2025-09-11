"""Network loading utilities."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable

import networkx as nx

from ..utils.logging import get_logger


@dataclass
class NetworkData:
    """Simple container for network related data."""

    graph: nx.Graph
    parents: Iterable[int]
    children: Iterable[int]
    info_dso: Dict[int, float]


def load(network: Any, logger=None) -> NetworkData:
    """Load a network from an object or identifier.

    Args:
        network: Either a pre-built :class:`networkx.Graph` or the string
            ``"toy"`` for a built-in tiny example.
        logger: Optional logger instance.

    Returns:
        :class:`NetworkData` describing the network.

    Raises:
        ValueError: If the network specification is unsupported.
    """

    logger = logger or get_logger()

    if isinstance(network, nx.Graph):
        parents = [0] if network.nodes else []
        children = [n for n in network.nodes if n not in parents]
        info = {n: network.nodes[n].get("info_DSO", 0.0) for n in children}
        return NetworkData(network, parents, children, info)

    if isinstance(network, str) and network == "toy":
        g = nx.Graph()
        g.add_node(0, P=0.0)
        g.add_node(1, P=0.0)
        g.add_edge(0, 1, b_pu=1.0, I_min_pu=-1.0, I_max_pu=1.0, type="line")
        parents = [0]
        children = [1]
        info = {1: 0.0}
        logger.info("Loaded built-in toy network")
        return NetworkData(g, parents, children, info)

    raise ValueError("Unsupported network specification")
