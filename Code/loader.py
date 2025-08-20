def load_network(test_case):
    """
    Permet de charger correctement l'import du réseau test, suivant sa nature (fichier python PandaPower,
    ou MatPower avec la convention IEEE).
    :param test_case: nom du fichier .txt ou .py contenant le réseau test.
    :return: réseau type PandaPower lisible par le code.
    """
    import os, importlib.util, pandapower as pp
    from IEEE_to_pp import import_ieee_txt_to_pandapower

    # 1) Déjà un objet pandapower ?
    if isinstance(test_case, pp.pandapowerNet):
        return test_case

    # 2) Chaîne de caractères = chemin de fichier
    if not isinstance(test_case, str):
        raise TypeError("test_case doit être un chemin ou un objet pandapowerNet")

    ext = os.path.splitext(test_case)[1].lower()

    # 2-a) Fichier IEEE (.txt) ➜ conversion
    if ext == ".txt":
        return import_ieee_txt_to_pandapower(test_case)

    # 2-b) Fichier MATPOWER (.m) ➜ conversion
    if ext == ".m":
        try:
            import pandapower.converter as pc
        except Exception as e:
            raise ImportError(
                "Impossible d'importer pandapower.converter pour la conversion MATPOWER (.m)."
            ) from e

        # f_hz par défaut = 50; adapter si vos cas sont à 60 Hz
        net = pc.from_matpower(test_case, validate_conversion=False, f_hz=50)
        if not isinstance(net, pp.pandapowerNet):
            raise TypeError("La conversion MATPOWER (.m) n'a pas renvoyé un pandapowerNet.")
        return net

    # 2-c) Script Python qui construit déjà le réseau
    if ext == ".py":
        spec = importlib.util.spec_from_file_location("user_net", test_case)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # soit la variable globale « net », soit une factory « create_network() »
        if hasattr(module, "net"):
            net = module.net
        elif hasattr(module, "create_network"):
            net = module.create_network()
        else:
        # BONUS : prise en charge des cas PYPOWER/MATPOWER Python qui fournissent un dict « mpc »
            if hasattr(module, "mpc"):
                try:
                    import pandapower.converter as pc
                except Exception as e:
                    raise ImportError(
                        "Impossible d'importer pandapower.converter pour convertir un 'mpc' Python."
                    ) from e
                net = pc.from_mpc(module.mpc, validate_conversion=False, f_hz=50)
            else:
                raise AttributeError(
                    f"{test_case} doit contenir une variable 'net', une fonction 'create_network()' "
                    f"ou un dict 'mpc' compatible MATPOWER/PYPOWER."
                )

    if not isinstance(net, pp.pandapowerNet):
        raise TypeError("L’objet chargé n’est pas un pandapowerNet")
    return net

    raise ValueError(f"Format de fichier non pris en charge : {ext}")

if __name__ == "__main__":
    load_network("Networks/network_test.py")