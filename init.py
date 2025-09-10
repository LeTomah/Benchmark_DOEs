"""Entry point of the project.

Configure the network and plotting options by editing the parameters below
before running ``init.py``.

Parameters
----------
TEST_CASE : str
    Path to the network description file (``.txt`` or ``.py``).
OPERATIONAL_NODES : list[int]
    Empty list runs an optimal power flow (OPF); otherwise runs a DOE on the
    specified nodes.
PARENT_NODES : list[int]
    Parent nodes that exchange power with the network.
CHILDREN_NODES : list[int]
    Children nodes connected to the parents.
ALPHA, BETA : float
    Coefficients of the objective function.
P_MIN, P_MAX : float
    Bounds for power exchanged at parent nodes.
PLOT_ALPHA : bool
    Enable an ``alpha`` sweep with bounds ``ALPHA_MIN``, ``ALPHA_MAX`` and step
    ``ALPHA_STEP``.
PLOT_BETA : bool
    Enable a ``beta`` sweep with bounds ``BETA_MIN``, ``BETA_MAX`` and step
    ``BETA_STEP``.
PLOT_NETWORK : bool
    Display the complete network graph.
PLOT_POWERFLOW_FULL : bool
    Display power flows for the full graph.
PLOT_POWERFLOW_OPERATIONAL : bool
    Display power flows for the operational subgraph.
PLOT_DOE : bool
    Display the DOE scatter plot.
CHECK_REQ : bool
    Check Python dependencies before running.
"""

from core.check_requirements import check_packages
from core.optimization import optim_problem
from viz.plot_alloc_alpha import plot_alloc_alpha
from viz.plot_alloc_beta import plot_alloc_beta
from viz.plot_network import plot_network
from viz.plot_powerflow import plot_power_flow

# ---- User configuration ----
CHECK_REQ = False
if CHECK_REQ:
    check_packages()

TEST_CASE = "Data/Networks/example_multivoltage_adapted.py"
OPERATIONAL_NODES = [11, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26]  # [] => OPF ; otherwise => DOE
PARENT_NODES = [11]
CHILDREN_NODES = [16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26]
# Parameters of the objective function
ALPHA = 2.05
BETA = 2.05
# Bounds for power exchanged at parent nodes
P_MIN = -0.28231
P_MAX = 0.27873

# Optional sweep of alpha to visualise its impact on the optimisation.
# Set ``PLOT_ALPHA`` to ``True`` to launch :func:`plot_alloc_alpha` with the
# following bounds and step.
PLOT_ALPHA = True
ALPHA_MIN = 0.1
ALPHA_MAX = 1
ALPHA_STEP = 0.1

# Optional sweep of beta to visualise its impact on the optimisation.
# Set ``PLOT_BETA`` to ``True`` to launch :func:`plot_alloc_beta` with the
# following bounds and step.
PLOT_BETA = False
BETA_MIN = 0.1
BETA_MAX = 2.5
BETA_STEP = 0.1

# Select which plots to display
PLOT_NETWORK = False
PLOT_POWERFLOW_FULL = False          #For OPF only
PLOT_POWERFLOW_OPERATIONAL = False   #For DOE only
PLOT_DOE = True
# ---------------------------------

# Optionally scan multiple ``alpha`` values and display the resulting metrics
# before running the main optimisation.
if PLOT_ALPHA:
    plot_alloc_alpha(
        test_case=TEST_CASE,
        operational_nodes=OPERATIONAL_NODES,
        parent_nodes=PARENT_NODES,
        children_nodes=CHILDREN_NODES,
        beta=BETA,
        alpha_min=ALPHA_MIN,
        alpha_max=ALPHA_MAX,
        alpha_step=ALPHA_STEP,
        P_min=P_MIN,
        P_max=P_MAX,
    )

if PLOT_BETA:
    plot_alloc_beta(
        test_case=TEST_CASE,
        operational_nodes=OPERATIONAL_NODES,
        parent_nodes=PARENT_NODES,
        children_nodes=CHILDREN_NODES,
        alpha=ALPHA,
        beta_min=BETA_MIN,
        beta_max=BETA_MAX,
        beta_step=BETA_STEP,
        P_min=P_MIN,
        P_max=P_MAX,
    )

res = optim_problem(
    test_case=TEST_CASE,
    operational_nodes=OPERATIONAL_NODES,
    parent_nodes=PARENT_NODES,
    children_nodes=CHILDREN_NODES,
    alpha=ALPHA,
    beta=BETA,
    P_min=P_MIN,
    P_max=P_MAX,
    plot_doe=PLOT_DOE,
)

# Optional display of the complete graph
if PLOT_NETWORK:
    plot_network(res["full_graph"])

# Display power flows for available models
if PLOT_POWERFLOW_FULL and "full" in res:
    plot_power_flow(res["full"]["model"], res["full"]["graph"], 0, 0)

if PLOT_POWERFLOW_OPERATIONAL and "operational" in res:
    plot_power_flow(res["operational"]["model"], res["operational"]["graph"], 0, 0)


