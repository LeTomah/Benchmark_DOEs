"""Test configuration shared across the suite."""

import importlib
import pathlib
import sys
from typing import Any, Dict

import pytest


ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

compute_module = importlib.import_module("doe.compute")  # noqa: E402


@pytest.fixture(autouse=True)
def stub_solve_model(monkeypatch):
    """Replace the heavy Pyomo solver with a lightweight stub during tests."""

    def fake_solver(
        G: Any,
        *,
        powerflow_builder,
        security_builder,
        objective_builder,
        params: Dict[str, Any],
        options: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        # Preserve the behaviour of the fairness placeholder by raising the
        # expected ``NotImplementedError`` when the corresponding builder is
        # requested.
        if "fairness" in getattr(objective_builder, "__module__", ""):
            raise NotImplementedError("Fairness objective not implemented yet")

        envelopes = {node: (0.0, 0.0) for node in getattr(G, "nodes", [])}
        return {
            "status": "optimal",
            "objective": 0.0,
            "envelopes": envelopes,
            "curtailment_report": {},
            "diagnostics": {"solver": "stub"},
        }

    monkeypatch.setattr(compute_module, "solve_model", fake_solver)

