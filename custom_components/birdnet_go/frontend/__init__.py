"""Auto-register the bundled `birdnet-go-card` as a Lovelace resource.

No manual "add resource" step for the user — this is the documented
community pattern for shipping a card together with its integration
(register a static path for the JS file, then add/refresh a storage-mode
Lovelace resource entry pointing at it). Only works with Lovelace in
storage mode; YAML-mode dashboards still need the resource added by hand.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_call_later

from custom_components.birdnet_go.const import FRONTEND_JS_MODULES, FRONTEND_URL_BASE

_LOGGER = logging.getLogger(__name__)


class JSModuleRegistration:
    """Registers the integration's Lovelace card JS module."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the registrar (Lovelace data is fetched on demand)."""
        self.hass = hass
        self.lovelace = None

    async def async_register(self) -> None:
        """Register the static path and, in storage mode, the resource."""
        await self._async_register_path()
        # Fetched here, not cached at __init__ time — hass.data["lovelace"]
        # may not exist yet when the registrar is constructed.
        self.lovelace = self.hass.data.get("lovelace")
        # LovelaceData's field is `resource_mode`, not `mode` — confirmed
        # against homeassistant/components/lovelace/__init__.py. Guessing
        # "mode" here silently skipped resource registration on 2026-08-26
        # (getattr fell through to None every time, no error logged).
        mode = getattr(self.lovelace, "resource_mode", None)
        if mode == "storage":
            await self._async_wait_for_lovelace_resources()
        else:
            _LOGGER.debug(
                "Lovelace is not in storage mode (resource_mode=%s) — add "
                "the %s/%s resource by hand",
                mode,
                FRONTEND_URL_BASE,
                FRONTEND_JS_MODULES[0]["filename"],
            )

    async def _async_register_path(self) -> None:
        """Serve custom_components/birdnet_go/frontend/ at FRONTEND_URL_BASE."""
        try:
            await self.hass.http.async_register_static_paths(
                [StaticPathConfig(FRONTEND_URL_BASE, str(Path(__file__).parent), False)]
            )
            _LOGGER.debug("Registered static path %s", FRONTEND_URL_BASE)
        except RuntimeError:
            # Already registered (e.g. config entry reload) — not an error.
            _LOGGER.debug("Static path %s already registered", FRONTEND_URL_BASE)

    async def _async_wait_for_lovelace_resources(self) -> None:
        """Storage-mode resources load asynchronously; poll until ready."""

        async def _check_loaded(_now: Any) -> None:
            if self.lovelace.resources.loaded:
                await self._async_register_modules()
            else:
                async_call_later(self.hass, 5, _check_loaded)

        await _check_loaded(None)

    async def _async_register_modules(self) -> None:
        """Create or version-bump this integration's Lovelace resources."""
        existing = [
            r
            for r in self.lovelace.resources.async_items()
            if r["url"].startswith(FRONTEND_URL_BASE)
        ]

        for module in FRONTEND_JS_MODULES:
            url = f"{FRONTEND_URL_BASE}/{module['filename']}"
            match = next((r for r in existing if r["url"].split("?")[0] == url), None)

            if match is None:
                _LOGGER.info("Registering %s v%s", module["name"], module["version"])
                await self.lovelace.resources.async_create_item(
                    {"res_type": "module", "url": f"{url}?v={module['version']}"}
                )
                continue

            current_version = (
                match["url"].split("?v=")[-1] if "?v=" in match["url"] else "0"
            )
            if current_version != module["version"]:
                _LOGGER.info(
                    "Updating %s: v%s -> v%s",
                    module["name"],
                    current_version,
                    module["version"],
                )
                await self.lovelace.resources.async_update_item(
                    match["id"],
                    {"res_type": "module", "url": f"{url}?v={module['version']}"},
                )
