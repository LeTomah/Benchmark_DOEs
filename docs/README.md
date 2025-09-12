# DOE Library

This project provides a minimal modular library for computing Distribution
Operation Envelopes (DOEs). The main entry point is `DOE.compute` which
accepts a pandapower network or the name of a network available in
`data/networks`.

```python
from doe import DOE
result = DOE.compute("network_test", "dc", "global_sum", alpha=0.1, beta=0.2)
print(result["status"], result["objective_value"])
```
