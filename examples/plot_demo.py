import os
import sys

# Ensure the project root is on the PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import matplotlib.pyplot as plt
import networkx as nx

from plot_utils import draw_network, draw_side_by_side, get_or_compute_pos

G = nx.Graph()
G.add_node(1, label="Prod A", is_generator=True, p_mw=50)
G.add_node(2, label="Load B", p_mw=-30)
G.add_node(3, label="Load C", p_mw=-20)
G.add_edges_from([(1, 2), (2, 3)])

pos = get_or_compute_pos(G)
draw_network(G, pos=pos, node_size=120, with_labels=True)
plt.show()

# Variante côte à côte
H = G.copy()
H.add_node(4, label="Prod D", is_generator=True, p_mw=40)
H.add_edge(1, 4)

fig = draw_side_by_side({"Full": G, "Operational": H}, layout="spring", common_pos=True)
plt.show()
