import graph
import pyo_environment
import pyomo.environ as pyo
import gurobipy as gp
from loader import load_network

# Retrieve Gurobi credentials from environment variables instead of
# hardcoding them in the source code. See ``gurobi_config`` for
# details on the expected variables.
from Code.Data.gurobi_config import get_wls_params

def _build_gurobi_solver():
    """Create a Gurobi solver with credentials from the environment."""
    env = gp.Env(params=get_wls_params())
    return pyo.SolverFactory('gurobi', env=env)

def constraints(m, G):

#Consommation aux noeuds enfants
    # info_DSO_node1 = m.F[1, 3, 0, 0].value
    # info_DSO_node2 = m.F[2, 4, 0, 0].value
    # print("info_DSO_1: ", info_DSO_node1)
    # print("info_DSO_2: ",info_DSO_node2)
    #
    # info_DSO = [info_DSO_node1, info_DSO_node2]

    # Children nodes consumption
    def worst_case_children(m, u, vert_pow, vert_volt):
        return m.P_C_set[u, vert_pow] == m.P_minus[u, vert_pow, vert_volt]
    m.worst_case = pyo.Constraint(m.children, m.i, m.j, rule=worst_case_children)

    # Auxiliary variable for the absolute value of E (already defined as per-unit)
    m.z = pyo.Var(m.Nodes, m.i, m.j, domain=pyo.NonNegativeReals)

    m.curt = pyo.Var(m.Nodes, m.i, m.j, domain=pyo.Reals)

    def curtailment_def_rule(m, u, vert_pow, vert_volt):
        return m.curt[u, vert_pow, vert_volt] == m.P[u] - m.E[u, vert_pow, vert_volt]
    m.curt_def = pyo.Constraint(m.Nodes, m.i, m.j, rule=curtailment_def_rule)

    # Constraints to define the absolute value (already defined for per-unit E)
    def abs_E_pos_rule(m, u, vert_pow, vert_volt):
        return m.z[u, vert_pow, vert_volt] >= m.curt[u, vert_pow, vert_volt]
    m.abs_E_pos = pyo.Constraint(m.Nodes, m.i, m.j, rule=abs_E_pos_rule)

    def abs_E_neg_rule(m, u, vert_pow, vert_volt):
        return m.z[u, vert_pow, vert_volt] >= -m.curt[u, vert_pow, vert_volt]
    m.abs_E_neg = pyo.Constraint(m.Nodes, m.i, m.j, rule=abs_E_neg_rule)

    def upper_bound_rule(m, vert_pow, vert_volt):
        # m.z is per-unit, m.O is per-unit
        return sum(m.z[n, vert_pow, vert_volt] for n in m.Nodes) <= m.O
    m.upper_bound = pyo.Constraint(m.i, m.j, rule=upper_bound_rule)

    # Current magnitude constraint (I_min, I_max are assumed per-unit)
    def current_bounds_rule(m, u, v, vert_pow, vert_volt):
        # m.I is per-unit current
        return pyo.inequality(m.I_min[u, v], m.I[u, v, vert_pow, vert_volt], m.I_max[u, v])
    m.CurrentBounds = pyo.Constraint(m.Lines, m.i, m.j, rule=current_bounds_rule)

    def phase_constr_rule(m, u, vert_pow, vert_volt):
        return pyo.inequality(m.theta_min, m.theta[u, vert_pow, vert_volt], m.theta_max)
    m.phaseConstr = pyo.Constraint(m.Nodes, m.i, m.j, rule=phase_constr_rule)

    def dc_power_flow_rule(m, u, v, vert_pow, vert_volt):
        if G[u][v]['b_pu']==None:
            return pyo.Constraint.Skip
        else:
            return m.F[u, v, vert_pow, vert_volt] == m.V_P[vert_volt] ** 2 * (G[u][v]['b_pu'] * (
                    m.theta[u, vert_pow, vert_volt] - m.theta[v, vert_pow, vert_volt]))
    m.DCFlow = pyo.Constraint(m.Lines, m.i, m.j, rule=dc_power_flow_rule)

    def current_def_rule(m, u, v, vert_pow, vert_volt):
        # This constraint relates per-unit current, per-unit voltage, and per-unit power flow.
        # In per-unit, P_pu = V_pu * I_pu. This is correct.
        return m.I[u, v, vert_pow, vert_volt] * m.V_P[vert_volt] == m.F[u, v, vert_pow, vert_volt]
    m.current_def = pyo.Constraint(m.Lines, m.i, m.j, rule=current_def_rule)

    def power_balance_rule(m, n, vert_pow, vert_volt):
        # Compute net flow into node n by summing over all lines (i,j) in m.Lines
        expr = sum(
            (m.F[i, j, vert_pow, vert_volt] if j == n else 0)
            - (m.F[i, j, vert_pow, vert_volt] if i == n else 0)
            for (i, j) in m.Lines)
        # If n is a parent node, subtract P_plus; otherwise use only E[n]
        if n in m.parents:
            return expr == m.E[n, vert_pow, vert_volt] - m.P_plus[n, vert_pow, vert_volt]
        else:
            return expr == m.E[n, vert_pow, vert_volt]
    m.power_balance = pyo.Constraint(m.Nodes, m.i, m.j, rule=power_balance_rule)

    def parent_power_constraint_rule(m, parent, vert_pow, vert_volt):
        # m.P_plus is per-unit power entering the operational graph
        return pyo.inequality(m.P_min, m.P_plus[parent, vert_pow, vert_volt], m.P_max)
    m.parent_power_constraint = pyo.Constraint(m.parents, m.i, m.j, rule=parent_power_constraint_rule)

    def parent_power_constraint_rule2(m, parent, vert_pow, vert_volt):
        # m.P_plus is per-unit power entering the operational graph
        return pyo.inequality(m.P_min, m.P_minus[parent, vert_pow, vert_volt], m.P_max)
    m.parent_power_constraint2 = pyo.Constraint(m.children, m.i, m.j, rule=parent_power_constraint_rule2)

    # Constant voltage assumption
    def voltage_constr_rule(m, u, vert_pow, vert_volt):
        return m.V[u, vert_pow, vert_volt] == m.V_P[vert_volt]
    m.voltageConstr = pyo.Constraint(m.Nodes, m.i, m.j, rule=voltage_constr_rule)

    def children_voltage_rule(m, children, vert_pow, vert_volt):
        return pyo.inequality(m.V_min, m.V[children, vert_pow, vert_volt], m.V_max)
    m.children_voltage = pyo.Constraint(m.children, m.i, m.j, rule=children_voltage_rule)

    def aux_constraint_rule(m, u):
        return m.aux[u] == m.P_C_set[u, 0] - m.P_C_set[u, 1]
    m.aux_constraint = pyo.Constraint(m.children, rule=aux_constraint_rule)

    def tot_rule(m):
        return m.tot == sum(m.aux[u] for u in m.children)
    m.tot_constraint = pyo.Constraint(rule=tot_rule)

    def diff_DSO_rule(m, u):
        return - m.diff_DSO[u] <= (m.P_C_set[u, 0] + m.P_C_set[u, 1]) / 2 - m.info_DSO_param[u]
    m.diff_DSO_constraint = pyo.Constraint(m.children, rule=diff_DSO_rule)

    def diff_bis_dso_rule(m, u):
        return (m.P_C_set[u, 0] + m.P_C_set[u, 1]) / 2 - m.info_DSO_param[u] <= m.diff_DSO[u]
    m.diff_bis_dso_constraint = pyo.Constraint(m.children, rule=diff_bis_dso_rule)

    m.tot_bis = pyo.Var(domain=pyo.Reals)
    def tot_bis_rule(m):
        return m.tot_bis == sum(m.diff_DSO[u] for u in m.children)
    m.tot_bis_constraint = pyo.Constraint(rule=tot_bis_rule)

    # -------------------------
    # Objectif
    # -------------------------
    # Define alpha as a parameter of the model


    def objective_rule(m):
        return m.tot - m.alpha * m.O - m.beta * m.tot_bis
    m.objective = pyo.Objective(rule=objective_rule, sense=pyo.maximize)

