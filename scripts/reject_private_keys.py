"""Fail if a tracked file contains a private-key block."""

from __future__ import annotations

from pathlib import Path

SKIP = {
    ".git",
    ".venv",
    "dist",
    "build",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
}
# Pieces stay split so this file does not contain a key header.
_BEGIN = b"BEGIN "
MARKERS = (
    _BEGIN + b"PRIVATE KEY",
    _BEGIN + b"RSA PRIVATE KEY",
    _BEGIN + b"OPENSSH PRIVATE KEY",
)


def main() -> None:
    own = Path(__file__).resolve()
    bad: list[str] = []
    for path in Path(".").rglob("*"):
        if not path.is_file() or SKIP.intersection(path.parts):
            continue
        if path.resolve() == own:
            continue
        blob = path.read_bytes()
        if any(marker in blob for marker in MARKERS):
            bad.append(str(path))
    if bad:
        raise SystemExit("\n".join(bad))


if __name__ == "__main__":
    main()
