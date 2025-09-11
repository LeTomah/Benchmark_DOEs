"""Input validation helpers."""
from __future__ import annotations

from typing import Any, Dict

REQUIRED_PARAMS = {"alpha", "beta"}


def validate_inputs(powerflow_mode: str, objective: str, options: Dict[str, Any]) -> Dict[str, Any]:
    """Validate user inputs and return normalized parameters."""

    params = dict(options)
    missing = [p for p in REQUIRED_PARAMS if p not in params]
    if missing:
        raise ValueError(f"Missing required parameters: {', '.join(missing)}")
    if not isinstance(params["alpha"], (int, float)):
        raise TypeError("alpha must be a number")
    if not isinstance(params["beta"], (int, float)):
        raise TypeError("beta must be a number")
    params.setdefault("solver", "glpk")
    return params
