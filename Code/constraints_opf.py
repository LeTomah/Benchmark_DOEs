import pyomo.environ as pyo

def constraints(m, G):
    def curtailment_def_rule(m, u, vert_pow, vert_volt):
        return m.curt[u, vert_pow, vert_volt] == m.P[u] - m.E[u, vert_pow, vert_volt]
    m.curt_def = pyo.Constraint(m.Nodes, m.i, m.j, rule=curtailment_def_rule)

    def abs_E_pos_rule(m, u, vert_pow, vert_volt):
        return m.z[u, vert_pow, vert_volt] >= m.curt[u, vert_pow, vert_volt]
    m.abs_E_pos = pyo.Constraint(m.Nodes, m.i, m.j, rule=abs_E_pos_rule)

    def abs_E_neg_rule(m, u, vert_pow, vert_volt):
        return m.z[u, vert_pow, vert_volt] >= -m.curt[u, vert_pow, vert_volt]
    m.abs_E_neg = pyo.Constraint(m.Nodes, m.i, m.j, rule=abs_E_neg_rule)

    def upper_bound_rule(m, vert_pow, vert_volt):
        return sum(m.z[n, vert_pow, vert_volt] for n in m.Nodes) <= m.O
    m.upper_bound = pyo.Constraint(m.i, m.j, rule=upper_bound_rule)

    def current_bounds_rule(m, u, v, vert_pow, vert_volt):
        return pyo.inequality(m.I_min[u, v], m.I[u, v, vert_pow, vert_volt], m.I_max[u, v])
    m.CurrentBounds = pyo.Constraint(m.Lines, m.i, m.j, rule=current_bounds_rule)

    def phase_constr_rule(m, u, vert_pow, vert_volt):
        return pyo.inequality(m.theta_min, m.theta[u, vert_pow, vert_volt], m.theta_max)
    m.phaseConstr = pyo.Constraint(m.Nodes, m.i, m.j, rule=phase_constr_rule)

    def dc_power_flow_rule(m, u, v, vert_pow, vert_volt):
        if G[u][v]['b_pu'] is None:
            return pyo.Constraint.Skip
        else:
            return m.F[u, v, vert_pow, vert_volt] == m.V_P[vert_volt] ** 2 * (
                G[u][v]['b_pu'] * (m.theta[u, vert_pow, vert_volt] - m.theta[v, vert_pow, vert_volt]))
    m.DCFlow = pyo.Constraint(m.Lines, m.i, m.j, rule=dc_power_flow_rule)

    def current_def_rule(m, u, v, vert_pow, vert_volt):
        return m.I[u, v, vert_pow, vert_volt] * m.V_P[vert_volt] == m.F[u, v, vert_pow, vert_volt]
    m.current_def = pyo.Constraint(m.Lines, m.i, m.j, rule=current_def_rule)

    def power_balance_rule(m, n, vert_pow, vert_volt):
        expr = sum(
            (m.F[i, j, vert_pow, vert_volt] if j == n else 0)
            - (m.F[i, j, vert_pow, vert_volt] if i == n else 0)
            for (i, j) in m.Lines)
        if n in m.parents:
            return expr == m.E[n, vert_pow, vert_volt] - m.P_plus[n, vert_pow, vert_volt]
        if n in m.children:
            return expr == m.E[n, vert_pow, vert_volt] + m.P_minus[n, vert_pow, vert_volt]
        else:
            return expr == m.E[n, vert_pow, vert_volt]
    m.power_balance = pyo.Constraint(m.Nodes, m.i, m.j, rule=power_balance_rule)

    def parent_power_constraint_rule(m, parent, vert_pow, vert_volt):
        return pyo.inequality(m.P_min, m.P_plus[parent, vert_pow, vert_volt], m.P_max)
    m.parent_power_constraint = pyo.Constraint(m.parents, m.i, m.j, rule=parent_power_constraint_rule)

    def voltage_constr_rule(m, u, vert_pow, vert_volt):
        return m.V[u, vert_pow, vert_volt] == m.V_P[vert_volt]
    m.voltageConstr = pyo.Constraint(m.Nodes, m.i, m.j, rule=voltage_constr_rule)

    def objective_rule(m):
        return m.alpha * m.O
    m.objective = pyo.Objective(rule=objective_rule, sense=pyo.minimize)
