import pandapower.networks as pn
import pandapower as pp

def modified_case_14():
    net = pn.case14()

    # Find line indices for (9,10) and (13,14)
    line_idx = net.line[
        ((net.line.from_bus == 8) & (net.line.to_bus == 9)) |   # buses are 0-based in pandapower
        ((net.line.from_bus == 12) & (net.line.to_bus == 13))
    ].index

    # Find trafo index for (7,9)
    trafo_idx = net.trafo[
        ((net.trafo.hv_bus == 6) & (net.trafo.lv_bus == 8))
    ].index

    # Drop them
    pp.drop_lines(net, line_idx)
    pp.drop_trafos(net, trafo_idx)

    return net

net = modified_case_14()
pp.plotting.simple_plotly(net)