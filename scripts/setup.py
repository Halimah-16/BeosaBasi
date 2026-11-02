"""Portable setup: python envs (uv preferred, pip fallback) + npm for web.

Tolerates npm failure (offline machine) with a warning, per TK-000:
the web scaffold files must exist even when installs cannot run.
"""

import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY_APPS = ["apps/api", "apps/worker"]
WEB_APP = os.path.join(ROOT, "apps", "web")


def run(cmd, cwd):
    print(f"+ {' '.join(cmd)}  (cwd={os.path.relpath(cwd, ROOT)})")
    # Bare command names (*.cmd shims like npm/npx) need a shell on Windows;
    # absolute paths (e.g. venv python) run directly.
    shell = os.name == "nt" and os.path.dirname(cmd[0]) == ""
    if shell and shutil.which(cmd[0]) is not None:
        return subprocess.run(cmd, cwd=cwd, shell=True).returncode
    return subprocess.run(cmd, cwd=cwd).returncode


def main():
    use_shell = os.name == "nt"
    failures = []

    if shutil.which("uv"):
        print("[setup] using uv")
        for app in PY_APPS:
            d = os.path.join(ROOT, app)
            # --frozen when a lockfile exists, plain sync (creates lock) otherwise.
            code = run(["uv", "sync", "--frozen", "--extra", "test"], d)
            if code != 0:
                code = run(["uv", "sync", "--extra", "test"], d)
            if code != 0:
                failures.append(app)
    else:
        print("[setup] uv not found, using pip + venv")
        for app in PY_APPS:
            d = os.path.join(ROOT, app)
            venv_py = os.path.join(d, ".venv", "Scripts" if os.name == "nt" else "bin",
                                   "python")
            if run([sys.executable, "-m", "venv", os.path.join(d, ".venv")], ROOT) != 0:
                failures.append(app)
                continue
            if run([venv_py, "-m", "pip", "install", "-e", f"{d}[test]"], ROOT) != 0:
                failures.append(app)

    if shutil.which("npm"):
        if run(["npm", "install"], WEB_APP) != 0:
            print("[setup] WARNING: npm install failed; web files exist but "
                  "lint/test need network. (TK-000 allows this.)")
    else:
        print("[setup] WARNING: npm not found; skipping web install.")

    if failures:
        print(f"[setup] FAILED for: {', '.join(failures)}")
        return 1
    print("[setup] done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
