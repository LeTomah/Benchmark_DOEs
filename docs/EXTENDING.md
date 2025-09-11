# Extending DOE

The library uses simple registries to map short names to implementation
functions. New modules can be added without modifying the core pipeline.

## Adding a power flow mode
1. Create a module under `doe/constraints/` exposing a `build(model, data,
   params, logger)` function.
2. Register it in `doe/registry.py` within `POWERFLOW_REGISTRY`.

## Adding a security constraint
Add new helper functions in `doe/constraints/security.py` and call them from
`attach_security_constraints`.

## Adding an objective
1. Create a module under `doe/objectives/` with a `build(model, data, params,
   logger)` function returning a Pyomo objective.
2. Register it in `OBJECTIVE_REGISTRY` in `doe/registry.py`.
