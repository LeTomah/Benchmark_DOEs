import pandapower as pp

def load():
    """Return a minimal two-bus pandapower network."""
    net = pp.create_empty_network()
    b1 = pp.create_bus(net, vn_kv=0.4)
    b2 = pp.create_bus(net, vn_kv=0.4)
    pp.create_line_from_parameters(net, b1, b2, length_km=1.0,
                                   r_ohm_per_km=0.1, x_ohm_per_km=0.1,
                                   c_nf_per_km=0.0, max_i_ka=1.0)
    return net
