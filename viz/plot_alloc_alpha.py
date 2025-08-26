"""Sweep alpha values and plot resulting metrics."""

import matplotlib.pyplot as plt
import numpy as np


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
    filename: str = "Figures/DOE_alloc_alpha.pdf",
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
        total.append(curtail[-1] + deviation[-1])

    if show:
        plt.figure(figsize=(10, 6))
        plt.plot(alpha_values, envelope, marker="o", linestyle="-", label="Envelope Volume")
        plt.plot(alpha_values, curtail, marker="x", linestyle="--", label="Curtailment")
        plt.plot(
            alpha_values,
            deviation,
            marker="s",
            linestyle="--",
            color="blue",
            label="Deviation of the center of the envelope from DSO estimation",
        )
        plt.plot(
            alpha_values,
            total,
            marker="^",
            linestyle=":",
            color="red",
            label="Deviation of the center of the envelope from DSO estimation + Envelope Volume",
        )
        plt.xlabel("$\\alpha$")
        plt.ylabel("Power [p.u.]")
        plt.title(
            "Evolution of the volume of the envelope, curtailment and closeness to DSO estimation as a function of parameter alpha (beta={})".format(
                beta
            )
        )
        plt.legend()
        plt.grid(True)
        plt.savefig(filename)
        plt.show()

    return {
        "alpha": alpha_values.tolist(),
        "envelope": envelope,
        "curtailment": curtail,
        "deviation": deviation,
        "total": total,
    }
