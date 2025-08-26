import json

import pandapower.plotting as plot
import pandas as pd
import shapely.geometry as geom


def import_ieee_txt_to_pandapower(filename):
    import pandapower as pp
    import pandas as pd
    from pandapower.plotting import create_generic_coordinates
    from pandapower.plotting.geo import convert_geodata_to_geojson

    net = pp.create_empty_network()
    with open(filename, "r") as f:
        lines = f.readlines()

    # Parse BUS DATA
    bus_data = []
    branch_data = []
    reading_bus, reading_branch = False, False

    for line in lines:
        if "BUS DATA" in line:
            reading_bus = True
        elif "BRANCH DATA" in line:
            reading_bus, reading_branch = False, True
        elif "-999" in line and reading_bus:
            reading_bus = False
        elif "-999" in line and reading_branch:
            reading_branch = False
        elif reading_bus:
            if line.strip() and not line.startswith("#"):
                bus_data.append(line)
        elif reading_branch:
            if line.strip() and not line.startswith("#"):
                branch_data.append(line)

    bus_map = {}
    # 1. Créer les bus
    for row in bus_data:
        data = row.split()
        idx = int(data[0])
        name = data[1]
        vn_kv = 110 if "HV" in data[2] else 20 if "MV" in data[2] else 0.4
        bus_map[idx] = pp.create_bus(net, vn_kv=vn_kv, name=name)

    # 2. Ajouter ext_grid, gen et charges
    for row in bus_data:
        data = row.split()
        idx = int(data[0])
        bustype = int(data[5])
        vm_pu = float(data[6])
        p_load = float(data[8])
        q_load = float(data[9])
        p_gen = float(data[10])
        q_gen = float(data[11])
        # Slack (toujours bus 1)
        if idx == 1:
            pp.create_ext_grid(net, bus=bus_map[idx], vm_pu=vm_pu)
        # PV (gen) buses
        if p_gen != 0 and idx != 1:
            pp.create_gen(
                net, bus=bus_map[idx], p_mw=p_gen, vm_pu=vm_pu, name=f"Gen_{idx}"
            )
        # Loads
        if p_load != 0 or q_load != 0:
            pp.create_load(
                net, bus=bus_map[idx], p_mw=p_load, q_mvar=q_load, name=f"Load_{idx}"
            )

    # 3. Lignes (ou trafo si tu veux détecter le type)
    for row in branch_data:
        data = row.split()
        from_bus = int(data[0])
        to_bus = int(data[1])
        r = float(data[6])
        x = float(data[7])
        b = float(data[8])
        # Génère une ligne fictive de 1km
        pp.create_line_from_parameters(
            net,
            from_bus=bus_map[from_bus],
            to_bus=bus_map[to_bus],
            length_km=1.0,
            r_ohm_per_km=r,
            x_ohm_per_km=x,
            c_nf_per_km=0,
            max_i_ka=1.0,
            name=f"Line_{from_bus}_{to_bus}",
        )

    # 4. Générer les coordonnées et les convertir au format moderne
    # a) S'assurer que la table existe
    net["bus_geodata"] = pd.DataFrame(index=net.bus.index)

    # b) Calcul automatique (ou laissez seed=None pour un layout aléatoire)
    create_generic_coordinates(net, overwrite=True)

    # c) Conversion x/y  ➜  geometry Point (GeoJSON)
    convert_geodata_to_geojson(net)

    return net


if __name__ == "__main__":
    net = import_ieee_txt_to_pandapower("Case_14.txt")

    plot.simple_plot(net)

    # Récupération des points (lon/lat) dans un DataFrame lisible
    bus_coords = net.bus["geo"].apply(
        lambda g: geom.shape(json.loads(g)).coords[0] if pd.notna(g) else (None, None)
    )

    df_bus = net.bus.assign(lon=bus_coords.str[0], lat=bus_coords.str[1])
    print(df_bus[["name", "lon", "lat"]].head())
