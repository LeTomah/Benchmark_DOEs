"""Common dataclasses and protocols."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable


@dataclass
class ComputeOptions:
    """Options controlling :func:`DOE.compute`.

    Attributes:
        alpha: Weight applied to the curtailment budget.
        beta: Weight applied to the envelope centre gap.
        solver: Name of the Pyomo solver to use.
    """

    alpha: float
    beta: float
    solver: str = "glpk"
    P_min: float = -1.0
    P_max: float = 1.0


@dataclass
class Result:
    """Structured result returned by :func:`DOE.compute`."""

    status: str
    objective_value: float | None
    envelopes: Dict[Any, Dict[Any, float]]
    curtailment_report: float | None
    diagnostics: Dict[str, Any]
