from fastapi import FastAPI

from app.config import settings
from app.health import router as health_router
from app.routers.pulse import router as pulse_router


def create_app() -> FastAPI:
    # App factory. Register EVERY router here so the boot-smoke import exercises the whole
    # app graph — this is what catches missing deps (jinja2 / python-multipart) before deploy.
    application = FastAPI(title=settings.app_name, version=settings.version)
    application.include_router(health_router)
    application.include_router(pulse_router)
    # NEW FEATURE ROUTERS: add one include_router(...) line per router below.
    return application
