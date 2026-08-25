"""Image entities for BirdNET-Go.

Uses HA's `image` platform instead of a plain URL-string sensor. HA fetches
and caches the picture itself (`ImageEntity.async_image`) and serves it back
through its own `/api/image_proxy/...` endpoint — so the picture stays
reachable from the Lovelace UI even when the browser viewing it has no direct
network path to the BirdNET-Go host (e.g. remote access through HA's own
proxy/URL, where the BirdNET-Go host is LAN-only).

`image_url`/`image_last_updated` are plain `@property` (not `_attr_*`) —
`ImageEntity` backs those with `cached_property`, which only evaluates once;
reading straight from `coordinator.data` on every access is the documented
pattern for a coordinator-backed image entity.
"""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.image import ImageEntity, ImageEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import CONF_HOST, CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL, DOMAIN
from .coordinator import BirdNetGoCoordinator

IMAGE_DESCRIPTIONS: tuple[ImageEntityDescription, ...] = (
    ImageEntityDescription(
        key="last_detection_image",
        translation_key="last_detection_image",
    ),
    ImageEntityDescription(
        key="top_species_thumbnail",
        translation_key="top_species_thumbnail",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up BirdNET-Go image entities from a config entry."""
    coordinator: BirdNetGoCoordinator = entry.runtime_data
    async_add_entities(
        BirdNetGoImage(hass, coordinator, entry, description)
        for description in IMAGE_DESCRIPTIONS
    )


class BirdNetGoImage(CoordinatorEntity[BirdNetGoCoordinator], ImageEntity):
    """A picture sourced from a BirdNET-Go detection, proxied through HA."""

    entity_description: ImageEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: BirdNetGoCoordinator,
        entry: ConfigEntry,
        description: ImageEntityDescription,
    ) -> None:
        CoordinatorEntity.__init__(self, coordinator)
        ImageEntity.__init__(
            self,
            hass,
            verify_ssl=entry.data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL),
        )
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="BirdNET-Go",
            manufacturer="tphakala",
            model="Audio Analyzer",
            configuration_url=f"https://{entry.data[CONF_HOST]}",
        )
        self._last_url: str | None = self._current_url()
        self._last_updated: datetime | None = (
            dt_util.utcnow() if self._last_url else None
        )

    def _current_url(self) -> str | None:
        return self.coordinator.data.get(self.entity_description.key)

    @property
    def image_url(self) -> str | None:
        return self._last_url

    @property
    def image_last_updated(self) -> datetime | None:
        return self._last_updated

    @callback
    def _handle_coordinator_update(self) -> None:
        url = self._current_url()
        if url != self._last_url:
            self._last_url = url
            self._last_updated = dt_util.utcnow()
            self._cached_image = None  # force re-fetch of image bytes
            self.async_update_token()
        super()._handle_coordinator_update()
