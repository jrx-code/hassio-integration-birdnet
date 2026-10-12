"""The BirdNET-Go integration.

Talks directly to the BirdNET-Go host (REST + SSE) — no MQTT broker, no
manually maintained YAML `rest:` platform sensors.
"""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED, Platform
from homeassistant.core import CoreState, HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import CONF_HOST, CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL, DOMAIN
from .coordinator import BirdNetGoCoordinator
from .frontend import JSModuleRegistration

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.IMAGE, Platform.SENSOR]

# Integration is config-entry only; async_setup only registers the Lovelace card.
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type BirdNetGoConfigEntry = ConfigEntry[BirdNetGoCoordinator]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the bundled Lovelace card once, independent of any entry.

    Done in `async_setup` (called once for the whole integration) rather
    than `async_setup_entry` (called once per config entry) — the card
    only needs registering a single time regardless of how many BirdNET-Go
    hosts are configured.
    """

    async def _register_frontend(_event=None) -> None:
        await JSModuleRegistration(hass).async_register()

    if hass.state is CoreState.running:
        await _register_frontend()
    else:
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _register_frontend)

    return True


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


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate an old config entry.

    v1 -> v2: before the host field accepted an explicit scheme, the
    coordinator always reached BirdNET-Go over HTTPS. Since then a bare
    ``host[:port]`` defaults to ``http://``, so a schemeless host stored by an
    older version would suddenly be probed on port 80 and fail. Pin such
    entries back to ``https://`` to preserve their original behaviour; entries
    that already carry a scheme are left untouched.
    """
    if entry.version > 2:
        # Downgrade from a future schema — nothing sensible we can do.
        return False

    if entry.version == 1:
        host = entry.data.get(CONF_HOST, "")
        new_data = dict(entry.data)
        if host and not host.startswith(("http://", "https://")):
            new_data[CONF_HOST] = f"https://{host}"
            _LOGGER.info(
                "Migrating BirdNET-Go entry host %r to %r (schemeless hosts now "
                "default to http://; pinning pre-v2 entries to https://)",
                host,
                new_data[CONF_HOST],
            )
        hass.config_entries.async_update_entry(entry, data=new_data, version=2)

    return True
