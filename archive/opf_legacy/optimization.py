import gurobipy as gp
import pyomo.environ as pyo

from data.gurobi_config import get_wls_params
from viz.plot_DOE import plot_DOE

from . import constraints_doe as cdoe, constraints_opf as copf, graph, pyo_environment
from .loader import load_network


def _build_gurobi_solver():
    """Configure and return a Gurobi solver for Pyomo."""
    env = gp.Env(params=get_wls_params())
    return pyo.SolverFactory("gurobi", env=env)


def _solve_and_pack(m, G, objective_name: str):
    """Solve a model and return a small result dictionary."""
    solver = _build_gurobi_solver()
    results = solver.solve(m, tee=True)
    status = str(results.solver.status)
    obj = pyo.value(getattr(m, objective_name))
    return {"status": status, "objective": obj, "model": m, "graph": G}


def optim_problem(
    test_case,
    operational_nodes=None,
    parent_nodes=None,
    children_nodes=None,
    alpha: float = 1.0,
    beta: float = 1.0,
    plot_doe: bool = True,
    P_min: float = -1.0,
    P_max: float = 1.0
):
    """Run either an OPF or DOE optimisation on the given network.

    Parameters
    ----------
    test_case: str or pandapowerNet
        Network description to load.
    operational_nodes, parent_nodes, children_nodes: iterable
        Definition of the operational perimeter and boundary nodes.
    alpha, beta: float
        Weights used in the objective function of the DOE optimisation.
    plot_doe: bool
        If ``True`` the DOE result for each run is plotted.  This is mainly
        useful for interactive debugging; when scanning many ``alpha`` values
        the plots can be disabled to avoid cluttering the output.
    P_min, P_max: float
        Bounds applied to the power exchanged with parent nodes.  They are
        passed down to the Pyomo environment construction.
    """

    # 1) Charger le réseau et créer le graphe complet
    net = load_network(test_case)
    full_graph = graph.create_graph(net)

    # 2) Cas OPF : operational_nodes == []  →  OPF sur graphe complet
    if operational_nodes is not None and len(operational_nodes) == 0:
        env_full = pyo_environment.create_pyo_env(
            graph=full_graph,
            parent_nodes=parent_nodes,
            children_nodes=children_nodes,
            info_DSO=None,
            alpha=alpha,
            beta=beta,
            P_min=P_min,
            P_max=P_max
        )
        m, G = env_full
        copf.apply(m, G)
        res_full = _solve_and_pack(m, G, "objective_opf")
        return {"full": res_full, "full_graph": full_graph}

    # 3) Cas DOE : operational_nodes non vide  →  DOE sur sous-graphe
    operational_nodes = list(operational_nodes or full_graph.nodes())
    op_graph = graph.op_graph(full_graph, set(operational_nodes))

    # restreindre parents/enfants au sous-graphe
    parents_op = list(set(parent_nodes or []) & set(op_graph.nodes()))
    children_op = list(set(children_nodes or []) & set(op_graph.nodes()))

    # calcul info_DSO depuis le graphe complet (hors périmètre)
    info_DSO = graph.compute_info_dso(
        G=full_graph,
        operational_nodes=operational_nodes,
        children_nodes=children_op,
        p_attr="P",
    )

    env_op = pyo_environment.create_pyo_env(
        graph=op_graph,
        operational_nodes=list(op_graph.nodes()),
        parent_nodes=parents_op,
        children_nodes=children_op,
        info_DSO=info_DSO,
        alpha=alpha,
        beta=beta,
        P_min=P_min,
        P_max=P_max
    )
    m, G = env_op
    cdoe.apply(m, G)  # crée m.objective_doe
    result = _solve_and_pack(m, G, "objective_doe")
    if plot_doe:
        plot_DOE(m)
    return {"operational": result, "full_graph": full_graph}
