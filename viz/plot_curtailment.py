"""Plot child-node power envelope with curtailment details."""

import matplotlib.pyplot as plt
import numpy as np
import scienceplots  # noqa: F401

plt.style.use(["science", "no-latex"])


def plot_curtailment(m, filename="figures/Child_nodes_curtailment.pdf"):
    """Plot power envelope and curtailment for child nodes.

    Parameters
    ----------
    m : pyomo.ConcreteModel
        Solved DOE model exposing ``P_C_set`` intervals, ``info_P`` and
        net power ``E`` for child nodes.
    filename : str, optional
        Destination path for the generated PDF figure.

    Notes
    -----
    For each child node a vertical segment represents the active power envelope
    ``[P_min, P_max]``.  A round marker shows the initial demand provided by the
    DSO and a square marker the net power after curtailment.  When curtailment
    occurs an arrow indicates the magnitude of the adjustment.
    """

    children = list(m.children)
    p_max = [getattr(m.P_C_set[n, 0], "value", m.P_C_set[n, 0]) for n in children]
    p_min = [getattr(m.P_C_set[n, 1], "value", m.P_C_set[n, 1]) for n in children]
    info = [
        getattr(m.info_P[n], "value", m.info_P[n]) for n in children
    ]
    e_vals = [getattr(m.E[n, 0, 0], "value", m.E[n, 0, 0]) for n in children]
    delta = [i - e for i, e in zip(info, e_vals)]
    x = np.arange(len(children)) * 5e-4

    plt.figure(figsize=(5, 6))
    for idx, (xs, lo, hi, i, e, d) in enumerate(
        zip(x, p_min, p_max, info, e_vals, delta)
    ):
        # Envelope segment
        plt.plot([xs, xs], [lo, hi], color="blue")

        # Initial demand (info_DSO)
        plt.plot(xs, i, "o", color="black", label="Initial demand" if idx == 0 else "")

        # Post-curtailment net power (m.E)
        plt.plot(xs, e, "s", color="red", label="After curtailment" if idx == 0 else "")

        if abs(d) > 1e-6:
            # Arrow from initial demand to post-curtailment point
            plt.annotate(
                "",
                xy=(xs, e),
                xytext=(xs, i),
                arrowprops=dict(arrowstyle="->", color="gray"),
            )
            # Annotation of curtailment value
            plt.annotate(
                f"{d:+.3f}",
                xy=(xs, (i + e) / 2),
                xytext=(5, 0),
                textcoords="offset points",
                fontsize=8,
                color="gray",
            )

    # Legend entry for the envelope
    plt.plot([], [], color="blue", label="Power envelope")

    plt.xticks(x, children)
    plt.xlabel("Child Node Index")
    plt.ylabel("Power P [p.u.]")
    plt.legend(loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=3)
    plt.grid(True)
    plt.savefig(filename)
    plt.show()
