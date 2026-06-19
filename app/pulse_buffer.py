from collections import deque
from datetime import datetime
import threading


class PulseBuffer:
    def __init__(self, maxlen: int = 20) -> None:
        self._buffer: deque[str] = deque(maxlen=maxlen)
        self._lock = threading.Lock()

    def append(self, timestamp: str) -> None:
        with self._lock:
            self._buffer.append(timestamp)

    def get_recent(self) -> list[str]:
        with self._lock:
            return list(self._buffer)

    def compute_interval_stats(self) -> dict:
        with self._lock:
            snapshot = list(self._buffer)
            window = self._buffer.maxlen

        count = len(snapshot)
        if count < 2:
            return {
                "count": count,
                "min_interval_seconds": None,
                "max_interval_seconds": None,
                "avg_interval_seconds": None,
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
            "min_interval_seconds": min(intervals),
            "max_interval_seconds": max(intervals),
            "avg_interval_seconds": sum(intervals) / len(intervals),
            "skew_clamped": skew_clamped,
            "window": window,
        }


pulse_buffer = PulseBuffer()