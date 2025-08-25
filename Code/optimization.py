import graph
import pyo_environment
import pyomo.environ as pyo
import gurobipy as gp
from loader import load_network
import constraints
import constraints_opf as copf
from Data.gurobi_config import get_wls_params


def _build_gurobi_solver():
    env = gp.Env(params=get_wls_params())
    return pyo.SolverFactory('gurobi', env=env)


def _solve_and_pack(m, G, objective_name: str):
    solver = _build_gurobi_solver()
    results = solver.solve(m, tee=True)
    status = str(results.solver.status)
    obj = pyo.value(getattr(m, objective_name))
    return {"status": status, "objective": obj, "model": m, "graph": G}


def optim_problem(test_case,
                  operational_nodes=None,
                  parent_nodes=None,
                  children_nodes=None):
    # 1) Charger le réseau et créer le graphe complet
    net = load_network(test_case)
    full_graph = graph.create_graph(net)

    # 2) Cas OPF : operational_nodes == []  →  OPF sur graphe complet
    if operational_nodes is not None and len(operational_nodes) == 0:
        env_full = pyo_environment.create_pyo_env(
            graph=full_graph,
            parent_nodes=parent_nodes,
            children_nodes=children_nodes,
            info_DSO=None
        )
        m, G = env_full
        copf.apply(m, G)
        return {"full": _solve_and_pack(m, G, "objective_opf")}

    # 3) Cas DOE : operational_nodes non vide  →  DOE sur sous-graphe
    operational_nodes = list(operational_nodes or full_graph.nodes())
    op_graph = graph.op_graph(full_graph, set(operational_nodes))

    # restreindre parents/enfants au sous-graphe
    parents_op  = list(set(parent_nodes or []) & set(op_graph.nodes()))
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
        info_DSO=info_DSO
    )
    m, G = env_op
    constraints.constraints(m, G)  # crée m.objective_doe
    return {"operational": _solve_and_pack(m, G, "objective_doe")}
