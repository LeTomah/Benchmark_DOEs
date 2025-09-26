"""AC power flow constraints based on a simplified DistFlow model."""

from __future__ import annotations

from typing import Any
import pyomo.environ as pyo


def build(m: pyo.ConcreteModel, G: Any) -> None:
    """Add AC power flow variables and constraints to ``model``.

    The implementation follows the same pattern as the DC formulation but
    relies on a DistFlow representation.  For each oriented line ``e = (n, j)``
    active and reactive power flows are represented by ``F[e]`` and ``G[e]``
    respectively.  Squared voltage magnitudes ``V_sqr`` and squared currents
    ``I_sqr`` are associated with buses and lines.  The following equations are
    enforced for every node ``n`` and line ``e`` of the operational network::

        E_n = sum(F_mn) - sum(F_nj + R_e * I_sqr_e) + P_plus_n - P_minus_n
        H_n = sum(G_mn) - sum(G_nj + X_e * I_sqr_e) + Q_plus_n - Q_minus_n
        V_sqr_n - V_sqr_j = 2*(R_e*F_e + X_e*G_e) + Z_e**2 * I_sqr_e
        V_sqr_n * I_sqr_e >= F_e**2 + G_e**2

    Parameters
    ----------
    m:
        Pyomo model to augment.
    G:
        NetworkX graph describing the electrical network.  Edge attributes
        ``R`` and ``X`` (per-unit resistance and reactance) are optional.  When
        absent they default to zero; the squared impedance ``Z_e**2`` is
        computed as ``R**2 + X**2``.
    """

    nodes = list(G.nodes)
    lines = list(G.edges)

    m.Nodes = pyo.Set(initialize=nodes)
    m.Lines = pyo.Set(initialize=lines, dimen=2)

    # Line parameters: resistance R, reactance X and squared impedance Z2
    m.R = pyo.Param(
        m.Lines,
        initialize={(u, v): float(G[u][v].get("R", 0.0)) for (u, v) in lines},
        mutable=True,
    )
    m.X = pyo.Param(
        m.Lines,
        initialize={(u, v): float(G[u][v].get("X", 0.0)) for (u, v) in lines},
        mutable=True,
    )
    m.Z2 = pyo.Param(
        m.Lines,
        initialize={
            (u, v): float(G[u][v].get("R", 0.0)) ** 2
                    + float(G[u][v].get("X", 0.0)) ** 2
            for (u, v) in lines
        },
        mutable=True,
    )

    # # Variables for power flows and squared quantities
    # m.F = pyo.Var(m.Lines, domain=pyo.Reals)
    # m.G = pyo.Var(m.Lines, domain=pyo.Reals)
    # m.I_sqr = pyo.Var(m.Lines, domain=pyo.NonNegativeReals)
    # m.V_sqr = pyo.Var(m.Nodes, domain=pyo.NonNegativeReals)
    #
    # # Nodal injections and exchanges with outside of the operational graph
    # m.E = pyo.Var(m.Nodes, domain=pyo.Reals)
    # m.H = pyo.Var(m.Nodes, domain=pyo.Reals)
    # m.P_plus = pyo.Var(m.Nodes, domain=pyo.Reals)
    # m.P_minus = pyo.Var(m.Nodes, domain=pyo.Reals)
    # m.Q_plus = pyo.Var(m.Nodes, domain=pyo.Reals)
    # m.Q_minus = pyo.Var(m.Nodes, domain=pyo.Reals)

    def active_balance_rule(m, n):
        incoming = sum(m.F[i, j] for (i, j) in m.Lines if j == n)
        outgoing = sum(m.F[n, j] + m.R[n, j] * m.I_sqr[n, j] for (n2, j) in m.Lines if n2 == n)
        return m.E[n] == incoming - outgoing + m.P_plus[n] - m.P_minus[n]

    m.active_balance = pyo.Constraint(m.Nodes, rule=active_balance_rule)

    def reactive_balance_rule(m, n):
        incoming = sum(m.G[i, j] for (i, j) in m.Lines if j == n)
        outgoing = sum(m.G[n, j] + m.X[n, j] * m.I_sqr[n, j] for (n2, j) in m.Lines if n2 == n)
        return m.H[n] == incoming - outgoing + m.Q_plus[n] - m.Q_minus[n]

    m.reactive_balance = pyo.Constraint(m.Nodes, rule=reactive_balance_rule)

    def voltage_drop_rule(m, n, j):
        return (
            m.V_sqr[n] - m.V_sqr[j]
            == 2 * (m.R[n, j] * m.F[n, j] + m.X[n, j] * m.G[n, j])
            + m.Z2[n, j] * m.I_sqr[n, j]
        )

    m.voltage_drop = pyo.Constraint(m.Lines, rule=voltage_drop_rule)

    def current_voltage_rule(m, n, j):
        return m.V_sqr[n] * m.I_sqr[n, j] >= m.F[n, j] ** 2 + m.G[n, j] ** 2

    m.current_voltage = pyo.Constraint(m.Lines, rule=current_voltage_rule)

    def add_curtailment_abs(m):
        """Define curtailment ``curt`` and its absolute value ``z``.

        Also enforce ``sum(z) <= curtailment_budget`` for each vertex pair.
        """

        def curt_def_rule(m, u, vp, vv):
            return m.curt[u, vp, vv] == m.P[u] - m.E[u, vp, vv]

        m.curt_def = pyo.Constraint(m.Nodes, m.VertP, m.VertV, rule=curt_def_rule)

        def abs_pos_rule(m, u, vp, vv):
            return m.z[u, vp, vv] >= m.curt[u, vp, vv]

        m.abs_E_pos = pyo.Constraint(m.Nodes, m.VertP, m.VertV, rule=abs_pos_rule)

        def abs_neg_rule(m, u, vp, vv):
            return m.z[u, vp, vv] >= -m.curt[u, vp, vv]

        m.abs_E_neg = pyo.Constraint(m.Nodes, m.VertP, m.VertV, rule=abs_neg_rule)

        def upper_bound_rule(m, vp, vv):
            return sum(m.z[u, vp, vv] for u in m.Nodes) <= m.curtailment_budget

        m.upper_bound = pyo.Constraint(m.VertP, m.VertV, rule=upper_bound_rule)