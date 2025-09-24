#!/usr/bin/env python3
"""Command line helper to run DOE computations and optional plots."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable, List, Mapping, Sequence

import matplotlib.pyplot as plt

from doe import DOE


def _parse_node_list(value: str | None) -> List[int] | None:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return []
    try:
        return [int(part) for part in stripped.split(",")]
    except ValueError as exc:  # pragma: no cover - argparse catches earlier
        raise argparse.ArgumentTypeError(str(exc)) from exc


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compute a Distribution Operation Envelope using DOE.compute.",
    )

    parser.add_argument(
        "network",
        help="Pandapower network name or path (see data/networks).",
    )
    parser.add_argument(
        "mode",
        choices=["dc", "ac"],
        help="Power flow formulation to use (dc/ac).",
    )
    parser.add_argument(
        "objective",
        choices=["global_sum", "fairness"],
        help="Objective function to optimise.",
    )

    parser.add_argument(
        "--operational-nodes",
        type=_parse_node_list,
        help="Comma-separated list of node indices forming the operational perimeter.",
    )
    parser.add_argument(
        "--parent-nodes",
        type=_parse_node_list,
        help="Comma-separated list of parent node indices (exchanges with upstream grid).",
    )
    parser.add_argument(
        "--children-nodes",
        type=_parse_node_list,
        help="Comma-separated list of child node indices (DSO boundary).",
    )
    parser.add_argument(
        "--alpha",
        type=float,
        default=1.0,
        help="Weight for curtailment in the objective (dimensionless, default=1.0).",
    )
    parser.add_argument(
        "--beta",
        type=float,
        default=1.0,
        help="Weight for DSO deviation in the objective (dimensionless, default=1.0).",
    )
    parser.add_argument(
        "--p-min",
        type=float,
        default=-1.0,
        help="Minimum active power at parent nodes [p.u., default=-1.0].",
    )
    parser.add_argument(
        "--p-max",
        type=float,
        default=1.0,
        help="Maximum active power at parent nodes [p.u., default=1.0].",
    )
    parser.add_argument(
        "--q-min",
        type=float,
        help="Minimum reactive power at parent nodes [p.u., AC only].",
    )
    parser.add_argument(
        "--q-max",
        type=float,
        help="Maximum reactive power at parent nodes [p.u., AC only].",
    )
    parser.add_argument(
        "--theta-min",
        type=float,
        help="Minimum voltage angle [rad, DC only].",
    )
    parser.add_argument(
        "--theta-max",
        type=float,
        help="Maximum voltage angle [rad, DC only].",
    )
    parser.add_argument(
        "--v-min",
        type=float,
        help="Minimum voltage magnitude [p.u., AC only].",
    )
    parser.add_argument(
        "--v-max",
        type=float,
        help="Maximum voltage magnitude [p.u., AC only].",
    )
    parser.add_argument(
        "--curtailment-limit",
        type=float,
        help="Optional cap on total curtailment [p.u.].",
    )
    parser.add_argument(
        "--envelope-center-gap",
        type=float,
        default=0.0,
        help="Initial envelope centre gap [p.u., default=0.0].",
    )

    parser.add_argument(
        "--solver",
        help="Preferred Pyomo solver (e.g. gurobi, appsi_highs, glpk).",
    )
    parser.add_argument(
        "--solver-io",
        help="Solver I/O backend (advanced, forwards to Pyomo).",
    )
    parser.add_argument(
        "--solver-tee",
        action="store_true",
        help="Enable solver verbose output (tee=True).",
    )

    # Plotting options
    parser.add_argument(
        "--plot-envelopes",
        action="store_true",
        help="Display the DOE envelope plot (children nodes).",
    )
    parser.add_argument(
        "--plot-curtailment",
        action="store_true",
        help="Display the curtailment report for child nodes.",
    )
    parser.add_argument(
        "--plot-voltages",
        action="store_true",
        help="Attempt to plot nodal voltages (if a viz helper is available).",
    )
    parser.add_argument(
        "--plot-flows",
        action="store_true",
        help="Display power flow magnitudes for the first vertex combination.",
    )
    parser.add_argument(
        "--plot-summary",
        action="store_true",
        help="Plot a network overview highlighting nodal powers.",
    )
    parser.add_argument(
        "--save-figs",
        action="store_true",
        help="Save generated figures into the output directory.",
    )
    parser.add_argument(
        "--fig-format",
        default="pdf",
        help="Figure file format when saving (default=pdf).",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=300,
        help="Figure resolution in dots-per-inch (default=300).",
    )
    parser.add_argument(
        "--no-show",
        action="store_true",
        help="Disable interactive display of figures (useful for batch runs).",
    )
    parser.add_argument(
        "--output-dir",
        default="results",
        help="Directory used to store generated artefacts (default=results).",
    )

    return parser


def _configure_matplotlib(save_figs: bool, fmt: str, dpi: int, no_show: bool) -> None:
    if no_show:
        plt.show = lambda *args, **kwargs: None  # type: ignore[assignment]
    if save_figs:
        plt.rcParams["savefig.format"] = fmt
        plt.rcParams["savefig.dpi"] = dpi
    else:
        plt.savefig = lambda *args, **kwargs: None  # type: ignore[assignment]


def _call_plot(module_name: str, func_name: str, *args, **kwargs) -> None:
    try:
        module = __import__(module_name, fromlist=[func_name])
        plot_func = getattr(module, func_name)
    except Exception as exc:  # pragma: no cover - depends on optional viz modules
        print(f"Plot '{module_name}.{func_name}' unavailable: {exc}", file=sys.stderr)
        return

    try:
        plot_func(*args, **kwargs)
    except Exception as exc:  # pragma: no cover - plotting failures are non critical
        print(f"Plot '{module_name}.{func_name}' failed: {exc}", file=sys.stderr)


def _build_solver_options(args: argparse.Namespace) -> Mapping[str, object]:
    options: dict[str, object] = {}
    if args.solver:
        options["solver"] = args.solver
    if args.solver_io:
        options["solver_io"] = args.solver_io
    if args.solver_tee:
        options["tee"] = True
    return options


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    solver_options = _build_solver_options(args)

    _configure_matplotlib(
        save_figs=args.save_figs,
        fmt=args.fig_format,
        dpi=args.dpi,
        no_show=args.no_show,
    )

    result = DOE.compute(
        args.network,
        args.mode,
        args.objective,
        operational_nodes=args.operational_nodes,
        parent_nodes=args.parent_nodes,
        children_nodes=args.children_nodes,
        alpha=args.alpha,
        beta=args.beta,
        p_min=args.p_min,
        p_max=args.p_max,
        q_min=args.q_min,
        q_max=args.q_max,
        theta_min=args.theta_min,
        theta_max=args.theta_max,
        v_min=args.v_min,
        v_max=args.v_max,
        curtailment_limit=args.curtailment_limit,
        envelope_center_gap=args.envelope_center_gap,
        solver_options=solver_options,
    )

    status = str(result.get("status", "")).lower()
    termination = str(result.get("diagnostics", {}).get("termination_condition", "")).lower()
    success = any(word in status for word in ("optimal", "ok")) or "optimal" in termination

    if not success:
        print(
            "Solver did not converge: status={}, termination={}".format(
                result.get("status"), result.get("diagnostics", {}).get("termination_condition")
            ),
            file=sys.stderr,
        )
        return 2

    model = result.get("model")
    graph = result.get("graph")

    output_dir = Path(args.output_dir)
    if args.save_figs:
        output_dir.mkdir(parents=True, exist_ok=True)

    if args.plot_envelopes and model is not None:
        filename = output_dir / f"DOE.{args.fig_format}"
        _call_plot("viz.plot_DOE", "plot_DOE", model, filename=str(filename))

    if args.plot_curtailment and model is not None:
        filename = output_dir / f"curtailment.{args.fig_format}"
        _call_plot("viz.plot_curtailment", "plot_curtailment", model, filename=str(filename))

    if args.plot_flows and model is not None and graph is not None:
        filename = output_dir / f"flows.{args.fig_format}"
        _call_plot("viz.plot_powerflow", "plot_power_flow", model, graph, 0, 0, filename=str(filename))

    if args.plot_summary and graph is not None:
        filename = output_dir / f"network.{args.fig_format}"
        _call_plot("viz.plot_network", "plot_network", graph, filename=str(filename), dpi=args.dpi)

    if args.plot_voltages:
        filename = output_dir / f"voltages.{args.fig_format}"
        if model is not None:
            _call_plot("viz.plot_powerflow", "plot_power_flow", model, graph, 0, 0, filename=str(filename))
        else:
            print("Voltage plot skipped: model unavailable", file=sys.stderr)

    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())

