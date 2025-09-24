from dataclasses import dataclass
from typing import Any, Dict, Set

import networkx as nx


@dataclass
class RunConfig:
    """Configuration required to run an optimisation experiment."""
    network_path: str
    operational_nodes: Set[int]
    parent_nodes: Set[int]
    children_nodes: Set[int]
    opf_only: bool  # True => on s’arrête après l’OPF full graph


@dataclass
class GraphBundle:
    """Bundle gathering the network graph and optional node metadata."""
    full_graph: nx.DiGraph
    node_attrs: Dict[int, Dict[str, Any]]  # si besoin de méta


@dataclass
class EnvPyo:
    """Container used to exchange the Pyomo graph representation and data."""
    graph: nx.DiGraph
    data: Dict[str, Any]  # tout ce qu’il faut pour Pyomo (sets, params…)


@dataclass
class OPFResult:
    """Summary of an OPF run including flows, voltages and objective."""
    graph: nx.DiGraph
    node_voltages: Dict[int, float]
    node_angles: Dict[int, float]
    flows: Dict[tuple, float]  # (u,v) -> P_ij
    objective: float
    status: str


# Info résumée pour DSO (enfants)
InfoDSO = Dict[int, Dict[str, float]]  # {child: {"P_in":..., "Q_in":..., "V":...}}
