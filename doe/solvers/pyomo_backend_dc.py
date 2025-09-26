"""Pyomo model construction and solving utilities."""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

import math

import pyomo.environ as pyo

from data.gurobi_config import get_wls_params

PowerflowBuilder = Callable[[pyo.ConcreteModel, Any], None]
ObjectiveBuilder = Callable[[pyo.ConcreteModel, Dict[str, Any]], None]
SecurityBuilder = Callable[[pyo.ConcreteModel, Any], None]


def build_sets(m: pyo.ConcreteModel,
               G: Any,
               parent_nodes,
               children_nodes):
    """Initialise core Pyomo sets shared by all builders."""

    m.Nodes = pyo.Set(initialize=list(G.nodes))
    m.Lines = pyo.Set(initialize=list(G.edges))
    m.VertP = pyo.Set(initialize=[0, 1])
    m.VertV = pyo.Set(initialize=[0, 1])
    m.parents = pyo.Set(initialize=parent_nodes)
    m.children = pyo.Set(initialize=children_nodes)

def build_params(m: pyo.ConcreteModel,
                 G: Any,
                 info_P,
                 alpha,
                 beta,
                 P_min,
                 P_max
                 ) -> None:
    """Populate Pyomo parameters used by the simplified DOE backend.

    Parameters
    ----------
    m : pyomo.ConcreteModel
        Model to populate with parameters.
    G : networkx.Graph
        Electrical network providing nodal data and line attributes.
    params : dict
        Mapping expected to contain keys such as ``info_DSO``, ``alpha``,
        ``beta``, ``P_min`` and ``P_max``.  Missing values fall back to the
        defaults defined inside the function.
    options : dict
        Solver options passed from :func:`doe.compute.compute`.  Currently not
        interpreted but accepted for API compatibility.
    children : list
        Identifiers of child nodes receiving DSO information.
    """

    m.P = pyo.Param(
        m.Nodes,
        initialize={n: G.nodes[n].get("P", 0.0) for n in G.nodes},
        domain=pyo.Reals,
        mutable=True,
    )
    m.PositiveNodes = pyo.Set(
        initialize=[n for n in m.Nodes if G.nodes[n].get("P", 0.0) > 0]
    )
    m.NegativeNodes = pyo.Set(
        initialize=[n for n in m.Nodes if G.nodes[n].get("P", 0.0) < 0]
    )
    m.info_P = pyo.Param(
        m.children,
        initialize={n: float(info_P.get(n, 0.0)) for n in m.children},
        domain=pyo.Reals,
    )
    m.positive_demand = pyo.Set(
        initialize=[n for n in m.children if pyo.value(m.info_P[n]) > 0]
    )
    m.negative_demand = pyo.Set(
        initialize=[n for n in m.children if pyo.value(m.info_P[n]) < 0]
    )
    m.V_min = pyo.Param(initialize=0.9)
    m.V_max = pyo.Param(initialize=1.1)
    m.V_P = pyo.Param(m.VertV, initialize={0: 0.9, 1: 1.1}, domain=pyo.NonNegativeReals)
    m.P_min = pyo.Param(initialize=P_min)
    m.P_max = pyo.Param(initialize=P_max)
    m.theta_min = pyo.Param(initialize=-0.25)
    m.theta_max = pyo.Param(initialize=0.25)
    m.alpha = pyo.Param(initialize=alpha)
    m.beta = pyo.Param(initialize=beta)
    m.I_min = pyo.Param(
        m.Lines,
        initialize={
            (u, v): G[u][v].get("I_min_pu", -1) for (u, v) in m.Lines
        },
        domain=pyo.Reals,
    )
    m.I_max = pyo.Param(
        m.Lines,
        initialize={
            (u, v): G[u][v].get("I_max_pu", 1) for (u, v) in m.Lines
        },
        domain=pyo.Reals,
    )

def build_variables(m: pyo.ConcreteModel, G: Any | None = None) -> None:
    """Create the decision variables used across the DOE models."""
    m.F = pyo.Var(m.Lines, m.VertP, m.VertV, domain=pyo.Reals)
    m.I = pyo.Var(m.Lines, m.VertP, m.VertV, domain=pyo.Reals)
    m.theta = pyo.Var(m.Nodes, m.VertP, m.VertV, domain=pyo.Reals)
    m.V = pyo.Var(m.Nodes, m.VertP, m.VertV, domain=pyo.NonNegativeReals)
    m.E = pyo.Var(m.Nodes, m.VertP, m.VertV, domain=pyo.Reals)
    m.P_plus = pyo.Var(m.parents, m.VertP, m.VertV, domain=pyo.Reals)
    m.P_minus = pyo.Var(m.children, m.VertP, m.VertV, domain=pyo.Reals)
    m.P_C_set = pyo.Var(m.children, m.VertP, domain=pyo.Reals)
    m.z = pyo.Var(m.Nodes, m.VertP, m.VertV, domain=pyo.NonNegativeReals)
    m.curt = pyo.Var(m.Nodes, m.VertP, m.VertV, domain=pyo.Reals)
    m.aux = pyo.Var(m.children, domain=pyo.Reals)
    m.envelope_volume = pyo.Var(domain=pyo.Reals)

    #Curtailment budget
    total_p_abs = sum(abs(pyo.value(m.P[n])) for n in m.Nodes)
    m.curtailment_budget = pyo.Var(domain=pyo.NonNegativeReals, bounds=(-total_p_abs, total_p_abs))

    m.diff_DSO = pyo.Var(m.children, domain=pyo.NonNegativeReals)
    m.envelope_center_gap = pyo.Var(domain=pyo.Reals)


