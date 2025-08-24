def load_network(test_case):
    """Load a test network from a Python script returning a pandapowerNet.

    Parameters
    ----------
    test_case : str or pandapowerNet
        Path to the ``.py`` file defining the network or an existing pandapowerNet.

    Returns
    -------
    pandapowerNet
        The loaded network.
    """

    import os
    import importlib.util
    import inspect
    import pandapower as pp

    # 1) Already a pandapower network?
    if isinstance(test_case, pp.pandapowerNet):
        return test_case

    # 2) String path to a file
    if not isinstance(test_case, str):
        raise TypeError("test_case doit être un chemin ou un objet pandapowerNet")

    ext = os.path.splitext(test_case)[1].lower()
    if ext != ".py":
        raise ValueError(
            f"Format de fichier non pris en charge : {ext}. Seuls les fichiers .py sont acceptés."
        )

    # Import the module containing the network definition
    spec = importlib.util.spec_from_file_location("user_net", test_case)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    # Retrieve network either as a variable 'net' or via a zero-arg callable
    if hasattr(module, "net"):
        net = module.net
    else:
        net = None
        for attr in module.__dict__.values():
            if callable(attr):
                try:
                    sig = inspect.signature(attr)
                except (TypeError, ValueError):
                    continue
                if len(sig.parameters) == 0:
                    candidate = attr()
                    if isinstance(candidate, pp.pandapowerNet):
                        net = candidate
                        break

        if net is None:
            raise AttributeError(
                f"{test_case} doit contenir une variable 'net' ou une fonction sans argument renvoyant un pandapowerNet."
            )

    if not isinstance(net, pp.pandapowerNet):
        raise TypeError("L’objet chargé n’est pas un pandapowerNet")

    return net


if __name__ == "__main__":
    load_network("Data/Networks/network_test.py")

