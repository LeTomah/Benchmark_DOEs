"""High level interface for computing DOEs."""

from __future__ import annotations

from importlib import import_module
from typing import Any, Dict

import pandapower as pp

from .constraints import powerflow_dc, powerflow_ac, security
from .objectives import global_sum, fairness
from .solvers.pyomo_backend_dc import solve_model
from .utils.graph import build_nx_from_pandapower

POWERFLOW = {"dc": powerflow_dc.build, "ac": powerflow_ac.build}
OBJECTIVES = {"global_sum": global_sum.build, "fairness": fairness.build}


def _load_network(network: Any) -> pp.pandapowerNet:
    """Return a :class:`pandapowerNet` built from a name or existing object.

    Parameters
    ----------
    network:
        Either an existing :class:`pandapowerNet` or the name of a module inside
        :mod:`data.networks` exposing a :func:`build` function.

    Returns
    -------
    pandapowerNet
        Network ready for DOE computations.

    Raises
    ------
    ValueError
        If ``network`` is a string that does not correspond to a known module
        or the module does not define ``build``.
    TypeError
        If ``network`` is neither a pandapower network nor a recognised name.
    """

    if isinstance(network, pp.pandapowerNet):
        return network
    if isinstance(network, str):
        try:
            module = import_module(f"data.networks.{network}")
        except ModuleNotFoundError as exc:
            raise ValueError(f"Unknown network '{network}'") from exc
        if not hasattr(module, "build"):
            raise ValueError(f"Network '{network}' does not provide a build() function")
        return module.build()
    raise TypeError("network must be a pandapowerNet or a known network name")


def compute(network: Any, powerflow_mode: str, objective: str, **options: Any) -> Dict[str, Any]:
    """Compute a Distribution Operation Envelope (DOE).

    Parameters
    ----------
    network:
        A :class:`pandapowerNet` instance or the name of a network module
        located in :mod:`data.networks`.
    powerflow_mode:
        Either ``"dc"`` (implemented) or ``"ac"`` (placeholder).
    objective:
        Either ``"global_sum"`` (implemented) or ``"fairness"`` (placeholder).
    options:
        Additional keyword arguments including at least ``alpha`` and ``beta``
        when using the ``global_sum`` objective.
    """

    net = _load_network(network)

    if powerflow_mode not in POWERFLOW:
        raise ValueError(f"Unknown powerflow mode '{powerflow_mode}'")
    if objective not in OBJECTIVES:
        raise ValueError(f"Unknown objective '{objective}'")

    if objective == "global_sum" and ("alpha" not in options or "beta" not in options):
        raise ValueError("alpha and beta must be provided for the global_sum objective")

    G = build_nx_from_pandapower(net)

    params = {
        "alpha": options.get("alpha"),
        "beta": options.get("beta"),
        "envelope_size": sum(abs(G.nodes[n]["P"]) for n in G.nodes),
        "curt_budget": float(options.get("curt_budget", 0.0)),
        "envelope_center_gap": 0.0,
    }

    result = solve_model(
        G,
        powerflow_builder=POWERFLOW[powerflow_mode],
        security_builder=security.build,
        objective_builder=OBJECTIVES[objective],
        params=params,
        options=options,
    )

    return {
        "status": result.get("status"),
        "objective_value": result.get("objective"),
        "envelopes": result.get("envelopes"),
        "curtailment_report": result.get("curtailment_report"),
        "diagnostics": result.get("diagnostics"),
    }
