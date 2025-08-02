def optim_problem():
    
    import digraph
    import pyo_environment
    import numpy as np
    import pyomo.environ as pyo
    import gurobipy as gp
    
    G=digraph.create_digraph()
    m, PTDF, node_to_idx, edge_to_idx = pyo_environment.create_pyo_environ()

# -------------------------    
#Constraints
# -------------------------

#Constant definition
    V_min = 0.8
    V_max = 1.2

    I_min = 0.8
    I_max = 1.2

    theta_min = -np.pi
    theta_max = np.pi


    m.alpha =1

# Auxiliary variable for the absolute value of E
    m.abs_E = pyo.Var(m.Nodes, m.i, m.j, domain=pyo.NonNegativeReals)

# Constraints to define the absolute value
    def abs_E_pos_rule(m, n, vert_pow, vert_volt):
        return m.abs_E[n, vert_pow, vert_volt] >= m.E[n, vert_pow, vert_volt]
    m.abs_E_pos = pyo.Constraint(m.Nodes, m.i, m.j, rule=abs_E_pos_rule)

    def abs_E_neg_rule(m, n, vert_pow, vert_volt):
        return m.abs_E[n, vert_pow, vert_volt] >= -m.E[n, vert_pow, vert_volt]
    m.abs_E_neg = pyo.Constraint(m.Nodes, m.i, m.j, rule=abs_E_neg_rule)


# Current magnitude constraint
    def voltage_bounds_rule(m, i, j, vert_pow, vert_volt):
        return pyo.inequality(I_min, m.I[i,j, vert_pow, vert_volt], I_max)
    m.VoltageBounds = pyo.Constraint(m.Lines, m.i, m.j, rule=voltage_bounds_rule)

#Constant voltage assumption
    def voltage_constr_rule(m, n, vert_pow, vert_volt):
        return m.V[n, vert_pow, vert_volt] == m.V_P[vert_volt]
    m.voltageConstr = pyo.Constraint(m.Nodes, m.i, m.j, rule=voltage_constr_rule)

# Neighbor mapping: find all neighbors for each node n
    def neighbors_init(m, n):
        return [neighbor for (i, neighbor) in m.Lines if i == n]
    m.Neighbors = pyo.Set(m.Nodes, initialize=neighbors_init)


    def En_constraint_rule(m, n, vert_pow, vert_volt):
        return m.E[n, vert_pow, vert_volt] == m.V_P[vert_volt]**2 * sum(
            G[n][neighbor].get('b', 0.0) * (m.theta[neighbor, vert_pow, vert_volt] - m.theta[n, vert_pow, vert_volt]) for neighbor in m.Neighbors[n]
            )
    m.EnConstraint = pyo.Constraint(m.Nodes, m.i, m.j, rule=En_constraint_rule)

    def PTDF_rule(m, u, v, vert_pow, vert_volt):
        line_index = edge_to_idx[(u, v)]
        return m.F[u,v, vert_pow, vert_volt] == sum(PTDF[line_index, node_to_idx[n]] * m.E[n, vert_pow, vert_volt] for n in m.Nodes)
    m.PTDF = pyo.Constraint(m.Lines, m.i, m.j, rule=PTDF_rule)

    def upper_bound_rule(m, vert_pow, vert_volt):
        return sum(m.abs_E[n, vert_pow, vert_volt] for n in m.Nodes) <= m.O

    m.upper_bound = pyo.Constraint(m.i, m.j, rule=upper_bound_rule)

    def phase_constr_rule(m,n, vert_pow, vert_volt):
        return pyo.inequality(theta_min, m.theta[n, vert_pow, vert_volt], theta_max)

    m.phaseConstr = pyo.Constraint(m.Nodes, m.i, m.j, rule=phase_constr_rule)

    def children_voltage_rule(m, children, vert_pow, vert_volt):
        return pyo.inequality(V_min, m.V[children, vert_pow, vert_volt], V_max)

    m.children_voltage = pyo.Constraint(m.children, m.i, m.j, rule=children_voltage_rule)


    def current_def_rule(m, n, i, j, vert_pow, vert_volt):
        return m.I[i,j, vert_pow, vert_volt] * m.V[n, vert_pow, vert_volt] == m.F[i,j, vert_pow, vert_volt]

    m.current_def = pyo.Constraint(m.Nodes, m.Lines, m.i, m.j, rule=current_def_rule)

    def balance_rule(m, vert_pow, vert_volt):
        return sum(m.P[n] - m.E[n, vert_pow, vert_volt] for n in m.Nodes) == sum(m.P_plus[parent, vert_pow, vert_volt] for parent in m.parents) - sum(m.P_minus[child, vert_pow, vert_volt] for child in m.children)

    m.balance = pyo.Constraint(m.i, m.j, rule=balance_rule)


    """def children_power(m, n, vert_pow, vert_volt):
        return pyo.inequality(m.P_C_min[n, vert_pow, vert_volt], m.P_minus[n, vert_pow, vert_volt], m.P_C_max[n, vert_pow, vert_volt])
    m.children_power = pyo.Constraint(m.children, m.i, m.j, rule=children_power)"""

    def children_power_lower_rule(m, n, vert_pow, vert_volt):
        return m.P_C_min[n, vert_pow, vert_volt] <= m.P_minus[n, vert_pow, vert_volt]
    m.children_power_lower = pyo.Constraint(m.children, m.i, m.j, rule=children_power_lower_rule)

    def children_power_upper_rule(m, n, vert_pow, vert_volt):
        return m.P_minus[n, vert_pow, vert_volt] <= m.P_C_max[n, vert_pow, vert_volt]
    m.children_power_upper = pyo.Constraint(m.children, m.i, m.j, rule=children_power_upper_rule)


# -------------------------
# Objectif
# -------------------------
# Define alpha as a parameter of the model
    m.alpha = pyo.Param(initialize=1)

    def objective_rule(m):
        somme = 0
        for child in m.children:  # Iterate over the elements in m.children
            for i in m.i:
                for j in m.j:
                    somme += m.P_C_min[child, i, j] + m.P_C_max[child, i, j] # Use 'child' as the index

        return somme - m.alpha * m.O

    m.Objective = pyo.Objective(rule=objective_rule, sense=pyo.maximize)
    
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
    
optim_problem()
