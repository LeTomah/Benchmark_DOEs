# -*- coding: utf-8 -*-
"""
Réseau test simple 'modified_case_14' pour DOE :
- point de départ : pandapower.networks.case14()
- suppression des lignes (9,10) et (13,14) et du transfo (7,9)
- affectation de max_i_ka via un dictionnaire "tension -> courant max" (match exact uniquement)
- injections P (prod/cons) codées en dur sur quelques bus
"""

import pandapower as pp
import pandapower.networks as pn


def build() -> pp.pandapowerNet:
    # 1) Base réseau (IEEE-14 pandapower)
    net = pn.case14()

    # 2) Retrait de deux lignes et d’un transfo (indices de bus en 0-based)
    line_idx = net.line[
        ((net.line.from_bus == 8) & (net.line.to_bus == 9))   # ex (9,10)
        | ((net.line.from_bus == 12) & (net.line.to_bus == 13))  # ex (13,14)
    ].index
    trafo_idx = net.trafo[
        (net.trafo.hv_bus == 6) & (net.trafo.lv_bus == 8)  # ex (7,9)
    ].index

    if len(line_idx):
        pp.drop_lines(net, line_idx)
    if len(trafo_idx):
        pp.drop_trafos(net, trafo_idx)

    # 3) Courants max admissibles par palier de tension (match exact des tensions bus vn_kv)
    #    NB: si la tension d’une ligne n’est pas exactement une clé du dict, on ne change rien.
    max_current_kA = {
        135.0: 0.96,   # ex. HT
        14.0: 0.535,   # ex. MT
        0.208: 0.35,   # ex. BT
    }

    bus_vn = net.bus["vn_kv"]  # série pandas : tension nominale (kV) par bus
    if not net.line.empty:
        # Initialise la colonne si absente
        if "max_i_ka" not in net.line.columns:
            net.line["max_i_ka"] = None

        for i, row in net.line.iterrows():
            vn_from = float(bus_vn.loc[row.from_bus])
            vn_to = float(bus_vn.loc[row.to_bus])
            vn_line = max(vn_from, vn_to)  # choix simple : la plus élevée des deux
            if vn_line in max_current_kA:  # match exact, aucune "recherche du plus proche"
                net.line.at[i, "max_i_ka"] = max_current_kA[vn_line]
            # sinon : on laisse la valeur existante telle quelle

    # 4) Injections P codées en dur (MW)
    #    Convention :
    #      p > 0 -> production (sgen)
    #      p < 0 -> consommation (load) (on passe -p à create_load)
    power_demand = {
        0: 0.0,
        1: 50,         # production
        2: -20,        # consommation
        3: 0,
        4: 0,
        5: -2.5e-2,
        6: 2.5e-2,
        7: -5e-2,
        8: -7.375e-2,
        9: -2.25e-1,
        10: -8.75e-2,
        11: -1.525e-1,
        12: -3.375e-2,
        13: -3.725e-2,
    }

    # (option simple) Neutralise la puissance active des charges/générateurs existants pour ne garder que ce scénario
    if not net.load.empty:
        net.load.loc[:, "p_mw"] = 0.0
    if "sgen" in net and not net.sgen.empty:
        net.sgen.loc[:, "p_mw"] = 0.0
    if not net.gen.empty:
        net.gen.loc[:, "p_mw"] = 0.0

    for bus, p in power_demand.items():
        if abs(p) < 1e-12:
            continue
        if p > 0:
            pp.create_sgen(net, bus=bus, p_mw=float(p), q_mvar=0.0, name=f"sgen_bus{bus}")
        else:
            pp.create_load(net, bus=bus, p_mw=float(-p), q_mvar=0.0, name=f"load_bus{bus}")

    net.name = f"modified_case_14_simple ()"
    return net


if __name__ == "__main__":
    net = build()
    if not net.line.empty:
        print("\nmax_i_ka (lignes):")
        print(net.line[["from_bus", "to_bus", "max_i_ka"]])
    tot_load = net.load["p_mw"].sum() if not net.load.empty else 0.0
    tot_sgen = net.sgen["p_mw"].sum() if "sgen" in net and not net.sgen.empty else 0.0
    print(f"\nTotal consommation (loads): {tot_load:.4f} MW")
    print(f"Total production (sgen):    {tot_sgen:.4f} MW")
