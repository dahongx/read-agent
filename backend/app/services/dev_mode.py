from __future__ import annotations

from pathlib import Path
from typing import List

from app.core.config import settings

# Files that must exist in the fixture directory for DEV_MODE to work
_REQUIRED_FIXTURE_FILES = [
    "design_spec.md",
]
_REQUIRED_FIXTURE_PATTERNS = [
    "*.pptx",
    "notes",
]


class FixtureIncompleteError(RuntimeError):
    pass


def validate_fixture() -> None:
    """
    Check that the fixture directory contains all required files.
    Raises FixtureIncompleteError with a descriptive message if anything is missing.
    Must be called at startup when DEV_MODE=true.
    """
    fixture = settings.fixture_path
    if not fixture.exists():
        raise FixtureIncompleteError(
            f"DEV_MODE fixture directory not found: {fixture.resolve()}"
        )

    missing: List[str] = []

    for fname in _REQUIRED_FIXTURE_FILES:
        if not (fixture / fname).exists():
            missing.append(fname)

    # Check for at least one .pptx
    if not list(fixture.glob("*.pptx")):
        missing.append("*.pptx (no PPTX file found)")

    # Check for notes/ directory
    if not (fixture / "notes").is_dir():
        missing.append("notes/ (directory)")

    if missing:
        raise FixtureIncompleteError(
            "DEV_MODE fixture is incomplete. Missing files:\n"
            + "\n".join(f"  - {m}" for m in missing)
            + f"\n\nFixture directory: {fixture.resolve()}"
        )


def get_fixture_pptx() -> Path:
    """Return the path to the fixture PPTX file."""
    pptx_files = list(settings.fixture_path.glob("*.pptx"))
    if not pptx_files:
        raise FixtureIncompleteError("No PPTX file found in fixture directory")
    return pptx_files[0]