def run_opf(env_tuple):
    m, G = env_tuple
    constraints(m, G)

    solver = _build_gurobi_solver()
    results = solver.solve(m, tee=True)

    # extrait quelques résultats
    flows = {(u, v): m.F[u, v, 0, 0].value for (u, v) in m.Lines}
    status = str(results.solver.status)
    obj = pyo.value(m.objective)
    return {"status": status, "objective": obj, "flows": flows, "model": m, "graph": G}

def extract_info(res_full, children):
    m = res_full["model"]
    # ici, un exemple simple : moyenne des deux sommets P_C_set
    info = {}
    for c in children:
        val = 0.5 * (m.P_C_set[c, 0].value + m.P_C_set[c, 1].value) if (c in m.children) else 0.0
        info[c] = float(val if val is not None else 0.0)
    return info

def optim_problem(test_case,
                  operational_nodes=None,
                  parent_nodes=None,
                  children_nodes=None,
                  opf_only=False):
    # 1) charge le réseau
    net = load_network(test_case)

    # 2) graphe complet
    full_graph = graph.create_graph(net)

    # 3) env sur graphe complet
    env_full = pyo_environment.create_pyo_env(graph=full_graph,
                                              parent_nodes=None,
                                              children_nodes=children_nodes,
                                              info_DSO=None)

    # 4) OPF complet
    res_full = run_opf(env_full)
    if opf_only:
        return res_full

    # 5) extrait info DSO aux enfants du FULL
    children_set = set(children_nodes or [])
    info_DSO = extract_info(res_full, children_set)

    # 6) sous-graphe opérationnel
    op_graph = graph.op_graph(full_graph, set(operational_nodes or full_graph.nodes()))

    # 7) restreint parents/enfants
    parents_op = list(set(parent_nodes or []) & set(op_graph.nodes()))
    children_op = list(set(children_nodes or []) & set(op_graph.nodes()))

    # 8) env sur le sous-graphe, avec info_DSO
    env_op = pyo_environment.create_pyo_env(graph=op_graph,
                                            operational_nodes=list(op_graph.nodes()),
                                            parent_nodes=parents_op,
                                            children_nodes=children_op,
                                            info_DSO=info_DSO)

    # 9) OPF sur sous-graphe
    res_op = run_opf(env_op)

    return {"full": res_full, "operational": res_op}


