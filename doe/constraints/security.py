"""Security constraints for the DOE optimisation models."""

from __future__ import annotations

from typing import Any
import pyomo.environ as pyo


def build(model: pyo.ConcreteModel, graph: Any) -> None:
    """Add generic security constraints to ``model``.

    Currently only thermal line limits are enforced. The function reads
    ``I_min_pu`` and ``I_max_pu`` attributes from the edges of ``graph`` and
    bounds the corresponding flow variable ``F``.
    """

    if not hasattr(model, "Lines") or not hasattr(model, "F"):
        return

    def line_limit_rule(m, u, v):
        data = graph[u][v]
        imin = float(data.get("I_min_pu", -1e3))
        imax = float(data.get("I_max_pu", 1e3))
        return pyo.inequality(imin, m.F[u, v], imax)

    model.LineLimits = pyo.Constraint(model.Lines, rule=line_limit_rule)
