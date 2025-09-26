from __future__ import annotations

from typing import Any
import pyomo.environ as pyo

def build(m: pyo.ConcreteModel, G: Any) -> None:
    """Add common DOE constraints shared by AC and DC formulations.

    Parameters
    ----------
    m : pyomo.ConcreteModel
        Model already equipped with sets, variables and key parameters.
    G : networkx.Graph
        Graph describing the operational network.  Only used for context; the
        current implementation reads data directly from the model parameters.
    """



    def add_voltage_vertices(m):
        """Fix voltage magnitude to discrete vertex values ``V_P``."""

        def voltage_rule(m, n, vp, vv):
            return m.V[n, vp, vv] == m.V_P[vv]

        m.voltageConstr = pyo.Constraint(m.Nodes, m.VertP, m.VertV, rule=voltage_rule)


    def add_parent_power_bounds(m):
        """Bound power entering the operational graph at parent nodes."""

        def parent_power_constraint_rule(m, parent, vp, vv):
            return pyo.inequality(m.P_min, m.P_plus[parent, vp, vv], m.P_max)

        m.parent_power_constraint = pyo.Constraint(
            m.parents, m.VertP, m.VertV, rule=parent_power_constraint_rule
        )