import os
import sys

# Ensure the project root is on the PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import networkx as nx
from plot_utils import get_or_compute_pos, draw_network, draw_side_by_side
import matplotlib.pyplot as plt

G = nx.Graph()
G.add_node(1, label="A")
G.add_node(2, label="B")
G.add_node(3, label="C")
G.add_edges_from([(1, 2), (2, 3)])

pos = get_or_compute_pos(G)
draw_network(G, pos=pos)
plt.show()

# Variante côte à côte
H = G.copy()
H.add_node(4, label="D")
H.add_edge(1, 4)

fig = draw_side_by_side({"Full": G, "Operational": H}, layout="spring", common_pos=True)
plt.show()
print("demo done")