#     # -------------------------
#     # Résolution
#     # -------------------------
#     # Create an environment with your WLS license
#     params = {
#         "WLSACCESSID": '295bde64-ffb2-46ce-92c9-af4e12ace58f',
#         "WLSSECRET": '2dc9e249-7d48-4e46-a099-71c52d5d7247',
#         "LICENSEID": 2689995
#     }
#     env = gp.Env(params=params)
#     solver = pyo.SolverFactory('gurobi')
#
#     # Solve the model
#     results = solver.solve(m, tee=True)
#
#     # Print the results
#     print("results: ", results)
#
#     for n in m.Nodes:
#         for vert_pow in m.i:
#             for vert_volt in m.j:
#                 print(f"theta ({n}):{m.theta[n, vert_pow, vert_volt].value}")
#
#     import networkx as nx
#     import matplotlib.pyplot as plt
#
#     def plot_power_flow(m, i, j):
#         pos = nx.get_node_attributes(G, 'pos')
#         # Use node indices as labels
#         labels = {}
#         label_colors = [] # This is for node colors, will remove this later if needed or set to default
#         for n in G.nodes():
#             label_text = f"{n}"
#             if n in m.parents:
#                 # Display parent bounds using the global P_min and P_max parameters
#                 label_text += f"\n[{P_min}, {P_max}]"
#                 # No specific color for label text here, use default
#                 label_colors.append('steelblue') # Default node color based on previous plots
#             elif n in m.children:
#                 # Display children interval with smaller value first
#                 p_c_values = [m.P_C_set[n, 0].value, m.P_C_set[n, 1].value]
#                 label_text += f"\n[{round(min(p_c_values), 4)}, {round(max(p_c_values), 4)}]"
#                 # We will try to color this text red when drawing labels
#                 label_colors.append('steelblue') # Default node color
#             else:
#                 label_colors.append('steelblue') # Default node color
#             labels[n] = label_text
#
#
#         plt.figure(figsize=(12, 8))
#
#         edge_colors = []
#         edge_labels = {}
#
#         for u, v in G.edges():
#             try:
#                 # Correct the sign of the flow value for plotting
#                 flow_value = m.F[u, v, i, j].value
#                 if flow_value is not None:
#                     edge_labels[(u, v)] = f"{round(flow_value, 4)}"
#                     if flow_value > 0:
#                         edge_colors.append('blue')  # Positive flow (now correctly represents flow from u to v)
#                     elif flow_value < 0:
#                         edge_colors.append('red')  # Negative (reverse) flow (now correctly represents flow from v to u)
#                     else:
#                         edge_colors.append('gray') # No flow
#                 else:
#                     edge_colors.append('gray') # No flow value
#             except:
#                 edge_colors.append('gray') # Handle cases where edge might not be in m.F
#
#         # Draw the network
#         nx.draw(
#             G, pos,
#             with_labels=False, # Draw labels separately for color control
#             node_size=1200,
#             edge_color=edge_colors, # Use the calculated edge colors
#             edgecolors="black", font_size=8,
#             alpha=0.85,
#             node_color = label_colors # Apply node colors
#         )
#
#         # Draw labels with different colors
#         for n in G.nodes():
#             x, y = pos[n]
#             text = labels[n]
#             if n in m.children:
#                 plt.text(x, y - 0.1, text, fontsize=10, ha='center', va='top', color='red') # Color children interval red
#             elif n in m.parents:
#                  plt.text(x, y + 0.1, text, fontsize=10, ha='center', va='bottom', color='black') # Color parent bounds black
#             else:
#                  plt.text(x, y, text, fontsize=8, ha='center', va='center', color='black') # Default color for other labels
#
#
#         nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=7, label_pos=0.3)
#
#         plt.title(f"Power Flow (per-unit) for i={i}, j={j}")
#         plt.axis("equal")
#         plt.show()
#
#     # Example usage (assuming m, i=0, and j=0 are defined)
#     plot_power_flow(m, 0, 1)
#
#
#
# if __name__ == "__main__":
#     optim_problem("Case_14.txt")