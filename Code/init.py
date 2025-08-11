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

# ---- Paramétrage utilisateur ----
TEST_CASE = "test_network.py"           # Chemin de votre fichier IEEE
OPERATIONAL_NODES = [0,1,2,11,12]    # Nœuds conservés dans le sous-réseau
PARENT_NODES      = [0]             # Injectent la puissance (P_plus)
CHILDREN_NODES    = [1,2]       # Absorbent la puissance (P_minus)
# ---------------------------------

install_missing_packages()      # requirements.txt auto-install
optim_problem(
    test_case=TEST_CASE,
    operational_nodes=OPERATIONAL_NODES,
    parent_nodes=PARENT_NODES,
    children_nodes=CHILDREN_NODES
)