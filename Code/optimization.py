import graph
import pyo_environment
import pyomo.environ as pyo
import gurobipy as gp
from loader import load_network
import constraints_opf
import constraints_DOE
from Data.gurobi_config import get_wls_params


def _build_gurobi_solver():
    """Create a Gurobi solver with credentials from the environment."""
    env = gp.Env(params=get_wls_params())
    return pyo.SolverFactory('gurobi', env=env)


def run_model(env_tuple, constraints_module):
    m, G = env_tuple
    constraints_module.constraints(m, G)
    solver = _build_gurobi_solver()
    results = solver.solve(m, tee=True)
    flows = {(u, v): m.F[u, v, 0, 0].value for (u, v) in m.Lines}
    status = str(results.solver.status)
    obj = pyo.value(m.objective)
    return {"status": status, "objective": obj, "flows": flows, "model": m, "graph": G}


def extract_info(res_full, children):
    m = res_full["model"]
    info = {}
    for c in children:
        val = m.E[c, 0, 0].value if (c in m.children) else 0.0
        info[c] = float(val if val is not None else 0.0)
    return info


def optim_problem(test_case,
                  operational_nodes=None,
                  parent_nodes=None,
                  children_nodes=None,
                  opf_only=False):
    net = load_network(test_case)
    full_graph = graph.create_graph(net)

    env_full = pyo_environment.create_pyo_env(graph=full_graph,
                                              parent_nodes=parent_nodes,
                                              children_nodes=children_nodes,
                                              info_DSO=None)

    res_full = run_model(env_full, constraints_opf)
    if opf_only:
        return res_full

    children_set = set(children_nodes or [])
    info_DSO = extract_info(res_full, children_set)

    op_graph = graph.op_graph(full_graph, set(operational_nodes or full_graph.nodes()))
    parents_op = list(set(parent_nodes or []) & set(op_graph.nodes()))
    children_op = list(set(children_nodes or []) & set(op_graph.nodes()))

    env_op = pyo_environment.create_pyo_env(graph=op_graph,
                                            operational_nodes=list(op_graph.nodes()),
                                            parent_nodes=parents_op,
                                            children_nodes=children_op,
                                            info_DSO=info_DSO)

    res_op = run_model(env_op, constraints_DOE)

    return {"full": res_full, "operational": res_op}
