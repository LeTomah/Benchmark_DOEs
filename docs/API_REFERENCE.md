# API Reference

## `DOE.compute`

```python
doe.compute.DOE.compute(network, powerflow_mode, objective, **options)
```

Compute a Dynamic Operating Envelope for a given pandapower network.

### Arguments
- `network`: a :mod:`pandapower` network object or the name of a Python module
  in the ``networks`` directory.
- `powerflow_mode`: short string selecting the constraint set.
- `objective`: short string selecting the objective function.
- `**options`: at minimum `alpha` and `beta` floats. The optional keywords
  `parents`, `children` and `operational_nodes` allow explicit node selection.
  Additional solver options may be provided.

### Returns
Dictionary with keys `status`, `objective_value`, `envelopes`,
`curtailment_report` and `diagnostics`.

### Raises
- `ValueError`: invalid or missing parameters.
- `NotImplementedError`: if a selected mode or objective is not implemented.
