"""Sweep alpha values and plot resulting metrics."""

from itertools import cycle

import matplotlib.pyplot as plt
import numpy as np
import scienceplots  # noqa: F401
from matplotlib.legend_handler import HandlerTuple
from matplotlib.lines import Line2D

plt.style.use(["science", "no-latex"])


def plot_alloc_alpha(
    test_case,
    operational_nodes=None,
    parent_nodes=None,
    children_nodes=None,
    beta: float = 1.0,
    alpha_min: float = 0.0,
    alpha_max: float = 1.0,
    alpha_step: float = 0.1,
    P_min: float = -1.0,
    P_max: float = 1.0,
    show: bool = True,
    filename: str = "figures/Plot_alpha.pdf",
):
    """Run the optimisation for several ``alpha`` values and optionally plot metrics.

    Parameters
    ----------
    test_case : str or pandapowerNet
        Network description passed to :func:`core.optimization.optim_problem`.
    operational_nodes, parent_nodes, children_nodes : iterable, optional
        Subsets describing the operational perimeter and its boundaries.
    beta : float, optional
        Weight applied to the envelope centre gap in the DOE objective.
    alpha_min, alpha_max : float, optional
        Lower and upper bounds of the scanned ``alpha`` range.
    alpha_step : float, optional
        Increment applied between successive ``alpha`` values.
    P_min, P_max : float, optional
        Bounds on the power exchanged with parent nodes.
    show : bool, optional
        If ``True`` display the resulting plot.
    filename : str, optional
        Destination path for the saved PDF figure.

    Returns
    -------
    dict
        Dictionary with sampled ``alpha`` values and associated metrics
        (envelope, curtailment, deviation and total).
    """

    from core.optimization import optim_problem  # local import to avoid cycle

    alpha_values = np.arange(alpha_min, alpha_max + alpha_step, alpha_step)
    envelope, curtail, deviation, total = [], [], [], []

    for alpha in alpha_values:
        res = optim_problem(
            test_case,
            operational_nodes=operational_nodes,
            parent_nodes=parent_nodes,
            children_nodes=children_nodes,
            alpha=float(alpha),
            beta=beta,
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
        alpha_values_np = np.array(alpha_values)
        envelope_np = np.array(envelope, dtype=float)
        curtail_np = np.array(curtail, dtype=float)
        deviation_np = np.array(deviation, dtype=float)
        total_np = np.array(total, dtype=float)

        plt.figure(figsize=(8, 5))

        # Envelope Volume (BLUE)
        plt.plot(
            alpha_values_np,
            envelope_np,
            marker="o",
            linestyle="-",
            color="blue",
            label="Envelope volume",
        )

        # Curtailment (ORANGE)
        plt.plot(
            alpha_values_np,
            curtail_np,
            marker="x",
            linestyle="--",
            color="orange",
            label="Curtailment",
        )

        # Deviation from DSO (GREEN)
        plt.plot(
            alpha_values_np,
            deviation_np,
            marker="s",
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
        plt.xlabel("$\\alpha$", fontsize="xx-large")
        plt.ylabel("Power (per-unit)", fontsize="xx-large")
        plt.grid(True)

        # Adjust layout so legend fits underneath
        plt.tight_layout(rect=[0, 0.05, 1, 1])

        # Save and show
        plt.savefig(filename, bbox_inches="tight")
        plt.show()

    return {
        "alpha": alpha_values.tolist(),
        "envelope": envelope,
        "curtailment": curtail,
        "deviation": deviation,
        "total": total,
    }
