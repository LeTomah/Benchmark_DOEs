from pathlib import Path

def install_missing_packages(requirements_file='requirements.txt'):
    import importlib.util
    import subprocess
    import sys

    # Construire le chemin absolu vers requirements.txt
    requirements_path = Path(__file__).parent.parent / "requirements.txt"

    with open(requirements_path, 'r') as file:
        packages = [line.strip() for line in file if line.strip() and not line.startswith('#')]

    for package in packages:
        if importlib.util.find_spec(package) is None:
            print(f"{package} n'est pas installé. Installation en cours...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        else:
            print(f"{package} est déjà installé.")

if __name__ == "__main__":
    install_missing_packages("requirements.txt")