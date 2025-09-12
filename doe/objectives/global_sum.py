"""Global-sum objective for DOE optimisation.

The objective maximises the envelope size while penalising curtailment
budget and the gap between envelope centre and DSO information:

``max envelope_size - alpha * curt_budget - beta * envelope_center_gap``

``alpha`` and ``beta`` are mandatory weighting coefficients provided in
``DOE.compute(..., alpha=..., beta=...)``.
"""

from __future__ import annotations

from typing import Dict, Any
import pyomo.environ as pyo


def build(model: pyo.ConcreteModel, params: Dict[str, Any]) -> None:
    """Attach the global-sum objective to ``model``.

    Parameters
    ----------
    model:
        Pyomo model to augment. The function creates three scalar parameters:
        ``envelope_size``, ``curt_budget`` and ``envelope_center_gap``. They
        should already be computed before building the model.
    params:
        Mapping providing at least ``alpha`` and ``beta``. Optional values for
        ``envelope_size``, ``curt_budget`` and ``envelope_center_gap`` can also
        be provided; defaults are zero.
    """

    alpha = params["alpha"]
    beta = params["beta"]

    env_size = float(params.get("envelope_size", 0.0))
    curt_budget = float(params.get("curt_budget", 0.0))
    center_gap = float(params.get("envelope_center_gap", 0.0))

    model.envelope_size = pyo.Param(initialize=env_size, mutable=True)
    model.curt_budget = pyo.Param(initialize=curt_budget, mutable=True)
    model.envelope_center_gap = pyo.Param(initialize=center_gap, mutable=True)

    model.objective = pyo.Objective(
        expr=model.envelope_size - alpha * model.curt_budget - beta * model.envelope_center_gap,
        sense=pyo.maximize,
    )
