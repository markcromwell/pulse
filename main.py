# PULSE — ASGI entrypoint. `uvicorn main:app` (the Docker CMD) imports `app` from here.
# Do not rename `app` or move this file: the Dockerfile, compose, and boot-smoke all
# assume `main:app` at the repo root. New code goes in app/ (routers in app/routers/).
from app import create_app

app = create_app()
