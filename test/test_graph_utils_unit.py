"""Unit tests for :mod:`doe.utils.graph` helper functions."""

import math
import pathlib
import sys

import networkx as nx
import pytest


ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from doe.utils.graph import (  # noqa: E402  (path injected above)
    build_graph_from_data,
    build_nx_from_pandapower,
    compute_info_P,
    create_graph,
    extract_network_data,
    op_graph,
    _maybe_float,
)
from data.networks import network_test  # noqa: E402


@pytest.fixture(scope="module")
def example_network():
    """Provide the demo pandapower network for the graph helpers."""

    return network_test.build()


@pytest.fixture(scope="module")
def extracted_data(example_network):
    """Return the cached data extracted from the pandapower network."""

    return extract_network_data(example_network)


def test_maybe_float_with_valid_values():
    """Valid inputs should convert to floating point numbers."""

    value = _maybe_float("3.14")
    print(f"_maybe_float('3.14') -> {value}")
    assert value == pytest.approx(3.14)

    integer_value = _maybe_float(5)
    print(f"_maybe_float(5) -> {integer_value}")
    assert integer_value == pytest.approx(5.0)


def test_maybe_float_with_invalid_values():
    """Invalid entries should gracefully return ``None``."""

    invalid = _maybe_float("not-a-number")
    assert invalid is None
    print(f"_maybe_float('not-a-number') -> {invalid}")

    nan_value = _maybe_float(math.nan)
    assert nan_value is None
    print(f"_maybe_float(math.nan) -> {nan_value}")


def test_extract_network_data_returns_expected_keys(extracted_data):
    """The extraction helper should return all required tables."""

    print(
        "extract_network_data -> keys:",
        sorted(extracted_data.keys()),
    )
    for key in ["pos", "s_base", "bus", "line", "P", "Q"]:
        assert key in extracted_data
    assert extracted_data["bus"].shape[0] == len(extracted_data["pos"])


def test_build_graph_from_data_matches_network_size(extracted_data):
    """Graph construction should respect bus count and produce edges."""

    graph = build_graph_from_data(extracted_data)
    print(
        "build_graph_from_data -> nodes/edges:",
        graph.number_of_nodes(),
        graph.number_of_edges(),
    )
    assert graph.number_of_nodes() == len(extracted_data["bus"])
    assert graph.number_of_edges() > 0


def test_create_graph_equivalent_to_manual_build(example_network, extracted_data):
    """``create_graph`` should provide the same topology as manual building."""

    graph_auto = create_graph(example_network)
    graph_manual = build_graph_from_data(extracted_data)
    print(
        "create_graph -> nodes/edges:",
        graph_auto.number_of_nodes(),
        graph_auto.number_of_edges(),
    )
    assert graph_auto.number_of_nodes() == graph_manual.number_of_nodes()
    assert graph_auto.number_of_edges() == graph_manual.number_of_edges()


def test_build_nx_from_pandapower_alias(example_network):
    """The backward compatibility alias should delegate to ``create_graph``."""

    graph = build_nx_from_pandapower(example_network)
    print(
        "build_nx_from_pandapower -> nodes/edges:",
        graph.number_of_nodes(),
        graph.number_of_edges(),
    )
    assert isinstance(graph, nx.Graph)


def test_op_graph_returns_induced_subgraph(example_network):
    """Subgraph helper should keep only the requested nodes."""

    full_graph = create_graph(example_network)
    selected_nodes = set(list(full_graph.nodes)[:3])
    sub = op_graph(full_graph, selected_nodes)
    print("op_graph -> nodes:", sorted(sub.nodes))
    assert set(sub.nodes) == selected_nodes


def test_compute_info_dso_on_synthetic_graph():
    """The BFS aggregation should only cover the external area."""

    G = nx.Graph()
    G.add_nodes_from(
        [
            (1, {"P": 0.0}),
            (2, {"P": 0.0}),
            (3, {"P": 0.5}),
            (4, {"P": 2.0}),
            (5, {"P": -0.5}),
        ]
    )
    G.add_edges_from([(1, 3), (2, 3), (3, 4), (4, 5)])

    info = compute_info_P(G, {1, 2}, {3})
    print("compute_info_dso ->", info)
    assert info == {3: pytest.approx(2.0)}
