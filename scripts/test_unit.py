# Unit tests for PULSE. Uses the app factory for an isolated instance.
from pathlib import Path
import time

from fastapi.testclient import TestClient

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
