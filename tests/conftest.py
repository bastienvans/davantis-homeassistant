"""Test bootstrap.

The integration's package ``__init__.py`` imports Home Assistant, so importing
``custom_components.davantis.api`` directly would require a full HA install. The
API client itself only depends on ``aiohttp``, so we load it (and the ``const``
module it uses) as a lightweight synthetic ``davantis`` package. This keeps the
API unit tests fast and free of the Home Assistant runtime.
"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

_BASE = Path(__file__).resolve().parents[1] / "custom_components" / "davantis"
_PKG = "davantis"

if _PKG not in sys.modules:
    _pkg = types.ModuleType(_PKG)
    _pkg.__path__ = [str(_BASE)]  # type: ignore[attr-defined]
    sys.modules[_PKG] = _pkg
    # Load const before api so api's ``from .const import ...`` resolves.
    for _name in ("const", "api"):
        _spec = importlib.util.spec_from_file_location(
            f"{_PKG}.{_name}", _BASE / f"{_name}.py"
        )
        assert _spec and _spec.loader
        _mod = importlib.util.module_from_spec(_spec)
        sys.modules[f"{_PKG}.{_name}"] = _mod
        _spec.loader.exec_module(_mod)
