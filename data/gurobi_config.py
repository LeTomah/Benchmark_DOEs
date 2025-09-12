"""Utilities for configuring Gurobi WLS credentials.

Read the credentials from environment variables to avoid
hardcoding secrets in the source code. The following environment
variables are used:

- ``GUROBI_WLSACCESSID``
- ``GUROBI_WLSSECRET``
- ``GUROBI_LICENSEID`` (optional)

Only the variables that are defined are passed to the Gurobi
environment. This keeps configuration lightweight and flexible.
"""

from __future__ import annotations

import os
from typing import Any, Dict


def get_wls_params() -> Dict[str, Any]:
    """Return a dictionary with Gurobi WLS parameters.

    The function reads credentials from environment variables and
    returns a dictionary compatible with :class:`gurobipy.Env`.
    Undefined variables are ignored, so only the provided values
    are passed to Gurobi.
    """
    params: Dict[str, Any] = {}

    access_id = os.getenv("GUROBI_WLSACCESSID")
    if access_id:
        params["WLSACCESSID"] = access_id

    secret = os.getenv("GUROBI_WLSSECRET")
    if secret:
        params["WLSSECRET"] = secret

    license_id = os.getenv("GUROBI_LICENSEID")
    if license_id:
        try:
            params["LICENSEID"] = int(license_id)
        except ValueError:
            raise ValueError("GUROBI_LICENSEID must be an integer")

    return params