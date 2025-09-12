"""High level entry point for computing Dynamic Operating Envelopes."""
from __future__ import annotations

from typing import Any, Dict

from .registry import POWERFLOW_REGISTRY, OBJECTIVE_REGISTRY
from .constraints import security
from .io.networks import load
from .solvers.pyomo_backend import create_model, solve_model
from .utils import logging as log_utils, validation


class DOE:
    """Facade providing the :meth:`compute` class method."""

    @classmethod
    def compute(
        cls,
        network: Any,
        powerflow_mode: str,
        objective: str,
        **options: Any,
    ) -> Dict[str, Any]:
        """Compute a Dynamic Operating Envelope for a network.

        Args:
            network: A ``pandapowerNet`` instance or the name of a file located
                in the repository ``networks`` directory. Python modules must
                provide a ``load()`` function returning the network.
            powerflow_mode: Power flow formulation to use (``"dc"`` or ``"ac"``).
            objective: Objective function name (``"global_sum"`` or ``"fairness"``).
            **options: Additional options such as ``alpha`` and ``beta``. Network
                related options ``parents``, ``children`` and ``operational_nodes``
                can be provided to explicitly select node roles.

        Returns:
            A dictionary with solver status, objective value, envelopes and
            diagnostics.
        """

        logger = log_utils.get_logger()
        net_opts = {k: options.pop(k) for k in ["parents", "children", "operational_nodes"] if k in options}
        params = validation.validate_inputs(powerflow_mode, objective, options)
        data = load(network, logger=logger, **net_opts)
        model = create_model(data, params, logger)

        pf_builder = POWERFLOW_REGISTRY[powerflow_mode]
        pf_builder(model, data, params, logger)

        security.attach_security_constraints(model, data, params, logger)

        obj_builder = OBJECTIVE_REGISTRY[objective]
        obj_builder(model, data, params, logger)

        result = solve_model(model, params, logger)
        return result
