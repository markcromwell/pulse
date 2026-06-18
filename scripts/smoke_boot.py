# Boot-smoke: prove the artifact imports and answers /health the SAME way the Docker image
# does — NO sys.path hacks, NO conftest shims. Run from the repo root: python -m scripts.smoke_boot
# Exit 0 = booted + /health == ok. This file MUST NOT modify sys.path.
import sys


def main() -> int:
    from main import app  # noqa: E402  (no path setup on purpose)
    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        resp = client.get("/health")
        if resp.status_code != 200:
            print(f"BOOT-SMOKE FAIL: /health -> {resp.status_code}", file=sys.stderr)
            return 1
        if resp.json() != {"status": "ok"}:
            print(f"BOOT-SMOKE FAIL: /health body {resp.json()!r}", file=sys.stderr)
            return 1

    print("BOOT-SMOKE OK: app imported and /health == ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
