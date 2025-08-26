import pyomo.environ as pyo


def apply(m, G):
    """Apply standard OPF constraints and objective."""

    # 1) curtailment = P - E
    def curtailment_def_rule(m, n, vert_pow, vert_volt):
        return m.curt[n, vert_pow, vert_volt] == m.P[n] - m.E[n, vert_pow, vert_volt]
    m.curt_def = pyo.Constraint(m.Nodes, m.i, m.j, rule=curtailment_def_rule)

    # 2) |E| via z
    def abs_E_pos_rule(m, n, vert_pow, vert_volt):
        return m.z[n, vert_pow, vert_volt] >= m.curt[n, vert_pow, vert_volt]
    m.abs_E_pos = pyo.Constraint(m.Nodes, m.i, m.j, rule=abs_E_pos_rule)

    def abs_E_neg_rule(m, n, vert_pow, vert_volt):
        return m.z[n, vert_pow, vert_volt] >= -m.curt[n, vert_pow, vert_volt]
    m.abs_E_neg = pyo.Constraint(m.Nodes, m.i, m.j, rule=abs_E_neg_rule)

    # 3) somme(z) <= O
    def upper_bound_rule(m, vert_pow, vert_volt):
        return sum(m.z[n, vert_pow, vert_volt] for n in m.Nodes) <= m.O
    m.upper_bound = pyo.Constraint(m.i, m.j, rule=upper_bound_rule)

    # 4) bornes de courant (per-unit déjà)
    def current_bounds_rule(m, u, v, vert_pow, vert_volt):
        return pyo.inequality(m.I_min[u, v], m.I[u, v, vert_pow, vert_volt], m.I_max[u, v])
    m.CurrentBounds = pyo.Constraint(m.Lines, m.i, m.j, rule=current_bounds_rule)

    # 5) bornes d’angle (utilise m.theta_min/m.theta_max présents dans l’env)
    def phase_constr_rule(m, n, vert_pow, vert_volt):
        return pyo.inequality(m.theta_min, m.theta[n, vert_pow, vert_volt], m.theta_max)
    m.phaseConstr = pyo.Constraint(m.Nodes, m.i, m.j, rule=phase_constr_rule)

    # 6) DC power flow (ignorer les transfos: b_pu=None)
    def dc_power_flow_rule(m, u, v, vert_pow, vert_volt):
        if G[u][v].get('b_pu') is None:
            return pyo.Constraint.Skip
        return m.F[u, v, vert_pow, vert_volt] == m.V_P[vert_volt]**2 * (
            G[u][v]['b_pu'] * (m.theta[u, vert_pow, vert_volt] - m.theta[v, vert_pow, vert_volt])
        )
    m.DCFlow = pyo.Constraint(m.Lines, m.i, m.j, rule=dc_power_flow_rule)

    # 7) définition du courant : P_pu = V_pu * I_pu → I*V = F (cohérent avec constraints.py)
    def current_def_rule(m, u, v, vert_pow, vert_volt):
        return m.I[u, v, vert_pow, vert_volt] * m.V_P[vert_volt] == m.F[u, v, vert_pow, vert_volt]
    m.current_def = pyo.Constraint(m.Lines, m.i, m.j, rule=current_def_rule)

    # 8) bilan de puissance au nœud
    def power_balance_rule(m, n, vert_pow, vert_volt):
        expr = sum(
            (m.F[i, j, vert_pow, vert_volt] if j == n else 0)
          - (m.F[i, j, vert_pow, vert_volt] if i == n else 0)
          for (i, j) in m.Lines
        )
        if n in m.parents:
            return expr == m.E[n, vert_pow, vert_volt] - m.P_plus[n, vert_pow, vert_volt]
        elif n in m.children:
            # côté OPF de base, pas de P_minus imposé → garder E
            return expr == m.E[n, vert_pow, vert_volt]
        else:
            return expr == m.E[n, vert_pow, vert_volt]
    m.power_balance = pyo.Constraint(m.Nodes, m.i, m.j, rule=power_balance_rule)

    # 9) borne parent (per-unit)
    def parent_power_constraint_rule(m, parent, vert_pow, vert_volt):
        return pyo.inequality(m.P_min, m.P_plus[parent, vert_pow, vert_volt], m.P_max)
    m.parent_power_constraint = pyo.Constraint(m.parents, m.i, m.j, rule=parent_power_constraint_rule)

    # 10) tension constante locale
    def voltage_constr_rule(m, n, vert_pow, vert_volt):
        return m.V[n, vert_pow, vert_volt] == m.V_P[vert_volt]
    m.voltageConstr = pyo.Constraint(m.Nodes, m.i, m.j, rule=voltage_constr_rule)

    # ---- Objectif OPF ----
    def objective_rule_opf(m):
        return m.alpha * m.O
    m.objective_opf = pyo.Objective(rule=objective_rule_opf, sense=pyo.minimize)
