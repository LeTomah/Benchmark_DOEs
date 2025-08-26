"""
Point d’entrée unique du projet.
Il suffit de choisir :
    • le fichier IEEE (.txt)
    • les nœuds opérationnels
    • les parents
    • les enfants
Et de renseigner ses identifiants gurobi dans optimization.py (l.131->133)
puis de lancer :  init.py
"""
from check_requirements import install_missing_packages
from optimization import optim_problem
from plot_utils import plot_power_flow, plot_alloc_alpha, plot_network
import pandapower.networks as pn

# ---- Paramétrage utilisateur ----
TEST_CASE = "Data/Networks/example_multivoltage_adapted.py"
OPERATIONAL_NODES = [0, 1, 2, 3, 4, 5]            # [] => OPF ; sinon => DOE
PARENT_NODES      = [0]
CHILDREN_NODES    = [1, 2, 3, 4, 5]
# Parameters of the objective function
ALPHA = 1
BETA = 1

# Optional sweep of alpha to visualise its impact on the optimisation.
# Set ``PLOT_ALPHA`` to ``True`` to launch :func:`plot_alloc_alpha` with the
# following bounds and step.
PLOT_ALPHA = True
ALPHA_MIN = 0.0
ALPHA_MAX = 1.0
ALPHA_STEP = 0.1
# ---------------------------------

install_missing_packages()

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
    plot_power_flow(res["full"]["model"], res["full"]["graph"], 0, 1)
if "operational" in res:
    plot_power_flow(res["operational"]["model"], res["operational"]["graph"], 0, 1)
