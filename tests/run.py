"""Simple DOE.compute launcher.

P and Q values are expressed in per-unit (p.u.) and `network` refers to an
existing network definition file.
"""

from collections.abc import Iterable

from doe.compute import compute
from viz.plot_DOE import plot_DOE
from viz.plot_alloc_alpha import plot_alloc_alpha
from viz.plot_alloc_beta import plot_alloc_beta
from viz.plot_network import plot_network
from viz.plot_powerflow import plot_power_flow

P_min = -1.0
P_max = 1.0
Q_min = -1.0
Q_max = 1.0
alpha = 1
beta = 1
powerflow_mode = "DC"
network = "example_multivoltage_adapted.py"
objective = "global_sum"
operational_nodes = (0, 1, 2, 3, 4, 5)
parent_nodes = (0,)
children_nodes = (2, 3, 4)

# Optional plotting controls.
plot_network_enabled = False
plot_powerflow_full = False
plot_powerflow_operational = False
plot_doe_enabled = False
plot_alpha_enabled = False
plot_beta_enabled = False

# Plot configuration (used when the corresponding toggle above is True).
alpha_min = 1.0
alpha_max = 2.5
alpha_step = 0.1
beta_min = 0.5
beta_max = 2.5
beta_step = 0.1


def _as_iterable(value: Iterable | None) -> list:
    """Convert *value* to a list for downstream plotting helpers."""

    if value is None:
        return []
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        return list(value)
    return [value]


if __name__ == "__main__":
    compute_kwargs = dict(
        P_min=P_min,
        P_max=P_max,
        Q_min=Q_min,
        Q_max=Q_max,
        alpha=alpha,
        beta=beta,
        powerflow_mode=powerflow_mode,
        network=network,
        objective=objective,
        operational_nodes=operational_nodes,
        parent_nodes=parent_nodes,
        children_nodes=children_nodes,
    )

    result = compute(**compute_kwargs)

    if plot_alpha_enabled:
        plot_alloc_alpha(
            test_case=network,
            operational_nodes=_as_iterable(operational_nodes),
            parent_nodes=_as_iterable(parent_nodes),
            children_nodes=_as_iterable(children_nodes),
            beta=beta,
            alpha_min=alpha_min,
            alpha_max=alpha_max,
            alpha_step=alpha_step,
            P_min=P_min,
            P_max=P_max,
        )

    if plot_beta_enabled:
        plot_alloc_beta(
            test_case=network,
            operational_nodes=_as_iterable(operational_nodes),
            parent_nodes=_as_iterable(parent_nodes),
            children_nodes=_as_iterable(children_nodes),
            alpha=alpha,
            beta_min=beta_min,
            beta_max=beta_max,
            beta_step=beta_step,
            P_min=P_min,
            P_max=P_max,
        )

    full_graph = None
    operational_section = None
    full_section = None
    if isinstance(result, dict):
        full_graph = result.get("full_graph")
        operational_section = result.get("operational")
        full_section = result.get("full")

    if plot_network_enabled and full_graph is not None:
        plot_network(full_graph)

    if plot_powerflow_full and isinstance(full_section, dict):
        model = full_section.get("model")
        graph = full_section.get("graph")
        if model is not None and graph is not None:
            plot_power_flow(model, graph, 0, 0)

    if plot_powerflow_operational and isinstance(operational_section, dict):
        model = operational_section.get("model")
        graph = operational_section.get("graph")
        if model is not None and graph is not None:
            plot_power_flow(model, graph, 0, 0)

    if plot_doe_enabled and isinstance(operational_section, dict):
        model = operational_section.get("model")
        if model is not None:
            plot_DOE(model)
