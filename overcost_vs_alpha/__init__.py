"""Configuration for relative curtailment overcost sweep."""

# ---- User parameters ----
TEST_CASE = "Data/Networks/example_multivoltage_adapted.py"
OPERATIONAL_NODES = [0, 1, 2, 3, 4, 5]
PARENT_NODES = [0]
CHILDREN_NODES = [1, 2, 3, 4, 5]
BETA = 1.0

ALPHA_MIN = 0.0
ALPHA_MAX = 1.0
ALPHA_STEP = 0.5
# ------------------------
