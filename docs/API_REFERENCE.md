# API Reference

## DOE.compute

``DOE.compute(network, mode, objective, **kwargs)``

Mandatory arguments:

* ``network`` – pandapowerNet instance or name of a network in ``data/networks``.
* ``mode`` – ``"dc"`` or ``"ac"`` (power flow formulation).
* ``objective`` – ``"global_sum"`` or ``"fairness"`` (placeholder).

Keyword arguments control the optimisation scenario:

* ``operational_nodes`` – list of node indices defining the operational perimeter.
* ``parent_nodes`` / ``children_nodes`` – boundary nodes (lists of indices).
* ``alpha`` / ``beta`` – objective weights (dimensionless).
* ``p_min`` / ``p_max`` – bounds on parent active power (p.u.).
* ``q_min`` / ``q_max`` – bounds on parent reactive power (p.u., AC only).
* ``theta_min`` / ``theta_max`` – voltage angle bounds (radians, DC only).
* ``v_min`` / ``v_max`` – voltage magnitude bounds (p.u., AC only).
* ``curtailment_limit`` – optional cap on total curtailment (p.u.).
* ``solver_options`` – mapping forwarded to :mod:`pyomo`'s solver factory.

Returned dictionary fields:
``status``, ``objective_value``, ``model``, ``graph``, ``envelopes``,
``curtailment_report`` and ``diagnostics``.
