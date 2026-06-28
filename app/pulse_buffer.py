from collections import deque
from datetime import datetime
import threading

# At least two timestamps are required to compute a single interval.
MIN_INTERVAL_SAMPLES = 2


def _window_descriptor(maxlen: int | None) -> str:
    if maxlen is not None:
        return f"last {maxlen} pulses"
    return "unbounded"


def compute_interval_stats(history: deque[str], lock: threading.Lock) -> dict:
    with lock:
        snapshot = list(history)
        maxlen = history.maxlen

    window = _window_descriptor(maxlen)
    count = len(snapshot)
    if count < MIN_INTERVAL_SAMPLES:
        return {
            "count": count,
            "min_interval_s": None,
            "max_interval_s": None,
            "avg_interval_s": None,
            "skew_clamped": 0,
            "window": window,
        }

    intervals: list[float] = []
    skew_clamped = 0
    for i in range(1, count):
        prev = datetime.fromisoformat(snapshot[i - 1])
        curr = datetime.fromisoformat(snapshot[i])
        delta = (curr - prev).total_seconds()
        if delta < 0:
            skew_clamped += 1
            delta = 0.0
        intervals.append(delta)

    return {
        "count": count,
        "min_interval_s": min(intervals),
        "max_interval_s": max(intervals),
        "avg_interval_s": sum(intervals) / len(intervals),
        "skew_clamped": skew_clamped,
        "window": window,
    }