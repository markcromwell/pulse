# Unit tests for PULSE. Uses the app factory for an isolated instance.
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
import threading
import time
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

import app.routers.pulse as pulse_module
from app import create_app
from app.pulse_buffer import compute_interval_stats

REPO_ROOT = Path(__file__).resolve().parent.parent
ARCHITECTURE_MD = REPO_ROOT / "ARCHITECTURE.md"

REQUIRED_SECTIONS = (
    "Project Overview",
    "File Structure",
    "Naming Conventions",
    "Module Responsibilities",
    "How to Test",
)

client = TestClient(create_app())


def test_health_ok():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_architecture_md_exists():
    assert ARCHITECTURE_MD.is_file()


def test_architecture_md_line_count():
    lines = ARCHITECTURE_MD.read_text(encoding="utf-8").splitlines()
    assert len(lines) <= 150, f"ARCHITECTURE.md has {len(lines)} lines (max 150)"


def test_architecture_md_required_sections():
    text = ARCHITECTURE_MD.read_text(encoding="utf-8")
    for heading in REQUIRED_SECTIONS:
        assert f"## {heading}" in text, f"missing section: {heading}"


def test_architecture_md_naming_conventions_fastapi_specific():
    text = ARCHITECTURE_MD.read_text(encoding="utf-8")
    naming_start = text.index("## Naming Conventions")
    naming_end = text.index("## Module Responsibilities")
    naming_section = text[naming_start:naming_end]
    for marker in ("main:app", "app/routers", "snake_case"):
        assert marker in naming_section, f"naming section missing {marker!r}"


def test_architecture_md_how_to_test_commands():
    text = ARCHITECTURE_MD.read_text(encoding="utf-8")
    how_to_test_start = text.index("## How to Test")
    how_to_test_section = text[how_to_test_start:]
    assert "python -m scripts.smoke_boot" in how_to_test_section
    assert "python -m pytest scripts/test_unit.py -x -q" in how_to_test_section


def clear_pulse_history():
    with pulse_module._pulse_history_lock:
        pulse_module._pulse_history.clear()


def test_pulse():
    resp1 = client.get("/pulse")
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert isinstance(data1["count"], int)
    assert isinstance(data1["uptime_seconds"], (int, float))
    assert data1["uptime_seconds"] >= 0
    assert isinstance(data1["sha"], str)

    time.sleep(0.1)

    resp2 = client.get("/pulse")
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert isinstance(data2["count"], int)
    assert isinstance(data2["uptime_seconds"], (int, float))
    assert data2["uptime_seconds"] >= 0
    assert isinstance(data2["sha"], str)
    assert data2["count"] - data1["count"] == 1
    assert data2["uptime_seconds"] > data1["uptime_seconds"]


def test_pulse_history_buffer_is_module_level_deque_with_lock():
    assert isinstance(pulse_module._pulse_history, deque)
    assert pulse_module._pulse_history.maxlen == 20
    assert isinstance(pulse_module._pulse_history_lock, type(threading.Lock()))


def test_pulse_records_valid_iso8601_timestamps():
    clear_pulse_history()
    client.get("/pulse")
    client.get("/pulse")

    resp = client.get("/pulse/history")
    assert resp.status_code == 200
    recent = resp.json()["recent"]
    assert len(recent) == 2
    for ts in recent:
        parsed = datetime.fromisoformat(ts)
        assert parsed.tzinfo is not None


def test_pulse_records_monotonic_timestamps():
    clear_pulse_history()
    client.get("/pulse")
    time.sleep(0.01)
    client.get("/pulse")

    recent = client.get("/pulse/history").json()["recent"]
    assert len(recent) == 2
    ts1 = datetime.fromisoformat(recent[0])
    ts2 = datetime.fromisoformat(recent[1])
    assert ts2 > ts1


def test_pulse_history_returns_recent_timestamps_newest_last():
    clear_pulse_history()
    before = client.get("/pulse/history").json()["recent"]
    assert before == []

    pulse_resp = client.get("/pulse")
    assert pulse_resp.status_code == 200

    history_resp = client.get("/pulse/history")
    assert history_resp.status_code == 200
    data = history_resp.json()
    assert list(data) == ["recent"]
    recent = data["recent"]
    assert isinstance(recent, list)
    assert len(recent) == 1
    parsed = datetime.fromisoformat(recent[-1])
    assert parsed.tzinfo is not None

    time.sleep(0.01)
    client.get("/pulse")
    updated_recent = client.get("/pulse/history").json()["recent"]
    assert len(updated_recent) == 2
    assert updated_recent[0] == recent[-1]
    assert datetime.fromisoformat(updated_recent[-1]) > parsed


