# DOE

Modular Python library to compute **Dynamic Operating Envelopes (DOEs)** for
power distribution networks. The package exposes a single high level API and a
plug-in architecture for power-flow formulations and objectives.

## Installation

```bash
pip install -e .
```

## Quickstart

```python
from doe.compute import DOE

  result = DOE.compute("toy.py", powerflow_mode="dc", objective="global_sum", alpha=1.0, beta=1.0)
print(result["objective_value"])
```

## Parameters

  - `network`: a :mod:`pandapower` network object or the name of a Python module
    in the repository-level ``networks`` directory (e.g. ``"toy.py"``).
- `powerflow_mode`: `"dc"` or `"ac"`. The AC mode is not implemented yet.
- `objective`: `"global_sum"` or `"fairness"`. The fairness objective is not
  implemented yet.
- `alpha`, `beta`: positive floats penalising curtailment budget and envelope
  centre gap respectively.
- `parents`, `children`, `operational_nodes`: optional iterables specifying
  node roles in the network. Defaults assume the first bus is the parent and
  the remaining buses are children.

## Results

`DOE.compute` returns a dictionary with keys:

- `status`: solver termination condition.
- `objective_value`: value of the objective.
- `envelopes`: mapping of child nodes to envelope endpoints.
- `curtailment_report`: value of the curtailment budget variable.
- `diagnostics`: raw solver information.

## Extending

New power flow modes or objectives can be added as modules and registered in
`registry.py`. See `EXTENDING.md` for details.
