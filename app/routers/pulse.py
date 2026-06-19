from collections import deque
import os
import threading
import time
from datetime import datetime, timezone

from fastapi import APIRouter

router = APIRouter()

_start_time = time.time()
_counter = 0
_pulse_history: deque[str] = deque(maxlen=20)
_pulse_history_lock = threading.Lock()


@router.get("/pulse")
def pulse() -> dict:
    global _counter
    _counter += 1
    timestamp = datetime.now(timezone.utc).isoformat()
    with _pulse_history_lock:
        _pulse_history.append(timestamp)
    return {
        "count": _counter,
        "uptime_seconds": time.time() - _start_time,
        "sha": os.environ.get("COMMIT_SHA", "unknown"),
    }


@router.get("/pulse/history")
def pulse_history() -> dict:
    with _pulse_history_lock:
        recent = list(_pulse_history)
    return {"recent": recent}
