from collections import deque
import os
import threading
import time
from datetime import UTC, datetime

from fastapi import APIRouter

from app.pulse_buffer import compute_interval_stats

router = APIRouter()

_start_time = time.time()


class _PulseCounter:
    value: int = 0


_counter = _PulseCounter()
_pulse_history: deque[str] = deque(maxlen=20)
_pulse_history_lock = threading.Lock()


@router.get("/pulse")
def pulse() -> dict:
    _counter.value += 1
    timestamp = datetime.now(UTC).isoformat()
    with _pulse_history_lock:
        _pulse_history.append(timestamp)
    return {
        "count": _counter.value,
        "uptime_seconds": time.time() - _start_time,
        "sha": os.environ.get("COMMIT_SHA", "unknown"),
    }


@router.get("/pulse/history")
def pulse_history() -> dict:
    with _pulse_history_lock:
        recent = list(_pulse_history)
    return {"recent": recent}


@router.get("/pulse/stats")
def pulse_stats() -> dict:
    return compute_interval_stats(_pulse_history, _pulse_history_lock)
