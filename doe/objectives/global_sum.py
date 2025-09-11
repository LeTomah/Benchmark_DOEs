"""Global sum objective."""
from __future__ import annotations

import pyomo.environ as pyo


def build(model, data, params, logger):
    """Maximise envelope size minus penalties on curtailment and gap."""

    def objective_rule(m):
        return m.envelope_size - (m.alpha * m.curt_budget) - (
            m.beta * m.envelope_center_gap
        )

    model.objective = pyo.Objective(rule=objective_rule, sense=pyo.maximize)
    return model.objective