def test_pulse_history_never_exceeds_twenty_entries():
    clear_pulse_history()
    for _ in range(25):
        client.get("/pulse")

    resp = client.get("/pulse/history")
    assert resp.status_code == 200
    recent = resp.json()["recent"]
    assert isinstance(recent, list)
    assert len(recent) == 20
    for ts in recent:
        assert datetime.fromisoformat(ts).tzinfo is not None


def test_pulse_history_access_uses_shared_lock():
    mock_lock = MagicMock()
    mock_lock.__enter__ = MagicMock(return_value=None)
    mock_lock.__exit__ = MagicMock(return_value=False)
    original_lock = pulse_module._pulse_history_lock
    try:
        pulse_module._pulse_history_lock = mock_lock
        pulse_module.pulse()
        pulse_module.pulse_history()
    finally:
        pulse_module._pulse_history_lock = original_lock

    assert mock_lock.__enter__.call_count == 2
    assert mock_lock.__exit__.call_count == 2


def _history_with_timestamps(
    timestamps: list[str], *, maxlen: int = 20
) -> tuple[deque[str], threading.Lock]:
    history: deque[str] = deque(maxlen=maxlen)
    lock = threading.Lock()
    with lock:
        for ts in timestamps:
            history.append(ts)
    return history, lock


def test_compute_interval_stats_empty_buffer():
    history, lock = _history_with_timestamps([])
    stats = compute_interval_stats(history, lock)
    assert stats == {
        "count": 0,
        "min_interval_s": None,
        "max_interval_s": None,
        "avg_interval_s": None,
        "skew_clamped": 0,
        "window": "last 20 pulses",
    }


def test_compute_interval_stats_single_entry():
    history, lock = _history_with_timestamps(["2026-01-01T00:00:00+00:00"])
    stats = compute_interval_stats(history, lock)
    assert stats == {
        "count": 1,
        "min_interval_s": None,
        "max_interval_s": None,
        "avg_interval_s": None,
        "skew_clamped": 0,
        "window": "last 20 pulses",
    }


def test_compute_interval_stats_multi_entry():
    history, lock = _history_with_timestamps(
        [
            "2026-01-01T00:00:00+00:00",
            "2026-01-01T00:00:10+00:00",
            "2026-01-01T00:00:25+00:00",
        ],
        maxlen=10,
    )
    stats = compute_interval_stats(history, lock)
    assert stats["count"] == 3
    assert stats["min_interval_s"] == 10.0
    assert stats["max_interval_s"] == 15.0
    assert stats["avg_interval_s"] == 12.5
    assert stats["skew_clamped"] == 0
    assert stats["window"] == "last 10 pulses"


def test_compute_interval_stats_clamps_clock_skew():
    history, lock = _history_with_timestamps(
        [
            "2026-01-01T00:00:20+00:00",
            "2026-01-01T00:00:10+00:00",
            "2026-01-01T00:00:30+00:00",
        ]
    )
    stats = compute_interval_stats(history, lock)
    assert stats["count"] == 3
    assert stats["skew_clamped"] == 1
    assert stats["min_interval_s"] == 0.0
    assert stats["max_interval_s"] == 20.0
    assert stats["avg_interval_s"] == 10.0
    assert stats["min_interval_s"] >= 0
    assert stats["avg_interval_s"] >= 0


def test_compute_interval_stats_concurrent_writes():
    history: deque[str] = deque(maxlen=50)
    lock = threading.Lock()
    errors: list[Exception] = []
    stop = threading.Event()

    def writer() -> None:
        i = 0
        while not stop.is_set():
            try:
                with lock:
                    history.append(
                        datetime.fromtimestamp(
                            1_700_000_000 + i, tz=timezone.utc
                        ).isoformat()
                    )
                i += 1
            except Exception as exc:
                errors.append(exc)

    def reader() -> None:
        while not stop.is_set():
            try:
                stats = compute_interval_stats(history, lock)
                assert isinstance(stats["count"], int)
                assert stats["count"] >= 0
                assert stats["window"] == "last 50 pulses"
                assert stats["skew_clamped"] >= 0
                if stats["count"] < 2:
                    assert stats["min_interval_s"] is None
                    assert stats["max_interval_s"] is None
                    assert stats["avg_interval_s"] is None
                    assert stats["skew_clamped"] == 0
                else:
                    assert stats["min_interval_s"] is not None
                    assert stats["max_interval_s"] is not None
                    assert stats["avg_interval_s"] is not None
                    assert stats["min_interval_s"] >= 0
                    assert stats["avg_interval_s"] >= 0
            except Exception as exc:
                errors.append(exc)

    writers = [threading.Thread(target=writer) for _ in range(4)]
    readers = [threading.Thread(target=reader) for _ in range(4)]
    for t in writers + readers:
        t.start()
    time.sleep(0.2)
    stop.set()
    for t in writers + readers:
        t.join(timeout=2)
    assert errors == []


