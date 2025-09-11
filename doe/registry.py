"""Dispatch registries for power flow modes and objectives."""

from .constraints import powerflow_ac, powerflow_dc
from .objectives import fairness, global_sum

POWERFLOW_REGISTRY = {
    "dc": powerflow_dc.build,
    "ac": powerflow_ac.build,
}

OBJECTIVE_REGISTRY = {
    "global_sum": global_sum.build,
    "fairness": fairness.build,
}
