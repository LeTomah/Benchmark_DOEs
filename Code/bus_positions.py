import json
import math
from typing import Dict, Tuple

def extract_bus_positions(net) -> Dict[int, Tuple[float, float]]:
    """Return a mapping of bus indices to ``(x, y)`` positions.

    The function tries several sources to obtain coordinates:

    A. ``net.bus['geo']`` containing a GeoJSON ``Point`` as a JSON string.
    B. ``net.bus['geo']`` containing a mapping or a shapely ``Point``.
    C. ``net.bus_geodata`` with ``x`` and ``y`` columns.
    D. As a last resort, generic coordinates are generated and converted to
       GeoJSON before retrying the previous steps.

    Returns
    -------
    dict
        Mapping ``{bus_idx: (x, y)}`` where both ``x`` and ``y`` are floats.

    Raises
    ------
    ValueError
        If coordinates cannot be determined for all buses.
    """

    try:  # Optional dependency
        from shapely.geometry import Point, shape
    except Exception:  # pragma: no cover - shapely is optional
        Point = None
        shape = None

    def _parse_geo(geo):
        """Extract coordinates from various geo representations."""
        if geo is None or (isinstance(geo, float) and math.isnan(geo)):
            return None
        # GeoJSON string
        if isinstance(geo, str):
            try:
                geo = json.loads(geo)
            except json.JSONDecodeError:
                return None

        # shapely Point instance
        if Point is not None and isinstance(geo, Point):
            return float(geo.x), float(geo.y)

        # Mapping GeoJSON or anything accepted by shapely.shape
        if isinstance(geo, dict):
            coords = geo.get("coordinates")
            if isinstance(coords, (list, tuple)) and len(coords) == 2:
                return float(coords[0]), float(coords[1])
            if shape is not None:
                try:
                    geom = shape(geo)
                    if isinstance(geom, Point):
                        return float(geom.x), float(geom.y)
                except Exception:
                    return None
        return None

    def _from_geodata(idx):
        if getattr(net, "bus_geodata", None) is not None:
            if idx in net.bus_geodata.index:
                x = net.bus_geodata.at[idx, "x"] if "x" in net.bus_geodata.columns else None
                y = net.bus_geodata.at[idx, "y"] if "y" in net.bus_geodata.columns else None
                if x is not None and y is not None and not (
                    (isinstance(x, float) and math.isnan(x)) or (isinstance(y, float) and math.isnan(y))
                ):
                    return float(x), float(y)
        return None

    def _attempt_extraction():
        positions: Dict[int, Tuple[float, float]] = {}
        for idx, row in net.bus.iterrows():
            xy = _parse_geo(row.get("geo"))
            if xy is None:
                xy = _from_geodata(idx)
            if xy is not None:
                positions[idx] = xy
        return positions

    pos = _attempt_extraction()
    missing = set(net.bus.index) - set(pos)

    if missing:
        # Generate generic coordinates only when bus_geodata is missing or incomplete
        need_generic = not hasattr(net, "bus_geodata") or len(getattr(net, "bus_geodata", [])) < len(net.bus)
        if not need_generic and hasattr(net, "bus_geodata"):
            try:
                need_generic = net.bus_geodata[["x", "y"]].isna().any().any()
            except Exception:
                need_generic = True
        if need_generic:
            from pandapower.plotting import create_generic_coordinates
            create_generic_coordinates(net, overwrite=False)

        from pandapower.plotting.geo import convert_geodata_to_geojson
        convert_geodata_to_geojson(net)

        pos = _attempt_extraction()
        missing = set(net.bus.index) - set(pos)

    if missing:
        raise ValueError(f"Impossible de déterminer des coordonnées pour les bus {sorted(missing)}")

    for idx, (x, y) in pos.items():
        name = net.bus.at[idx, "name"] if "name" in net.bus.columns else str(idx)
        print(f'"{name}": ({x}, {y})')

    return pos