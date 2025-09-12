# API Reference

## DOE.compute

``DOE.compute(network, powerflow_mode, objective, **options)``

* ``network`` – pandapowerNet instance or name of a network in ``data/networks``.
* ``powerflow_mode`` – ``"dc"`` or ``"ac"`` (placeholder).
* ``objective`` – ``"global_sum"`` or ``"fairness"`` (placeholder).
* ``options`` – must include ``alpha`` and ``beta`` for ``global_sum``.

Returns a dictionary with the following fields:
``status``, ``objective_value``, ``envelopes``, ``curtailment_report`` and
``diagnostics``.