def build_expressions(m: pyo.ConcreteModel, G: Any) -> None:
    """Create auxiliary Pyomo expressions if required.

    The DC backend currently does not rely on additional Pyomo expressions, but
    the helper mirrors the public API exposed in :mod:`archive.pyo_environment`.
    """

    # No additional expressions are required for the simplified DC backend.
    return

def create_pyo_env(
    graph,
    operational_nodes=None,
    parent_nodes=None,
    children_nodes=None,
    info_DSO: Optional[Dict[int, float]] = None,
    alpha: float = 1.0,
    beta: float = 1.0,
    P_min: float = -1.0,
    P_max: float = 1.0,
):
    """Create and populate a Pyomo model from a NetworkX graph.

    Parameters
    ----------
    graph : networkx.Graph
        Complete network graph, typically produced by
        :func:`archive.graph.create_graph`.
    operational_nodes : Iterable[int], optional
        Subset of nodes forming the operational perimeter.  When ``None`` the
        full graph is used.
    parent_nodes, children_nodes : Iterable[int], optional
        Boundary nodes used to exchange power with the outside grid.
    info_DSO : Mapping[int, float], optional
        External demand estimates for child nodes.
    alpha, beta : float, optional
        Objective weights used by DOE formulations.
    P_min, P_max : float, optional
        Bounds on the power injected at parent nodes.

    Returns
    -------
    tuple
        ``(model, graph)`` where ``model`` is a populated
        :class:`pyomo.ConcreteModel` and ``graph`` the induced operational
        subgraph.
    """

    G_full = graph
    if operational_nodes is None:
        operational_nodes = list(G_full.nodes)

    G = G_full.subgraph(operational_nodes).copy()

    if parent_nodes is None and children_nodes:
        raise ValueError("parent_nodes must be provided for DOE problems")

    m = pyo.ConcreteModel()
    build_sets(m, G, parent_nodes or [operational_nodes[0]], children_nodes or [])
    build_params(m, G, info_DSO or {}, alpha, beta, P_min, P_max)
    build_variables(m, G)
    build_expressions(m, G)

    return m, G


# ---------------------------------------------------------------------------
# Legacy solver pipeline preserved for backwards compatibility
# ---------------------------------------------------------------------------

def solve_model(
    G: Any,
    powerflow_builder: PowerflowBuilder,
    security_builder: SecurityBuilder,
    objective_builder: ObjectiveBuilder,
    params: Dict[str, Any],
    options: Dict[str, Any],
) -> Dict[str, Any]:
    """Build and solve a DOE Pyomo model using scalar power limits."""

    # Older revisions reconstructed ``P_min``/``P_max`` from a ``p_limits``
    # mapping.  That normalisation step is kept below for documentation because
    # user interfaces used to expose per-node dictionaries.
    # p_limits_option = options.get("p_limits")
    # if isinstance(p_limits_option, dict):
    #     P_min = min(limits.get("pmin", 0.0) for limits in p_limits_option.values())
    #     P_max = max(limits.get("pmax", 0.0) for limits in p_limits_option.values())
    # else:
    #     P_min, P_max = p_limits_option

    P_min = float(options["P_min"])
    P_max = float(options["P_max"])

    m, operational_graph = create_pyo_env(
        graph=G,
        operational_nodes=options.get("operational_nodes"),
        parent_nodes=options.get("parent_nodes"),
        children_nodes=options.get("children_nodes"),
        info_DSO=options.get("info_DSO") or {},
        alpha=float(params.get("alpha", 1.0)),
        beta=float(params.get("beta", 1.0)),
        P_min=P_min,
        P_max=P_max,
    )

    powerflow_builder(m, operational_graph)
    security_builder(m, operational_graph)
    objective_builder(m, params)

    try:
        env_params = get_wls_params()
        solver = pyo.SolverFactory("gurobi", solver_io="python")
        if env_params:
            solver.options.update(env_params)
        result = solver.solve(m, tee=False)
        status = str(result.solver.termination_condition)
    except Exception:  # pragma: no cover - fallback when solver missing
        result = None
        status = "not_solved"

    # Tolère les résolutions impossibles en gardant une valeur numérique sûre.
    objective_raw = pyo.value(m.objective, exception=False)
    objective_val = float(objective_raw) if objective_raw is not None else math.nan

    envelopes: Dict[Any, tuple[float, float]] = {}

    if hasattr(m, "P_C_set") and hasattr(m, "children"):
        vertices = list(m.VertP)
        for node in m.children:
            # Ignore les entrées sans valeur (cas "not_solved").
            values = []
            for v in vertices:
                p_val = pyo.value(m.P_C_set[node, v], exception=False)
                if p_val is not None:
                    values.append(float(p_val))
            if values:
                lower = min(values)
                upper = max(values)
                envelopes[node] = (lower, upper)

    if not envelopes:
        # When the DOE formulation does not populate ``P_C_set`` (e.g. legacy
        # pipelines), fall back to the global parent bounds to maintain a
        # meaningful payload for API consumers.
        parent_bounds = (float(pyo.value(m.P_min)), float(pyo.value(m.P_max)))
        envelopes = {node: parent_bounds for node in getattr(m, "parents", [])}

    return {
        "status": status,
        "objective": objective_val,
        "envelopes": envelopes,
        "curtailment_report": {},
        "diagnostics": {
            "solver": status,
        },
    }
