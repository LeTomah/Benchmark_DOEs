"""Sweep beta values and plot resulting metrics."""

from itertools import cycle

import matplotlib.pyplot as plt
import numpy as np
import scienceplots  # noqa: F401
from matplotlib.legend_handler import HandlerTuple
from matplotlib.lines import Line2D

plt.style.use(["science", "no-latex"])


def plot_alloc_beta(
    test_case,
    operational_nodes=None,
    parent_nodes=None,
    children_nodes=None,
    alpha: float = 1.0,
    beta_min: float = 0.0,
    beta_max: float = 1.0,
    beta_step: float = 0.1,
    P_min: float = -1.0,
    P_max: float = 1.0,
    show: bool = True,
    filename: str = "figures/Plot_beta.pdf",
):
    """Run the optimisation for several ``beta`` values and optionally plot metrics.

    Parameters
    ----------
    test_case : str or pandapowerNet
        Network description passed to :func:`core.optimization.optim_problem`.
    operational_nodes, parent_nodes, children_nodes : iterable, optional
        Subsets describing the operational perimeter and its boundaries.
    alpha : float, optional
        Weight applied to the curtailment budget in the DOE objective.
    beta_min, beta_max : float, optional
        Lower and upper bounds of the scanned ``beta`` range.
    beta_step : float, optional
        Increment applied between successive ``beta`` values.
    P_min, P_max : float, optional
        Bounds on the power exchanged with parent nodes.
    show : bool, optional
        If ``True`` display the resulting plot.
    filename : str, optional
        Destination path for the saved PDF figure.

    Returns
    -------
    dict
        Dictionary with sampled ``beta`` values and associated metrics
        (envelope, curtailment, deviation and total).
    """

    from core.optimization import optim_problem  # local import to avoid cycle

    beta_values = np.arange(beta_min, beta_max + beta_step, beta_step)
    envelope, curtail, deviation, total = [], [], [], []

    for beta in beta_values:
        res = optim_problem(
            test_case,
            operational_nodes=operational_nodes,
            parent_nodes=parent_nodes,
            children_nodes=children_nodes,
            alpha=alpha,
            beta=float(beta),
            P_min=P_min,
            P_max=P_max,
            plot_doe=False,
        )["operational"]
        m = res["model"]
        envelope.append(float(m.envelope_volume.value))
        curtail.append(float(m.curtailment_budget.value))
        deviation.append(float(m.envelope_center_gap.value))
        total.append(envelope[-1] + deviation[-1])

    if show:
        beta_values_np = np.array(beta_values)
        envelope_np = np.array(envelope, dtype=float)
        curtail_np = np.array(curtail, dtype=float)
        deviation_np = np.array(deviation, dtype=float)
        total_np = np.array(total, dtype=float)

        plt.figure(figsize=(8, 5))

        # Envelope Volume (BLUE)
        plt.plot(
            beta_values_np,
            envelope_np,
            marker="o",
            markersize=4,
            linestyle="-",
            color="blue",
            label="Envelope Volume",
        )

        # Curtailment (ORANGE)
        plt.plot(
            beta_values_np,
            curtail_np,
            marker="x",
            markersize=4,
            linestyle="--",
            color="orange",
            label="Curtailment",
        )

        # Deviation from DSO (GREEN)
        plt.plot(
            beta_values_np,
            deviation_np,
            marker="s",
            markersize=4,
            linestyle="--",
            color="green",
            label="Distance to estimation",
        )

        # Collect existing legend entries
        handles, labels = plt.gca().get_legend_handles_labels()

        # Place legend below the plot, centered
        plt.legend(
            handles,
            labels,
            handler_map={tuple: HandlerTuple(ndivide=None, pad=0)},
            loc="upper center",
            bbox_to_anchor=(0.5, -0.15),
            ncol=3,
            frameon=False,
            fontsize="x-large",
        )

        # Axis formatting
        plt.xlabel("$\\beta$", fontsize="xx-large")
        plt.ylabel("Power (per-unit)", fontsize="xx-large")
        plt.grid(True)

        # Adjust layout so legend fits underneath
        plt.tight_layout(rect=[0, 0.05, 1, 1])

        # Save and show
        plt.savefig(filename, bbox_inches="tight")
        plt.show()

    return {
        "beta": beta_values.tolist(),
        "envelope": envelope,
        "curtailment": curtail,
        "deviation": deviation,
        "total": total,
    }

