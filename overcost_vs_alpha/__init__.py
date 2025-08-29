"""Generate relative curtailment overcost plot across α values.

Running this module executes the necessary OPF and DOE optimisations for a
range of α and saves the resulting CSV and plot alongside this file.
"""

from pathlib import Path

import numpy as np

from viz.plot_utils import plot_relative_curtailment_overcost
from viz.rel_overcost import run_series_over_alpha_for_overcost

# ---- User parameters ----
TEST_CASE = "Data/Networks/example_multivoltage_adapted.py"
OPERATIONAL_NODES = [0, 1, 2, 3, 4, 5]
PARENT_NODES = [0]
CHILDREN_NODES = [1, 2, 3, 4, 5]
BETA = 1.0

ALPHA_MIN = 0.0
ALPHA_MAX = 1.0
ALPHA_STEP = 0.5
# ------------------------


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
