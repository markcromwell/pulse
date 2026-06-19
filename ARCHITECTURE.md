# PULSE Architecture

## Project Overview

PULSE is a standalone FastAPI ASGI application served by uvicorn via the immutable `main:app` entrypoint. The service is containerized with Docker (uvicorn bound to `0.0.0.0:8000`), configured through pydantic-settings and a `.env` file, and designed as a self-contained API program within the Standard SOV ecosystem. Runtime boot and health checks exercise the same import path used in production.

## File Structure

```
.
├── main.py              # ASGI entrypoint; exposes `app = create_app()` for uvicorn
├── app/
│   ├── __init__.py      # `create_app()` factory; registers all routers
│   ├── config.py        # pydantic-settings `Settings` and `settings` singleton
│   ├── health.py        # `/health` contract router
│   └── routers/         # Feature routers; each include_router'd in create_app()
├── scripts/
│   ├── smoke_boot.py    # Boot gate: import `main:app` and assert /health
│   ├── setup.py         # Operational tooling
│   └── test_unit.py     # Unit tests (pytest)
├── Dockerfile           # Production image; CMD uvicorn main:app
├── docker-compose.yml   # Local container orchestration
├── requirements.in      # Direct dependency declarations
└── requirements.lock    # Pinned lockfile for reproducible installs
```

## Naming Conventions

- **Modules and functions:** `snake_case` (e.g. `app/config.py`, `create_app()`).
- **Routers:** each feature module defines `router = APIRouter()`; `create_app()` calls `application.include_router(...)` for every router under `app/routers/`.
- **Entrypoint:** the ASGI callable is always `main:app` at the repo root — never rename `app` or move `main.py`.
- **Tests:** live in `scripts/test_*.py`; run with `python -m pytest scripts/test_unit.py -x -q`.
- **Health contract:** `GET /health` returns exactly `{"status": "ok"}` with HTTP 200 — no auth, no extra fields.
- **Config fields:** settings attributes use `snake_case` and map to env vars via pydantic-settings (e.g. `database_url`).

## Module Responsibilities

| Module | Owns | Must NOT |
|--------|------|----------|
| `main.py` | Constructs `app = create_app()` for uvicorn/Docker | Define routes, business logic, or settings |
| `app/__init__.py` (`create_app`) | Instantiates `FastAPI`, registers every router | Handle request logic or I/O |
| `app/config.py` | `Settings` model and `settings` singleton | Perform I/O, define routes, or import routers |
| `app/health.py` | `GET /health` returning `{"status": "ok"}` | Auth, DB access, or feature endpoints |
| `app/routers/` | Feature-specific endpoints and schemas | App factory logic or global settings |
| `scripts/` | Tests (`test_*.py`), boot gate (`smoke_boot`), tooling | App runtime wiring beyond importing the factory |

New feature work adds a router under `app/routers/`, registers it in `create_app()`, and extends `scripts/test_unit.py` (or a named topic file under `scripts/tests/`).

## How to Test

Run from the repository root:

```bash
python -m scripts.smoke_boot                 # boot gate: import main:app + /health
python -m pytest scripts/test_unit.py -x -q  # unit suite
```

`smoke_boot` must not modify `sys.path`; it imports `main:app` exactly as Docker does. CI runs the pytest command on every push.