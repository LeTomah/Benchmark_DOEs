"""Plot power envelope and DSO estimation for child nodes."""

import matplotlib.pyplot as plt
import numpy as np
import scienceplots  # noqa: F401

plt.style.use(["science", "no-latex"])


def plot_DOE(m, filename="figures/DOE.pdf"):
    """Plot power envelopes and DSO estimations for child nodes.

    Parameters
    ----------
    m : pyomo.ConcreteModel
        Solved DOE model providing ``P_C_set`` intervals and ``info_DSO_param``
        values for child nodes.
    filename : str, optional
        Path where the PDF figure should be saved.
    """

    children = list(m.children)
    p0 = [getattr(m.P_C_set[n, 0], "value", m.P_C_set[n, 0]) for n in children]
    p1 = [getattr(m.P_C_set[n, 1], "value", m.P_C_set[n, 1]) for n in children]
    info = [getattr(m.info_DSO_param[n], "value", m.info_DSO_param[n]) for n in children]
    x = np.arange(len(children))

    plt.figure(figsize=(5, 5))
    for xs, hi, lo in zip(x, p0, p1):
        plt.plot([xs, xs], [lo, hi], "o-", color="blue")
    plt.plot(x, info, "s", label="DSO power demand estimation")

    alpha = getattr(m, "alpha", None)
    beta = getattr(m, "beta", None)
    alpha_val = getattr(alpha, "value", alpha) if alpha is not None else None
    beta_val = getattr(beta, "value", beta) if beta is not None else None
    plt.plot(
        [],
        [],
        "o-",
        color="blue",
        label=f"Power envelope ($\\alpha$={alpha_val}, $\\beta$={beta_val})",
    )

    plt.xticks(x, children)
    plt.xlabel("Child Node Index")
    plt.ylabel("Power [p.u.]")
    plt.legend(loc="upper center", bbox_to_anchor=(0.5, 1.13))
    plt.grid(True)
    plt.savefig(filename)
    plt.show()

    # To plot curtailment details, uncomment the following line:
    # from .plot_curtailment import plot_curtailment
    # plot_curtailment(m)
