"""Security constraints for the DOE optimisation models."""

from __future__ import annotations

from typing import Any
import pyomo.environ as pyo


def build(m: pyo.ConcreteModel, G: Any) -> None:
    """Attach both DC and AC security constraints to ``m``.

    Parameters
    ----------
    m : pyomo.ConcreteModel
        Model already initialised with sets and flow variables.
    G : networkx.Graph
        Graph describing the network; edge attributes are used to populate
        current and voltage bounds.
    """

    build_dc(m, G)
    build_ac(m, G)


def build_dc(m: pyo.ConcreteModel, G: Any) -> None:
    """Add DC security constraints to ``model``.

    Parameters
    ----------
    m : pyomo.ConcreteModel
        Model containing DC flow variables ``F`` and currents ``I``.
    G : networkx.Graph
        Network graph providing current bounds on edges.
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

    Parameters
    ----------
    m : pyomo.ConcreteModel
        Model containing squared voltage ``V_sqr`` and current ``I_sqr``.
    G : networkx.Graph
        Network graph providing voltage and current limits for each element.
    """
    if not hasattr(m, "Nodes") or not hasattr(m, "Lines"):
        return

    if not hasattr(m, "V_sqr") or not hasattr(m, "I_sqr"):
        return

    default_vmin = 0.9
    default_vmax = 1.1

    v_min_init = {
        n: float(G.nodes[n].get("V_min_pu", default_vmin)) ** 2 for n in m.Nodes
    }
    v_max_init = {
        n: float(G.nodes[n].get("V_max_pu", default_vmax)) ** 2 for n in m.Nodes
    }

    m.V_sqr_min = pyo.Param(m.Nodes, initialize=v_min_init, mutable=True)
    m.V_sqr_max = pyo.Param(m.Nodes, initialize=v_max_init, mutable=True)

    def voltage_limit_rule(m, n):
        return pyo.inequality(m.V_sqr_min[n], m.V_sqr[n], m.V_sqr_max[n])

    m.VoltageLimits = pyo.Constraint(m.Nodes, rule=voltage_limit_rule)

    default_imax = 1e3
    i_max_init = {}
    for (u, v) in m.Lines:
        data = G[u][v]
        imax = data.get("I_max_pu", default_imax)
        if imax is None:
            imax = default_imax
        imax_val = float(imax)
        if imax_val < 0:
            imax_val = 0.0
        i_max_init[(u, v)] = imax_val ** 2

    m.I_sqr_max = pyo.Param(m.Lines, initialize=i_max_init, mutable=True)

    def current_limit_rule(m, u, v):
        return pyo.inequality(0.0, m.I_sqr[u, v], m.I_sqr_max[u, v])

    m.CurrentLimits = pyo.Constraint(m.Lines, rule=current_limit_rule)
