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
    result = compute(
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

    # Ajout : affichage des principaux résultats de l'optimisation.
    print("=== Résumé de l'optimisation DOE ===")
    print(f"Statut: {result.get('status')}")
    if result.get("objective_value") is not None:
        print(f"Valeur de l'objectif: {result['objective_value']}")

    envelopes = result.get("envelopes") or {}
    if envelopes:
        print("\nBornes des enveloppes (P_min, P_max) par nœud:")
        for node, bounds in envelopes.items():
            print(f"  Nœud {node}: {bounds}")
    else:
        print("\nAucune enveloppe calculée.")

    curtailment_report = result.get("curtailment_report") or {}
    if curtailment_report:
        print("\nValeurs de curtailment:")
        for node, value in curtailment_report.items():
            print(f"  Nœud {node}: {value}")
    else:
        print("\nAucun curtailment détecté.")

    diagnostics = result.get("diagnostics") or {}
    if diagnostics:
        print("\nDiagnostics complémentaires:")
        for key, value in diagnostics.items():
            print(f"  {key}: {value}")
