# DOE Library

Cette bibliothèque propose une implémentation modulaire et minimale pour calculer des *Distribution Operation Envelopes* (DOE) sur des réseaux électriques modélisés avec [pandapower](https://pandapower.readthedocs.io/).

## Installation

1. Cloner le dépôt puis se placer à sa racine.
2. Créer un environnement virtuel Python 3.10 ou supérieur.
3. Installer les dépendances :
   ```bash
   pip install -r requirements.txt
   ```

Pour l'utilisation du solveur Gurobi via Pyomo, les variables d'environnement suivantes peuvent être définies :
`GUROBI_WLSACCESSID`, `GUROBI_WLSSECRET` et éventuellement `GUROBI_LICENSEID`.

## Structure du projet

- `doe/` : cœur de la bibliothèque
  - `compute.py` : point d'entrée principal avec `DOE.compute`
  - `constraints/`, `objectives/`, `solvers/`, `utils/` : modules Pyomo et utilitaires
- `data/networks/` : exemples de réseaux `pandapower`
- `viz/` : fonctions de visualisation basées sur `matplotlib`
- `test/` : tests automatiques `pytest`
- `docs/` : documentation et guides

## Utilisation rapide

```python
from doe import DOE
result = DOE.compute("modified_case_14", "dc", "global_sum", alpha=0.1, beta=0.2)
print(result["status"], result["objective_value"])
```

Le premier argument peut être soit le nom d'un module de réseau présent dans `data/networks`, soit un objet `pandapowerNet` déjà chargé :

```python
import pandapower.networks as pn
net = pn.case14()
DOE.compute(net, "dc", "global_sum", alpha=0.1, beta=0.2)
```

Options principales :
- `powerflow_mode` : actuellement `"dc"` est implémenté, `"ac"` est un placeholder.
- `objective` : `"global_sum"` (implémenté) ou `"fairness"` (placeholder).
- Pour `global_sum`, fournir les paramètres `alpha` et `beta`.

La fonction retourne un dictionnaire contenant l'état du solveur, la valeur de l'objectif et les enveloppes calculées.

## Visualisation

Les fonctions du dossier `viz/` permettent de représenter graphiquement le réseau ou les enveloppes calculées. Exemple :

```python
from viz.plot_DOE import plot_DOE
plot_DOE(result["envelopes"])
```

## Exécution des tests

Les tests unitaires se lancent avec :

```bash
pytest test
```

Ils vérifient l'intégration basique de la bibliothèque et le chargement des réseaux.

## Ressources complémentaires

- `docs/API_REFERENCE.md` : référence d'API
- `docs/EXTENDING.md` : guide pour étendre la bibliothèque
