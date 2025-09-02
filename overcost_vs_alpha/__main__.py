"""Run OPF and DOE sweeps to generate overcost plot.

Executed as ``python -m overcost_vs_alpha``. Uses parameters defined in
:mod:`overcost_vs_alpha` to run the baseline OPF and DOE optimisations
for a range of ``alpha`` values, then saves the CSV results and the
corresponding plot next to this file.
"""

from pathlib import Path

import numpy as np

from viz.plot_utils import plot_relative_curtailment_overcost
from overcost_vs_alpha.rel_overcost import run_series_over_alpha_for_overcost

from __init__ import (
    ALPHA_MAX,
    ALPHA_MIN,
    ALPHA_STEP,
    BETA,
    CHILDREN_NODES,
    OPERATIONAL_NODES,
    PARENT_NODES,
    TEST_CASE,
)


def main() -> None:
    alpha_list = list(np.arange(ALPHA_MIN, ALPHA_MAX + ALPHA_STEP, ALPHA_STEP))
    this_dir = Path(__file__).resolve().parent
    csv_path = this_dir / "rel_overcost_vs_alpha.csv"
    fig_path = this_dir / "rel_overcost_vs_alpha"

    df = run_series_over_alpha_for_overcost(
        alpha_list,
        test_case=TEST_CASE,
        operational_nodes=OPERATIONAL_NODES,
        parent_nodes=PARENT_NODES,
        children_nodes=CHILDREN_NODES,
        beta=BETA,
        results_csv=str(csv_path),
    )
    plot_relative_curtailment_overcost(df, savepath=fig_path)


if __name__ == "__main__":
    main()
