from __future__ import annotations

import sys
from pathlib import Path


def ensure_backend_path() -> Path:
    repo = Path(__file__).resolve().parents[3]
    backend = repo / "backend"
    backend_s = str(backend)
    if backend_s not in sys.path:
        sys.path.insert(0, backend_s)
    return repo


__all__ = ["ensure_backend_path"]
