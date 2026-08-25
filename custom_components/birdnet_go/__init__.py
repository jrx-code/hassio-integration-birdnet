"""The BirdNET-Go integration.

Talks directly to the BirdNET-Go host (REST + SSE) — no MQTT broker, no
manually maintained YAML `rest:` platform sensors.
"""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_HOST, CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL
from .coordinator import BirdNetGoCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.SENSOR]

type BirdNetGoConfigEntry = ConfigEntry[BirdNetGoCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: BirdNetGoConfigEntry) -> bool:
    """Set up BirdNET-Go from a config entry."""
    coordinator = BirdNetGoCoordinator(
        hass,
        host=entry.data[CONF_HOST],
        verify_ssl=entry.data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL),
    )
    await coordinator.async_config_entry_first_refresh()
    coordinator.start_sse()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: BirdNetGoConfigEntry) -> bool:
    """Unload a config entry."""
    await entry.runtime_data.stop_sse()
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
