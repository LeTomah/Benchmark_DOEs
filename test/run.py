"""Simple DOE.compute launcher.

P and Q values are expressed in per-unit (p.u.) and `network` refers to an
existing network definition file.
"""

from doe.compute import compute

P_min = -1.0
P_max = 1.0
Q_min = -1.0
Q_max = 1.0
alpha = 1
beta = 1
powerflow_mode = "dc"
network = "example_multivoltage_adapted"
objective = "global_sum"
operational_nodes = (0, 1, 2, 3, 4, 5)
parent_nodes = (0,)
children_nodes = (2, 3, 4)


if __name__ == "__main__":
    compute(
        P_min=P_min,
        P_max=P_max,
        Q_min=Q_min,
        Q_max=Q_max,
        alpha=alpha,
        beta=beta,
        powerflow_mode=powerflow_mode,
        network=network,
        objective=objective,
        operational_nodes=operational_nodes,
        parent_nodes=parent_nodes,
        children_nodes=children_nodes,
    )