def test_pulse_stats_empty_buffer():
    clear_pulse_history()
    resp = client.get("/pulse/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data == {
        "count": 0,
        "min_interval_s": None,
        "max_interval_s": None,
        "avg_interval_s": None,
        "skew_clamped": 0,
        "window": "last 20 pulses",
    }


def test_pulse_stats_known_sequence():
    clear_pulse_history()
    with pulse_module._pulse_history_lock:
        pulse_module._pulse_history.append("2026-01-01T00:00:00+00:00")
        pulse_module._pulse_history.append("2026-01-01T00:00:10+00:00")
        pulse_module._pulse_history.append("2026-01-01T00:00:25+00:00")

    resp = client.get("/pulse/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 3
    assert data["min_interval_s"] == 10.0
    assert data["max_interval_s"] == 15.0
    assert data["avg_interval_s"] == 12.5
    assert data["skew_clamped"] == 0
    assert data["window"] == "last 20 pulses"


def test_pulse_stats_clamps_clock_skew():
    clear_pulse_history()
    with pulse_module._pulse_history_lock:
        pulse_module._pulse_history.append("2026-01-01T00:00:20+00:00")
        pulse_module._pulse_history.append("2026-01-01T00:00:10+00:00")
        pulse_module._pulse_history.append("2026-01-01T00:00:30+00:00")

    resp = client.get("/pulse/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 3
    assert data["skew_clamped"] == 1
    assert data["min_interval_s"] == 0.0
    assert data["max_interval_s"] == 20.0
    assert data["avg_interval_s"] == 10.0


def test_pulse_stats_handler_delegates_to_buffer_function():
    clear_pulse_history()
    with pulse_module._pulse_history_lock:
        pulse_module._pulse_history.append("2026-01-01T00:00:00+00:00")
        pulse_module._pulse_history.append("2026-01-01T00:00:05+00:00")

    expected = compute_interval_stats(
        pulse_module._pulse_history, pulse_module._pulse_history_lock
    )
    resp = client.get("/pulse/stats")
    assert resp.status_code == 200
    assert resp.json() == expected


def test_pulse_stats_does_not_hold_lock_during_response():
    mock_lock = MagicMock()
    mock_lock.__enter__ = MagicMock(return_value=None)
    mock_lock.__exit__ = MagicMock(return_value=False)
    original_lock = pulse_module._pulse_history_lock
    try:
        pulse_module._pulse_history_lock = mock_lock
        pulse_module.pulse_stats()
    finally:
        pulse_module._pulse_history_lock = original_lock

    assert mock_lock.__enter__.call_count == 1
    assert mock_lock.__exit__.call_count == 1


def test_pulse_stats_concurrent_writes_no_tearing():
    clear_pulse_history()
    errors: list[Exception] = []
    stop = threading.Event()
    counts: list[int] = []

    def writer() -> None:
        while not stop.is_set():
            try:
                client.get("/pulse")
            except Exception as exc:
                errors.append(exc)

    def reader() -> None:
        while not stop.is_set():
            try:
                resp = client.get("/pulse/stats")
                assert resp.status_code == 200
                data = resp.json()
                count = data["count"]
                counts.append(count)
                assert 0 <= count <= 20
                assert data["window"] == "last 20 pulses"
                assert data["skew_clamped"] >= 0
                if count < 2:
                    assert data["min_interval_s"] is None
                    assert data["max_interval_s"] is None
                    assert data["avg_interval_s"] is None
                else:
                    assert data["min_interval_s"] is not None
                    assert data["max_interval_s"] is not None
                    assert data["avg_interval_s"] is not None
                    assert data["min_interval_s"] >= 0
            except Exception as exc:
                errors.append(exc)

    writers = [threading.Thread(target=writer) for _ in range(4)]
    readers = [threading.Thread(target=reader) for _ in range(4)]
    for t in writers + readers:
        t.start()
    time.sleep(0.2)
    stop.set()
    for t in writers + readers:
        t.join(timeout=2)
    assert errors == []
    assert counts
    assert max(counts) <= 20
