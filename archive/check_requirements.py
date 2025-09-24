"""Lightweight dependency checker."""

import subprocess
import sys
from importlib import import_module
from pathlib import Path


def check_packages(
    requirements_file: str = "data/requirements.txt",
    show_versions: bool = False,
    install_missing: bool = True,
) -> None:
    """Check presence of packages listed in ``requirements_file``.

    Parameters
    ----------
    requirements_file : str, optional
        Relative path to a pip requirements file.
    show_versions : bool, optional
        If ``True`` display the detected package versions.
    install_missing : bool, optional
        When ``True`` attempt to install missing dependencies using ``pip``.
    """
    requirements_path = Path(__file__).parent.parent / requirements_file
    with open(requirements_path, "r", encoding="utf-8") as file:
        packages = [
            line.strip() for line in file if line.strip() and not line.startswith("#")
        ]
    for pkg in packages:
        try:
            module = import_module(pkg)
        except Exception:
            print(f"{pkg} manquant")
            if install_missing:
                try:
                    subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])
                    module = import_module(pkg)
                except Exception as exc:  # pragma: no cover - installation error
                    print(f"Installation failed for {pkg}: {exc}")
                    continue
        if show_versions:
            version = getattr(module, "__version__", "unknown")
            print(f"{pkg}: {version}")
        else:
            print(f"{pkg} présent")


if __name__ == "__main__":
    check_packages(show_versions=True)
