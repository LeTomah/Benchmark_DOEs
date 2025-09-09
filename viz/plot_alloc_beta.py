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
    filename: str = "Figures/DOE_alloc_beta_final.pdf",
):
    """Run the optimisation for several ``beta`` values and optionally plot metrics.

    Parameters
    ----------
    P_min, P_max: float, optional
        Bounds applied to the power exchanged with parent nodes.  They are
        forwarded to :func:`core.optimization.optim_problem` so that envelope
        sizes match those shown by :func:`viz.plot_DOE.plot_DOE`.
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

        plt.figure(figsize=(10, 6))

        # Envelope Volume (BLUE)
        plt.plot(
            beta_values_np,
            envelope_np,
            marker="o",
            linestyle="-",
            color="blue",
            label="Envelope Volume",
        )

        # Curtailment (ORANGE)
        plt.plot(
            beta_values_np,
            curtail_np,
            marker="x",
            linestyle="--",
            color="orange",
            label="Curtailment",
        )

        # Deviation from DSO (GREEN)
        plt.plot(
            beta_values_np,
            deviation_np,
            marker="s",
            linestyle="--",
            color="green",
            label="Distance to estimation",
        )

        # Alternating-color sum curve: blue (envelope) ↔ green (deviation)
        alt_colors = cycle(["blue", "green"])
        for i in range(len(beta_values_np) - 1):
            plt.plot(
                beta_values_np[i : i + 2],
                total_np[i : i + 2],
                linestyle=":",
                linewidth=1.2,
                alpha=0.9,
                color=next(alt_colors),
                zorder=2,
            )

        # Custom legend entry for alternating curve (overlay, no gap)
        custom_sum_handle = (
            Line2D([0, 1], [0, 0], color="blue", linestyle=":", linewidth=1.5),
            Line2D([0, 1], [0, 0], color="green", linestyle=":", linewidth=1.5),
        )

        # Collect existing legend entries
        handles, labels = plt.gca().get_legend_handles_labels()

        # Add custom alternating-color entry
        handles.append(custom_sum_handle)
        labels.append(
            "Distance to estimation + Envelope Volume"
        )

        # Place legend below the plot, centered
        plt.legend(
            handles,
            labels,
            handler_map={tuple: HandlerTuple(ndivide=None, pad=0)},
            loc="upper center",
            bbox_to_anchor=(0.5, -0.15),
            ncol=2,
            frameon=False,
            fontsize="large",
        )

        # Axis formatting
        plt.xlabel("$\\beta$", fontsize="large")
        plt.ylabel("Power (per-unit)", fontsize="large")
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

