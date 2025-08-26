"""Standard OPF constraints and objective."""

import pyomo.environ as pyo
from constraints_common import (
    add_curtailment_abs,
    add_current_bounds,
    add_current_definition,
    add_dc_flow_constraints,
    add_parent_power_bounds,
    add_phase_bounds,
    add_power_balance,
    add_voltage_vertices,
)


def apply(m, G):
    """Apply OPF constraints and objective to model ``m``."""

    add_curtailment_abs(m)
    add_current_bounds(m, G)
    add_dc_flow_constraints(m, G)
    add_current_definition(m)
    add_phase_bounds(m)
    add_power_balance(m, G)
    add_parent_power_bounds(m)
    add_voltage_vertices(m)

    def objective_rule_opf(m):
        return m.alpha * m.curtailment_budget

    m.objective_opf = pyo.Objective(rule=objective_rule_opf, sense=pyo.minimize)
