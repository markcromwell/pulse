# PULSE

A Standard SOV Program (FastAPI + Docker) bootstrapped by Sovereign.

## Run locally
    uv pip compile requirements.in -o requirements.lock   # if deps changed
    pip install -r requirements.lock
    uvicorn main:app --reload

## Verify it boots like prod
    python -m scripts.smoke_boot                 # import + /health, no path hacks
    python -m pytest scripts/test_unit.py -x -q

## Docker
    docker compose up --build
    curl -fsS http://localhost:8000/health       # -> ok

## Conventions (the pipeline gate enforces these)
- Entrypoint is `main:app` at the repo root. No `src/` layout, no PYTHONPATH.
- New code goes in `app/` (routers in `app/routers/`, each include_router'd in `create_app()`).
- New deps go in `requirements.in`, then recompile the lock. `/health` returns exactly ok.
- `scripts/smoke_boot.py` must never touch `sys.path`.
