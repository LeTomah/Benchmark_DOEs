"""Lightweight dependency checker."""

from pathlib import Path
from importlib import import_module


def check_packages(requirements_file: str = "Data/requirements.txt", show_versions: bool = False) -> None:
    """Check presence of packages listed in ``requirements_file``.

    No installation is performed; missing packages are reported to the user.
    """
    requirements_path = Path(__file__).parent / requirements_file
    with open(requirements_path, "r") as file:
        packages = [line.strip() for line in file if line.strip() and not line.startswith("#")]
    for pkg in packages:
        try:
            module = import_module(pkg)
            if show_versions:
                version = getattr(module, "__version__", "unknown")
                print(f"{pkg}: {version}")
            else:
                print(f"{pkg} présent")
        except Exception:
            print(f"{pkg} manquant")


if __name__ == "__main__":
    check_packages(show_versions=True)
