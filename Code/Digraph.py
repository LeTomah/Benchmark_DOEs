# Conversion en DiGraph
G = nx.DiGraph()

# Créer les positions à partir de la colonne "geo"
if "geo" in net.bus.columns and net.bus["geo"].notnull().all():
    pos = {idx: row["geo"] for idx, row in net.bus.iterrows()}
else:
    # fallback arbitraire si les géodonnées sont manquantes
    pos = {idx: (i, 0) for i, idx in enumerate(net.bus.index)}

# Ajouter les nœuds (avec le nom comme label)
for idx, row in net.bus.iterrows():
    G.add_node(idx, label=row["name"])

# Ajouter les arêtes pour les lignes
for _, row in net.line.iterrows():
    G.add_edge(row["from_bus"], row["to_bus"], type="line", name=row["name"])

# Ajouter les arêtes pour les transformateurs
for _, row in net.trafo.iterrows():
    G.add_edge(row["hv_bus"], row["lv_bus"], type="trafo", name=row["name"])

# Ajouter les arêtes pour les générateurs et charges (boucles locales)
for _, row in net.gen.iterrows():
    G.add_edge(row["bus"], row["bus"], type="gen", name=row["name"])
for _, row in net.load.iterrows():
    G.add_edge(row["bus"], row["bus"], type="load", name=row["name"])
for _, row in net.ext_grid.iterrows():
    G.add_edge(row["bus"], row["bus"], type="ext_grid", name=row["name"])
