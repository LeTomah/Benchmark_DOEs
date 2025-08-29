import logging
from pathlib import Path
from typing import Union

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd


def parse_alpha_list(alpha_str: str) -> list[float]:
    """Parse a string specifying a list or range of alpha values.

    The input accepts either a comma-separated list (e.g. ``"0,0.5,1"``) or
    a ``start:stop:step`` range expression (inclusive of ``stop``).
    """
    if ":" in alpha_str:
        start, stop, step = map(float, alpha_str.split(":"))
        return [float(x) for x in np.arange(start, stop + step, step)]
    return [float(x) for x in alpha_str.split(",") if x.strip()]


def plot_relative_curtailment_overcost(
    df_or_csv_path: Union[pd.DataFrame, str, Path],
    *,
    title: str | None = None,
    savepath: str | Path | None = None,
):
    """Plot relative curtailment overcost vs ``alpha``.

    Parameters
    ----------
    df_or_csv_path:
        Either the DataFrame produced by
        :func:`run_series_over_alpha_for_overcost` or the path to the
        corresponding CSV file.
    title:
        Optional custom title for the plot.
    savepath:
        Base path (without extension) where the figure will be saved as PNG
        and PDF.  If ``None``, the figure is not saved.

    Returns
    -------
    str | None
        Path to the saved PNG figure or ``None`` if ``savepath`` is ``None``.
    """

    if isinstance(df_or_csv_path, (str, Path)):
        df = pd.read_csv(df_or_csv_path)
    else:
        df = df_or_csv_path

    o_opf = df.get("O_OPF", pd.Series([0])).iloc[0]
    fig, ax = plt.subplots()

    if o_opf <= 0:
        ax.text(
            0.5,
            0.5,
            "Baseline OPF sans curtailment (O_OPF ≤ 0), surcoût relatif non défini.",
            ha="center",
            va="center",
            wrap=True,
        )
        ax.axis("off")
    else:
        df_plot = df.dropna(subset=["alpha", "rel_overcost_pct"])
        missing = len(df) - len(df_plot)
        if missing:
            logging.warning("%d NaN rows dropped from plotting", missing)
        if len(df_plot) == 1:
            ax.scatter(df_plot["alpha"], df_plot["rel_overcost_pct"], color="C0")
            ax.text(
                df_plot["alpha"].iloc[0],
                df_plot["rel_overcost_pct"].iloc[0],
                "un seul point α",
                ha="left",
                va="bottom",
            )
        else:
            ax.plot(
                df_plot["alpha"],
                df_plot["rel_overcost_pct"],
                marker="o",
                linestyle="-",
                label="Surcoût relatif DOE vs OPF",
            )
            ax.legend()
        ax.set_xlabel("α")
        ax.set_ylabel("Surcoût relatif de curtailment (%)")
        ax.grid(True)
        ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=100, decimals=1))
        if title is None:
            title = "Surcoût relatif de curtailment (DOE vs OPF) en fonction de α"
        ax.set_title(title)

    if savepath is not None:
        savepath = Path(savepath)
        savepath.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(savepath.with_suffix(".png"), bbox_inches="tight")
        fig.savefig(savepath.with_suffix(".pdf"), bbox_inches="tight")
        return str(savepath.with_suffix(".png"))
    return None
