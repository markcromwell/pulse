from collections import deque
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


pulse_buffer = PulseBuffer()