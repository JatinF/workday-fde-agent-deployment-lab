"""Find the repository root without assuming the process cwd."""

from __future__ import annotations

import os
from pathlib import Path


def repo_root() -> Path:
    override = os.environ.get("FDE_LAB_ROOT", "").strip()
    if override:
        return Path(override)
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").is_file() and (parent / "agent").is_dir():
            return parent
    raise FileNotFoundError("FDE lab root not found from " + str(here))
