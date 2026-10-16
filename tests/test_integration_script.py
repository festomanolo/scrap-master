import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "test.sh"


def test_integration_script_has_valid_shell_syntax(bash_executable):
    subprocess.run([bash_executable, "-n", SCRIPT.name], check=True, cwd=ROOT)


