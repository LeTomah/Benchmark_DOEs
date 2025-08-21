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
from plot_utils import plot_power_flow
import pandapower.networks as pn

# ---- Paramétrage utilisateur ----
TEST_CASE = pn.example_multivoltage()           # Chemin de votre fichier IEEE
OPERATIONAL_NODES = [4, 5, 9, 10, 11, 12]   # Nœuds conservés dans le sous-réseau
PARENT_NODES      = [4]             # Injectent la puissance (P_plus)
CHILDREN_NODES    = [9, 10, 11, 12]           # Absorbent la puissance (P_minus)
OPF_ONLY          = False           # Choix du modèle d'optimisation
# ---------------------------------

install_missing_packages()      # requirements.txt auto-install
res = optim_problem(
    test_case=TEST_CASE,
    operational_nodes=OPERATIONAL_NODES,
    parent_nodes=PARENT_NODES,
    children_nodes=CHILDREN_NODES,
    opf_only=OPF_ONLY)          # run the optimization

plot_power_flow(res["full"]["model"], res["full"]["graph"], 0, 1)
plot_power_flow(res["operational"]["model"], res["operational"]["graph"], 0, 1)