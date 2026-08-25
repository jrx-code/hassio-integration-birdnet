"""Load `birdnet_go.parsing` (and its `.const` import) without touching
`birdnet_go/__init__.py` — that file imports `homeassistant`, which isn't
(and shouldn't need to be) a dependency of these tests. `parsing.py` is
deliberately pure Python; this is what makes testing it without the full
`homeassistant` package/test harness possible.

Registers a bare namespace module for `birdnet_go` pointing at
`custom_components/birdnet_go/`, so the package's relative imports
(`from .const import ...`) resolve normally via Python's own import
machinery — without ever importing the real `__init__.py`.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

_COMPONENT_DIR = Path(__file__).parent.parent / "custom_components" / "birdnet_go"

if "birdnet_go" not in sys.modules:
    _pkg = types.ModuleType("birdnet_go")
    _pkg.__path__ = [str(_COMPONENT_DIR)]
    sys.modules["birdnet_go"] = _pkg
