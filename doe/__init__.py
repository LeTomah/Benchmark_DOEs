"""DOE modular library."""

from __future__ import annotations

from .compute import compute


class DOE:
    """Namespace exposing the :func:`compute` function."""

    compute = staticmethod(compute)


__all__ = ["DOE", "compute"]
