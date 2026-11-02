"""Portable lint: ruff for python apps, eslint for web."""

import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY_APPS = ["apps/api", "apps/worker"]


def venv_python(app_dir):
    cand = os.path.join(app_dir, ".venv", "Scripts" if os.name == "nt" else "bin",
                         "python" + (".exe" if os.name == "nt" else ""))
    return cand if os.path.exists(cand) else None


def run(cmd, cwd):
    print(f"+ {' '.join(cmd)}  (cwd={os.path.relpath(cwd, ROOT)})")
    # .cmd shims (npm/npx) need a shell on Windows.
    if os.name == "nt" and shutil.which(cmd[0]) is not None:
        return subprocess.run(cmd, cwd=cwd, shell=True).returncode
    return subprocess.run(cmd, cwd=cwd).returncode


def main():
    failures = []
    for app in PY_APPS:
        d = os.path.join(ROOT, app)
        py = venv_python(d) or sys.executable
        if run([py, "-m", "ruff", "check", "."], d) != 0:
            failures.append(app + " (ruff)")

    web = os.path.join(ROOT, "apps", "web")
    if not os.path.isdir(os.path.join(web, "node_modules")):
        print("[lint] web: node_modules missing, run `make setup` with network first")
        failures.append("web (missing node_modules)")
    elif shutil.which("npm") is None:
        print("[lint] web: npm not found")
        failures.append("web (no npm)")
    elif run(["npm", "run", "lint"], web) != 0:
        failures.append("web (eslint)")

    if failures:
        print(f"[lint] FAILED for: {', '.join(failures)}")
        return 1
    print("[lint] all clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
