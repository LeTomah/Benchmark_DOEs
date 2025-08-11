def optim_problem(test_case,
                  operational_nodes=None,
                  parent_nodes=None,
                  children_nodes=None):
    import digraph
    import pyo_environment
    import numpy as np
    import pyomo.environ as pyo
    import gurobipy as gp

    # Afficher les nœuds disponibles
    G_full = digraph.create_digraph(test_case)

    digraph.plot_network(G_full)

    # # --- Asking for operational nodes ---
    # user_input_nodes = input("Entrez les ID des nœuds opérationnels (ex: 0,1,2): ")
    # operational_nodes = [int(x.strip()) for x in user_input_nodes.split(",")]

    # # --- Asking for parent node ---
    # user_input_parents = input(f"Entrez les ID des nœuds parents parmi {operational_nodes} (ex: 0): ")
    # parent_nodes = [int(x.strip()) for x in user_input_parents.split(",")]

    # # --- Asking for children nodes ---
    # user_input_children = input(f"Entrez les ID des nœuds enfants parmi {operational_nodes} (ex: 1,2): ")
    # child_nodes = [int(x.strip()) for x in user_input_children.split(",")]

    # --- Model creation with these choices ---
    m = pyo_environment.create_pyo_environ(
        test_case,
        operational_nodes=operational_nodes,
        parent_nodes=parent_nodes,
        children_nodes=children_nodes
    )
    G = G_full.subgraph(operational_nodes).copy()
    # -------------------------
    # Constraints
    # -------------------------

    # Constant definition
    V_min = 0
    V_max = 100

    I_min = -1
    I_max = 1

    P_min = -2
    P_max = 2

    theta_min = -200
    theta_max = 200

    alpha = 1000

    # Children nodes consumption
    def worst_case_children(m, n, vert_pow, vert_volt):
        return m.P_C_set[n, vert_pow] == m.P_minus[n, vert_pow, vert_volt]

    m.worst_case = pyo.Constraint(m.children, m.i, m.j, rule=worst_case_children)

    # Auxiliary variable for the absolute value of E (already defined as per-unit)
    m.z = pyo.Var(m.Nodes, m.i, m.j, domain=pyo.NonNegativeReals)

    m.curt = pyo.Var(m.Nodes, m.i, m.j, domain=pyo.Reals)

    def curtailment_def_rule(m, n, vert_pow, vert_volt):

        return m.curt[n, vert_pow, vert_volt] == m.P[n] - m.E[n, vert_pow, vert_volt]

    m.curt_def = pyo.Constraint(m.Nodes, m.i, m.j, rule=curtailment_def_rule)

    # Constraints to define the absolute value (already defined for per-unit E)
    def abs_E_pos_rule(m, n, vert_pow, vert_volt):
        return m.z[n, vert_pow, vert_volt] >= m.curt[n, vert_pow, vert_volt]

    m.abs_E_pos = pyo.Constraint(m.Nodes, m.i, m.j, rule=abs_E_pos_rule)

    def abs_E_neg_rule(m, n, vert_pow, vert_volt):
        return m.z[n, vert_pow, vert_volt] >= -m.curt[n, vert_pow, vert_volt]

    m.abs_E_neg = pyo.Constraint(m.Nodes, m.i, m.j, rule=abs_E_neg_rule)

    def upper_bound_rule(m, vert_pow, vert_volt):
        # m.z is per-unit, m.O is per-unit
        return sum(m.z[n, vert_pow, vert_volt] for n in m.Nodes) <= m.O

    m.upper_bound = pyo.Constraint(m.i, m.j, rule=upper_bound_rule)

    # Current magnitude constraint (I_min, I_max are assumed per-unit)
    def current_bounds_rule(m, i, j, vert_pow, vert_volt):
        # m.I is per-unit current
        return pyo.inequality(I_min, m.I[i, j, vert_pow, vert_volt], I_max)

    m.CurrentBounds = pyo.Constraint(m.Lines, m.i, m.j, rule=current_bounds_rule)

    def phase_constr_rule(m, n, vert_pow, vert_volt):
        return pyo.inequality(theta_min, m.theta[n, vert_pow, vert_volt], theta_max)

    m.phaseConstr = pyo.Constraint(m.Nodes, m.i, m.j, rule=phase_constr_rule)

    def dc_power_flow_rule(m, i, j, vert_pow, vert_volt):
        return m.F[i, j, vert_pow, vert_volt] == m.V_P[vert_volt] ** 2 * (G[i][j]['b_pu'] * (
                m.theta[i, vert_pow, vert_volt] - m.theta[j, vert_pow, vert_volt])
                                                                          )

    m.DCFlow = pyo.Constraint(m.Lines, m.i, m.j, rule=dc_power_flow_rule)

    def current_def_rule(m, n, i, j, vert_pow, vert_volt):
        # This constraint relates per-unit current, per-unit voltage, and per-unit power flow.
        # In per-unit, P_pu = V_pu * I_pu. This is correct.
        return m.I[i, j, vert_pow, vert_volt] * m.V_P[vert_volt] == m.F[i, j, vert_pow, vert_volt]

    m.current_def = pyo.Constraint(m.Nodes, m.Lines, m.i, m.j, rule=current_def_rule)

    def nodes_balance(m, n, vert_pow, vert_volt):
        inflow = sum(m.F[k, n, vert_pow, vert_volt] for k in G.predecessors(n) if (k, n) in m.Lines)
        outflow = sum(m.F[n, j, vert_pow, vert_volt] for j in G.successors(n) if (n, j) in m.Lines)
        if n in m.parents:
            return inflow - outflow == m.E[n, vert_pow, vert_volt] - m.P_plus[n, vert_pow, vert_volt]

        if n in m.children:
            return inflow - outflow == m.E[n, vert_pow, vert_volt] + m.P_minus[n, vert_pow, vert_volt]

        else:
            return inflow - outflow == m.E[n, vert_pow, vert_volt]

    m.nodes_balance = pyo.Constraint(m.Nodes, m.i, m.j, rule=nodes_balance)

    def parent_power_constraint_rule(m, parent, vert_pow, vert_volt):
        # m.P_plus is per-unit power entering the operational graph
        return pyo.inequality(P_min, m.P_plus[parent, vert_pow, vert_volt], P_max)

    m.parent_power_constraint = pyo.Constraint(m.parents, m.i, m.j, rule=parent_power_constraint_rule)

    def parent_power_constraint_rule2(m, parent, vert_pow, vert_volt):
        # m.P_plus is per-unit power entering the operational graph
        return pyo.inequality(P_min, m.P_minus[parent, vert_pow, vert_volt], P_max)

    m.parent_power_constraint2 = pyo.Constraint(m.children, m.i, m.j, rule=parent_power_constraint_rule2)

    # Constant voltage assumption
    def voltage_constr_rule(m, n, vert_pow, vert_volt):
        return m.V[n, vert_pow, vert_volt] == m.V_P[vert_volt]

    m.voltageConstr = pyo.Constraint(m.Nodes, m.i, m.j, rule=voltage_constr_rule)

    def children_voltage_rule(m, children, vert_pow, vert_volt):
        return pyo.inequality(V_min, m.V[children, vert_pow, vert_volt], V_max)

    m.children_voltage = pyo.Constraint(m.children, m.i, m.j, rule=children_voltage_rule)

    m.aux = pyo.Var(m.children, domain=pyo.Reals)

    def aux_constraint_rule(m, n):
        return m.aux[n] == m.P_C_set[n, 0] - m.P_C_set[n, 1]

    m.aux_constraint = pyo.Constraint(m.children, rule=aux_constraint_rule)

    """# Auxiliary variables for the L1 norm of P_C_set
    m.abs_P_C_set = pyo.Var(m.children, domain=pyo.NonNegativeReals)

    # Constraints to linearize the L1 norm of P_C_set
    def abs_P_C_set_pos_rule(m, n):
        return m.abs_P_C_set[n] >= m.aux[n]
    m.abs_P_C_set_pos = pyo.Constraint(m.children, rule=abs_P_C_set_pos_rule)

    def abs_P_C_set_neg_rule(m, n):
        return m.abs_P_C_set[n] >= -m.aux[n]
    m.abs_P_C_set_neg = pyo.Constraint(m.children, rule=abs_P_C_set_neg_rule)"""

    # -------------------------
    # Objectif
    # -------------------------
    # Define alpha as a parameter of the model
    m.alpha = pyo.Param(initialize=1)

    def objective_rule(m):
        return sum(m.aux[n] for n in m.children) - alpha * m.O

    m.objective = pyo.Objective(rule=objective_rule, sense=pyo.maximize)

    # -------------------------
    # Résolution
    # -------------------------
    # Create an environment with your WLS license
    params = {
        "WLSACCESSID": '295bde64-ffb2-46ce-92c9-af4e12ace58f',
        "WLSSECRET": '2dc9e249-7d48-4e46-a099-71c52d5d7247',
        "LICENSEID": 2689995
    }
    env = gp.Env(params=params)
    solver = pyo.SolverFactory('gurobi')

    # Solve the model
    results = solver.solve(m, tee=True)

    # Print the results
    print(results)


if __name__ == "__main__":
    optim_problem("Case_14.txt")