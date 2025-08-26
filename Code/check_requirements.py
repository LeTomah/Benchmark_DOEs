from pathlib import Path


def install_missing_packages(requirements_file: str = "Data/requirements.txt") -> None:
    """Install any package listed in ``requirements_file`` that is missing."""

    import importlib.util
    import subprocess
    import sys

    requirements_path = Path(__file__).parent / requirements_file

    with open(requirements_path, "r") as file:
        packages = [
            line.strip() for line in file if line.strip() and not line.startswith("#")
        ]

    for package in packages:
        if importlib.util.find_spec(package) is None:
            print(f"{package} n'est pas installé. Installation en cours...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        else:
            print(f"{package} est déjà installé.")


if __name__ == "__main__":
    install_missing_packages()
