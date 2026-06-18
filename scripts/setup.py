'''
setup.py — Install PULSE on a new machine.

Usage:
    python scripts/setup.py              # interactive install
    python scripts/setup.py --check      # validate existing install

Pure stdlib — no pip install needed before running.
'''
from __future__ import annotations

import argparse
import os
import platform
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_GREEN  = lambda t: f"\033[32m{t}\033[0m" if sys.stdout.isatty() else t
_YELLOW = lambda t: f"\033[33m{t}\033[0m" if sys.stdout.isatty() else t
_RED    = lambda t: f"\033[31m{t}\033[0m" if sys.stdout.isatty() else t
_BOLD   = lambda t: f"\033[1m{t}\033[0m"  if sys.stdout.isatty() else t


def check_prerequisites() -> bool:
    ok = True
    # Docker
    if shutil.which("docker") is None:
        print(_RED("  [FAIL] docker not found — install Docker Desktop or Docker Engine"))
        ok = False
    else:
        print(_GREEN("  [ OK ] docker"))

    # Python version
    if sys.version_info < (3, 10):
        print(_RED(f"  [FAIL] Python 3.10+ required (got {sys.version_info.major}.{sys.version_info.minor})"))
        ok = False
    else:
        print(_GREEN(f"  [ OK ] python {sys.version_info.major}.{sys.version_info.minor}"))

    return ok


def port_free(port: int) -> bool:
    with socket.socket() as s:
        return s.connect_ex(("127.0.0.1", port)) != 0


def prompt(label: str, default: str = "", secret: bool = False) -> str:
    import getpass
    hint = f" [{default}]" if default else ""
    try:
        val = (getpass.getpass if secret else input)(f"  {label}{hint}: ").strip()
    except (KeyboardInterrupt, EOFError):
        print()
        sys.exit(1)
    return val or default


def write_env(values: dict[str, str], env_path: Path) -> None:
    existing = env_path.read_text() if env_path.exists() else ""
    lines = existing.splitlines(keepends=True)
    for key, val in values.items():
        for i, line in enumerate(lines):
            if line.startswith(f"{key}="):
                lines[i] = f"{key}={val}\n"
                break
        else:
            lines.append(f"{key}={val}\n")
    tmp = env_path.with_suffix(".tmp")
    tmp.write_text("".join(lines))
    tmp.replace(env_path)
    env_path.chmod(0o600)


def wait_healthy(url: str, timeout: int = 60) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url, timeout=5)
            return True
        except Exception:
            time.sleep(2)
    return False


def run_install(args):
    print(_BOLD("\n=== PULSE installer ===\n"))

    # 1. Prerequisites
    print("Checking prerequisites...")
    if not check_prerequisites():
        print(_RED("\nFix the above issues and re-run."))
        sys.exit(1)

    # 2. Collect env vars
    print("\nCollecting configuration (press Enter to keep defaults):\n")
    env_path = _ROOT / ".env"
    existing_env: dict[str, str] = {}
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                existing_env[k.strip()] = v.strip()

    # TODO: add program-specific keys here, e.g.:
    # api_key = prompt("{CODE}_API_KEY", existing_env.get("{CODE}_API_KEY", ""), secret=True)
    # sov_url = prompt("SOV_URL (Sovereign base URL)", existing_env.get("SOV_URL", "http://localhost:8765"))

    # Write .env
    # write_env({"KEY": api_key, "SOV_URL": sov_url}, env_path)

    # 3. Docker compose up
    print("\nStarting services...")
    result = subprocess.run(
        ["docker", "compose", "up", "-d", "--build"],
        cwd=_ROOT, capture_output=False,
    )
    if result.returncode != 0:
        print(_RED("docker compose up failed — see above output"))
        sys.exit(1)

    # 4. Wait for health
    health_url = "http://localhost:8765/health"  # TODO: update port if different
    print(f"\nWaiting for service at {health_url}...")
    if wait_healthy(health_url):
        print(_GREEN("\nPULSE is up and healthy."))
        print(f"\nNext steps:")
        print(f"  bin/sov health   # verify API is reachable")
        print(f"  bin/sov pipeline # check pipeline status")
    else:
        print(_YELLOW(f"\nService did not respond at {health_url} within 60s."))
        print("Check logs with: docker compose logs -f")


def run_check(args):
    print(_BOLD("\n=== PULSE install check ===\n"))
    ok = check_prerequisites()
    env_path = _ROOT / ".env"
    if env_path.exists():
        print(_GREEN("  [ OK ] .env exists"))
    else:
        print(_YELLOW("  [WARN] .env not found — run python scripts/setup.py to create it"))
        ok = False
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PULSE installer")
    parser.add_argument("--check", action="store_true", help="Validate existing install")
    args = parser.parse_args()
    if args.check:
        run_check(args)
    else:
        run_install(args)
