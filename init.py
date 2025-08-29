"""
Point d’entrée unique du projet.
Il suffit de choisir :
    • le fichier IEEE (.txt)
    • les nœuds opérationnels
    • les parents
    • les enfants
Et de choisir les options de plot (pour alpha et beta)

puis de lancer :  init.py
"""

from core.check_requirements import check_packages
from core.optimization import optim_problem
from viz.plot_alloc_alpha import plot_alloc_alpha
from viz.plot_alloc_beta import plot_alloc_beta
from viz.plot_network import plot_network
from viz.plot_powerflow import plot_power_flow

# ---- Paramétrage utilisateur ----
TEST_CASE = "Data/Networks/example_multivoltage_adapted.py"
OPERATIONAL_NODES = [0, 1, 2, 3, 4, 5]  # [] => OPF ; sinon => DOE
PARENT_NODES = [0]
CHILDREN_NODES = [1, 2, 3, 4, 5]
# Parameters of the objective function
ALPHA = 2
BETA = 1

# Optional sweep of alpha to visualise its impact on the optimisation.
# Set ``PLOT_ALPHA`` to ``True`` to launch :func:`plot_alloc_alpha` with the
# following bounds and step.
PLOT_ALPHA = False
ALPHA_MIN = 0.0
ALPHA_MAX = 10.0
ALPHA_STEP = 1

# Optional sweep of beta to visualise its impact on the optimisation.
# Set ``PLOT_BETA`` to ``True`` to launch :func:`plot_alloc_beta` with the
# following bounds and step.
PLOT_BETA = False
BETA_MIN = 1.0
BETA_MAX = 4.0
BETA_STEP = 0.1
# ---------------------------------

CHECK_REQ = False
if CHECK_REQ:
    check_packages()

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
    )

res = optim_problem(
    test_case=TEST_CASE,
    operational_nodes=OPERATIONAL_NODES,
    parent_nodes=PARENT_NODES,
    children_nodes=CHILDREN_NODES,
    alpha=ALPHA,
    beta=BETA,
)

# Always display the complete graph
plot_network(res["full_graph"])

# Display power flows for available models
if "full" in res:
    plot_power_flow(res["full"]["model"], res["full"]["graph"], 0, 0)
if "operational" in res:
    plot_power_flow(res["operational"]["model"], res["operational"]["graph"], 0, 0)


