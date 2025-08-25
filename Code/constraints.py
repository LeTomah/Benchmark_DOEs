import pyomo.environ as pyo

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
    m.worst_case = pyo.Constraint(m.children,
                                  m.i,
                                  m.j,
                                  rule=worst_case_children)

    def curtailment_def_rule(m, u, vert_pow, vert_volt):
        return m.curt[u, vert_pow, vert_volt] == m.P[u] - m.E[u, vert_pow, vert_volt]
    m.curt_def = pyo.Constraint(m.Nodes,
                                m.i,
                                m.j,
                                rule=curtailment_def_rule)

    # Constraints to define the absolute value (already defined for per-unit E)
    def abs_E_pos_rule(m, u, vert_pow, vert_volt):
        return m.z[u, vert_pow, vert_volt] >= m.curt[u, vert_pow, vert_volt]
    m.abs_E_pos = pyo.Constraint(m.Nodes,
                                 m.i,
                                 m.j,
                                 rule=abs_E_pos_rule)

    def abs_E_neg_rule(m, u, vert_pow, vert_volt):
        return m.z[u, vert_pow, vert_volt] >= -m.curt[u, vert_pow, vert_volt]
    m.abs_E_neg = pyo.Constraint(m.Nodes,
                                 m.i,
                                 m.j,
                                 rule=abs_E_neg_rule)

    def upper_bound_rule(m, vert_pow, vert_volt):
        # m.z is per-unit, m.O is per-unit
        return sum(m.z[n, vert_pow, vert_volt] for n in m.Nodes) <= m.O
    m.upper_bound = pyo.Constraint(m.i,
                                   m.j,
                                   rule=upper_bound_rule)

    # Current magnitude constraint (I_min, I_max are assumed per-unit)
    def current_bounds_rule(m, u, v, vert_pow, vert_volt):
        # m.I is per-unit current
        return pyo.inequality(m.I_min[u, v], m.I[u, v, vert_pow, vert_volt], m.I_max[u, v])
    m.CurrentBounds = pyo.Constraint(m.Lines,
                                     m.i,
                                     m.j,
                                     rule=current_bounds_rule)

    def phase_constr_rule(m, u, vert_pow, vert_volt):
        return pyo.inequality(m.theta_min, m.theta[u, vert_pow, vert_volt], m.theta_max)
    m.phaseConstr = pyo.Constraint(m.Nodes,
                                   m.i,
                                   m.j,
                                   rule=phase_constr_rule)

    def dc_power_flow_rule(m, u, v, vert_pow, vert_volt):
        if G[u][v]['b_pu']==None:
            return pyo.Constraint.Skip #Ne prend pas en compte les transfos
        else:
            return m.F[u, v, vert_pow, vert_volt] == m.V_P[vert_volt] ** 2 * (G[u][v]['b_pu'] * (
                    m.theta[u, vert_pow, vert_volt] - m.theta[v, vert_pow, vert_volt]))
    m.DCFlow = pyo.Constraint(m.Lines,
                              m.i,
                              m.j,
                              rule=dc_power_flow_rule)

    def current_def_rule(m, u, v, vert_pow, vert_volt):
        # This constraint relates per-unit current, per-unit voltage, and per-unit power flow.
        # In per-unit, P_pu = V_pu * I_pu. This is correct.
        return m.I[u, v, vert_pow, vert_volt] * m.V_P[vert_volt] == m.F[u, v, vert_pow, vert_volt]
    m.current_def = pyo.Constraint(m.Lines,
                                   m.i,
                                   m.j,
                                   rule=current_def_rule)

    def power_balance_rule(m, n, vert_pow, vert_volt):
        # Compute net flow into node n by summing over all lines (i,j) in m.Lines
        expr = sum(
            (m.F[i, j, vert_pow, vert_volt] if j == n else 0)
            - (m.F[i, j, vert_pow, vert_volt] if i == n else 0)
            for (i, j) in m.Lines)
        # If n is a parent node, subtract P_plus;
        # If n is a child node, add P_minus;
        # Otherwise use only E[n]
        if n in m.parents:
            return expr == m.E[n, vert_pow, vert_volt] - m.P_plus[n, vert_pow, vert_volt]
        if n in m.children:
            return expr == m.E[n, vert_pow, vert_volt] + m.P_minus[n, vert_pow, vert_volt]
        else:
            return expr == m.E[n, vert_pow, vert_volt]
    m.power_balance = pyo.Constraint(m.Nodes,
                                     m.i,
                                     m.j,
                                     rule=power_balance_rule)

    def parent_power_constraint_rule(m, parent, vert_pow, vert_volt):
        # m.P_plus is per-unit power entering the operational graph
        return pyo.inequality(m.P_min, m.P_plus[parent, vert_pow, vert_volt], m.P_max)
    m.parent_power_constraint = pyo.Constraint(m.parents,
                                               m.i,
                                               m.j,
                                               rule=parent_power_constraint_rule)

    # Constant voltage assumption
    def voltage_constr_rule(m, u, vert_pow, vert_volt):
        return m.V[u, vert_pow, vert_volt] == m.V_P[vert_volt]
    m.voltageConstr = pyo.Constraint(m.Nodes,
                                     m.i,
                                     m.j,
                                     rule=voltage_constr_rule)

    def children_voltage_rule(m, children, vert_pow, vert_volt):
        return pyo.inequality(m.V_min, m.V[children, vert_pow, vert_volt], m.V_max)
    m.children_voltage = pyo.Constraint(m.children,
                                        m.i,
                                        m.j,
                                        rule=children_voltage_rule)

    def aux_constraint_rule(m, u):
        return m.aux[u] == m.P_C_set[u, 0] - m.P_C_set[u, 1]
    m.aux_constraint = pyo.Constraint(m.children,
                                      rule=aux_constraint_rule)

    def tot_P_rule(m):
        return m.tot_P == sum(m.aux[u] for u in m.children)
    m.tot_P_constraint = pyo.Constraint(rule=tot_P_rule)

    def diff_DSO_rule(m, u):
        return - m.diff_DSO[u] <= (m.P_C_set[u, 0] + m.P_C_set[u, 1]) / 2 - m.info_DSO_param[u]
    m.diff_DSO_constraint = pyo.Constraint(m.children,
                                           rule=diff_DSO_rule)

    def diff_bis_dso_rule(m, u):
        return (m.P_C_set[u, 0] + m.P_C_set[u, 1]) / 2 - m.info_DSO_param[u] <= m.diff_DSO[u]
    m.diff_bis_dso_constraint = pyo.Constraint(m.children,
                                               rule=diff_bis_dso_rule)

    m.tot_diff_DSO = pyo.Var(domain=pyo.Reals)
    def tot_diff_dso_rule(m):
        return m.tot_diff_DSO == sum(m.diff_DSO[u] for u in m.children)
    m.tot_diff_dso_constraint = pyo.Constraint(rule=tot_diff_dso_rule)

    # Constraint for positive P: upper bound
    def net_power_upper_rule(m, n, vert_pow, vert_volt):
        return m.E[n, vert_pow, vert_volt] <= m.P[n]
    m.net_power_upper = pyo.Constraint(m.PositiveNodes, m.i, m.j, rule=net_power_upper_rule)

    def sign_E_upper_rule(m, n, vert_pow, vert_volt):
        return m.E[n, vert_pow, vert_volt] >= 0
    m.sign_E_upper = pyo.Constraint(m.PositiveNodes, m.i, m.j, rule=sign_E_upper_rule)

    # Constraint for negative P: lower bound
    def net_power_lower_rule(m, n, vert_pow, vert_volt):
        return m.E[n, vert_pow, vert_volt] >= m.P[n]
    m.net_power_lower = pyo.Constraint(m.NegativeNodes, m.i, m.j, rule=net_power_lower_rule)

    def sign_E_lower_rule(m, n, vert_pow, vert_volt):
        return m.E[n, vert_pow, vert_volt] <= 0
    m.sign_E_lower = pyo.Constraint(m.NegativeNodes, m.i, m.j, rule=sign_E_lower_rule)

    # -------------------------
    # Objective (DOE case)
    # -------------------------
    def objective_rule_doe(m):
        return m.tot_P - m.alpha * m.O - m.beta * m.tot_diff_DSO
    m.objective_doe = pyo.Objective(rule=objective_rule_doe, sense=pyo.maximize)