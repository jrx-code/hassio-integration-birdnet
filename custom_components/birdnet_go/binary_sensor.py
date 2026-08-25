"""Binary sensor entities for BirdNET-Go."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_HOST, DOMAIN
from .coordinator import BirdNetGoCoordinator

STATUS_DESCRIPTION = BinarySensorEntityDescription(
    key="status",
    translation_key="status",
    device_class=BinarySensorDeviceClass.CONNECTIVITY,
    entity_category="diagnostic",
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the BirdNET-Go connectivity binary sensor."""
    coordinator: BirdNetGoCoordinator = entry.runtime_data
    async_add_entities([BirdNetGoStatusSensor(coordinator, entry)])


class BirdNetGoStatusSensor(
    CoordinatorEntity[BirdNetGoCoordinator], BinarySensorEntity
):
    """Reflects whether the last REST/SSE contact with BirdNET-Go succeeded."""

    entity_description = STATUS_DESCRIPTION
    _attr_has_entity_name = True

    def __init__(self, coordinator: BirdNetGoCoordinator, entry: ConfigEntry) -> None:
        """Initialize the connectivity binary sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_status"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="BirdNET-Go",
            manufacturer="tphakala",
            model="Audio Analyzer",
            configuration_url=f"https://{entry.data[CONF_HOST]}",
        )

    @property
    def is_on(self) -> bool:
        """Return True while the last REST/SSE contact with BirdNET-Go succeeded."""
        return bool(self.coordinator.data.get("available"))
