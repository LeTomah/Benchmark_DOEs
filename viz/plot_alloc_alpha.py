"""Sweep alpha values and plot resulting metrics."""

import matplotlib.pyplot as plt
import numpy as np
from itertools import cycle
from matplotlib.lines import Line2D
from matplotlib.legend_handler import HandlerTuple


def plot_alloc_alpha(
    test_case,
    operational_nodes=None,
    parent_nodes=None,
    children_nodes=None,
    beta: float = 1.0,
    alpha_min: float = 0.0,
    alpha_max: float = 1.0,
    alpha_step: float = 0.1,
    show: bool = True,
    filename: str = "Figures/DOE_alloc_alpha_final.pdf",
):
    """Run the optimisation for several ``alpha`` values and optionally plot metrics."""

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

        plt.figure(figsize=(10, 6))

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

        # Alternating-color sum curve: blue (envelope) ↔ green (deviation)
        alt_colors = cycle(["blue", "green"])
        for i in range(len(alpha_values_np) - 1):
            plt.plot(
                alpha_values_np[i : i + 2],
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
            "Distance to estimation + Envelope volume"
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
        plt.xlabel("$\\alpha$", fontsize="large")
        plt.ylabel("Power (per-unit)", fontsize="large")
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
