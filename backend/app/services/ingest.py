"""
Ingest service: startup checks for Cognee local storage.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# Cognee stores its graph and vector data here by default.
COGNEE_SYSTEM_DIR = Path(os.getenv("COGNEE_SYSTEM_PATH", ".cognee_system"))


def check_cognee_storage() -> None:
    """
    Verify that Cognee's local storage directory is writable.

    Call this at startup so failures are caught early with a clear message
    rather than surfacing mid-request.

    Raises:
        RuntimeError: if the directory cannot be created or written to.
    """
    try:
        COGNEE_SYSTEM_DIR.mkdir(parents=True, exist_ok=True)
        probe = COGNEE_SYSTEM_DIR / ".write_check"
        probe.touch()
        probe.unlink()
    except PermissionError as exc:
        raise RuntimeError(
            f"Cognee storage directory '{COGNEE_SYSTEM_DIR}' is not writable. "
            "Check directory permissions before starting the service."
        ) from exc
    except OSError as exc:
        raise RuntimeError(
            f"Cannot access Cognee storage directory '{COGNEE_SYSTEM_DIR}': {exc}"
        ) from exc
