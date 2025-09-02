import logging
from datetime import datetime
from pathlib import Path
from typing import Sequence

import pandas as pd

from core.optimization import optim_problem


def relative_overcost_pct(o_opf: float, o_doe: float) -> float:
    """Compute relative curtailment overcost in percent.

    If ``o_opf`` is not strictly positive, return ``float('nan')``.
    """
    if o_opf <= 0:
        return float("nan")
    return 100.0 * (o_doe - o_opf) / o_opf


def run_series_over_alpha_for_overcost(
    alpha_list: Sequence[float],
    *,
    test_case,
    operational_nodes,
    parent_nodes,
    children_nodes,
    beta: float = 1.0,
    results_csv: str = "results/rel_overcost_vs_alpha.csv",
) -> pd.DataFrame:
    """Run OPF and DOE series to evaluate relative curtailment overcost.

    Parameters
    ----------
    alpha_list:
        Iterable of ``alpha`` values for DOE runs.
    test_case, operational_nodes, parent_nodes, children_nodes:
        Parameters forwarded to :func:`core.optimization.optim_problem`.
    beta:
        Weight of the DSO deviation term in the DOE objective.
    results_csv:
        Where to store the aggregated CSV result table.

    Returns
    -------
    pandas.DataFrame
        Table with columns ``alpha``, ``O_OPF``, ``O_DOE`` and
        ``rel_overcost_pct``.  The table is also saved to ``results_csv``.
    """

    rows = []

    # Baseline OPF
    logging.info("Running baseline OPF for relative overcost analysis")
    res_opf = optim_problem(
        test_case,
        operational_nodes=[],
        parent_nodes=parent_nodes,
        children_nodes=children_nodes,
        alpha=1.0,
        beta=beta,
        plot_doe=False,
    )["full"]
    m_opf = res_opf["model"]
    o_opf = float(getattr(m_opf, "curtailment_budget").value)
    rows.append(
        {
            "alpha": None,
            "mode": "OPF",
            "O_unweighted": o_opf,
            "status": res_opf.get("status"),
            "timestamp": datetime.utcnow().isoformat(),
        }
    )

    # DOE runs for each alpha
    for alpha in alpha_list:
        logging.info("Running DOE for alpha=%s", alpha)
        res_doe = optim_problem(
            test_case,
            operational_nodes=operational_nodes,
            parent_nodes=parent_nodes,
            children_nodes=children_nodes,
            alpha=float(alpha),
            beta=beta,
            plot_doe=False,
        )["operational"]
        m_doe = res_doe["model"]
        o_doe = float(getattr(m_doe, "curtailment_budget").value)
        rows.append(
            {
                "alpha": float(alpha),
                "mode": "DOE",
                "O_unweighted": o_doe,
                "status": res_doe.get("status"),
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

    runs_df = pd.DataFrame(rows)

    # Aggregate OPF baseline with DOE runs
    o_opf_val = runs_df.loc[runs_df["mode"] == "OPF", "O_unweighted"].iloc[0]
    doe_df = runs_df[runs_df["mode"] == "DOE"]["alpha"].to_frame()
    doe_df["O_DOE"] = runs_df.loc[runs_df["mode"] == "DOE", "O_unweighted"].values
    doe_df["O_OPF"] = o_opf_val
    doe_df["rel_overcost_pct"] = doe_df["O_DOE"].apply(
        lambda o: relative_overcost_pct(o_opf_val, o)
    )

    # Persist CSV
    results_path = Path(results_csv)
    results_path.parent.mkdir(parents=True, exist_ok=True)
    doe_df.to_csv(results_path, index=False)
    logging.info("Saved overcost results to %s", results_path)

    return doe_df
