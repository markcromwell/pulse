import os
import time

from fastapi import APIRouter

router = APIRouter()

_start_time = time.time()
_counter = 0


@router.get("/pulse")
def pulse() -> dict:
    global _counter
    _counter += 1
    return {
        "count": _counter,
        "uptime_seconds": time.time() - _start_time,
        "sha": os.environ.get("COMMIT_SHA", "unknown"),
    }