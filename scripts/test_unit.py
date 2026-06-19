# Unit tests for PULSE. Uses the app factory for an isolated instance.
from collections import deque
from datetime import datetime
from pathlib import Path
import threading
import time
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

import app.routers.pulse as pulse_module
from app import create_app

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
