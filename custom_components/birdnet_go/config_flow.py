"""Config flow for BirdNET-Go integration."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol
from aiohttp import ClientTimeout

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    API_PATH_RECENT,
    CONF_HOST,
    CONF_VERIFY_SSL,
    DEFAULT_HOST,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
    REST_TIMEOUT,
)

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
        vol.Optional(CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL): bool,
    }
)


async def _test_connection(hass, host: str, verify_ssl: bool) -> str | None:
    """Probe the BirdNET-Go API. Returns an error key or None on success."""
    session = async_get_clientsession(hass, verify_ssl=verify_ssl)
    try:
        async with session.get(
            f"https://{host}{API_PATH_RECENT}",
            params={"limit": 1},
            timeout=ClientTimeout(total=REST_TIMEOUT),
        ) as resp:
            if resp.status != 200:
                return "cannot_connect"
            await resp.json()
    except aiohttp.ClientConnectorCertificateError:
        return "ssl_error"
    except (aiohttp.ClientError, TimeoutError):
        return "cannot_connect"
    except Exception:  # noqa: BLE001
        _LOGGER.exception("Unexpected error probing BirdNET-Go")
        return "unknown"
    return None


class BirdNetGoConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for BirdNET-Go."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            verify_ssl = user_input[CONF_VERIFY_SSL]

            await self.async_set_unique_id(host)
            self._abort_if_unique_id_configured()

            error = await _test_connection(self.hass, host, verify_ssl)
            if error is None:
                return self.async_create_entry(
                    title=f"BirdNET-Go ({host})",
                    data={CONF_HOST: host, CONF_VERIFY_SSL: verify_ssl},
                )
            errors["base"] = error

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )
