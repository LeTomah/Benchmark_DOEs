import math
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from viz.plot_utils import parse_alpha_list
from viz.rel_overcost import relative_overcost_pct


def test_relative_overcost_pct():
    assert relative_overcost_pct(10.0, 15.0) == 50.0


def test_relative_overcost_pct_zero_opf():
    assert math.isnan(relative_overcost_pct(0.0, 10.0))


def test_parse_alpha_list():
    assert parse_alpha_list("0,0.5,1") == [0.0, 0.5, 1.0]
    assert parse_alpha_list("0:1:0.5") == [0.0, 0.5, 1.0]
