import os
import time
from datetime import datetime, timezone

from fastapi import APIRouter

from app.pulse_buffer import pulse_buffer

router = APIRouter()

_start_time = time.time()
_counter = 0


@router.get("/pulse")
def pulse() -> dict:
    global _counter
    _counter += 1
    pulse_buffer.append(datetime.now(timezone.utc).isoformat())
    return {
        "count": _counter,
        "uptime_seconds": time.time() - _start_time,
        "sha": os.environ.get("COMMIT_SHA", "unknown"),
    }