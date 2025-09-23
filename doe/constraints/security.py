"""Security constraints for the DOE optimisation models."""

from __future__ import annotations

from typing import Any
import pyomo.environ as pyo


def build_dc(m: pyo.ConcreteModel, G: Any) -> None:
    """Add DC security constraints to ``model``.
    """

    if not hasattr(m, "Lines") or not hasattr(m, "F"):
        return

    def line_limit_rule(m, u, v, vp, vv):
        data = G[u][v]
        imin = float(data.get("I_min_pu", -1e3))
        imax = float(data.get("I_max_pu", 1e3))
        return pyo.inequality(imin, m.I[u, v, vp, vv], imax)

    m.LineLimits = pyo.Constraint(m.Lines, m.VertP, m.VertV, rule=line_limit_rule)

    def add_phase_bounds(m):
        """Bound voltage angle variables between ``theta_min`` and ``theta_max``."""

        def phase_constr_rule(m, u, vp, vv):
            return pyo.inequality(m.theta_min, m.theta[u, vp, vv], m.theta_max)

        m.phaseConstr = pyo.Constraint(m.Nodes, m.VertP, m.VertV, rule=phase_constr_rule)

def build_ac(m: pyo.ConcreteModel, G: Any) -> None:
    """Add AC security constraints to ``model``.
    """

