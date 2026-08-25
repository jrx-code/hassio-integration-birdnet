"""Sensor entities for BirdNET-Go."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_HOST, DOMAIN
from .coordinator import BirdNetGoCoordinator


@dataclass(frozen=True, kw_only=True)
class BirdNetGoSensorDescription(SensorEntityDescription):
    """Describes a BirdNET-Go sensor backed by a coordinator.data key."""

    value_fn: Callable[[dict], object] = lambda data: None


SENSOR_DESCRIPTIONS: tuple[BirdNetGoSensorDescription, ...] = (
    BirdNetGoSensorDescription(
        key="last_detection",
        translation_key="last_detection",
        icon="mdi:bird",
        value_fn=lambda d: d.get("last_detection"),
    ),
    BirdNetGoSensorDescription(
        key="last_detection_scientific",
        translation_key="last_detection_scientific",
        icon="mdi:format-quote-close",
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.get("last_detection_scientific"),
    ),
    BirdNetGoSensorDescription(
        key="last_detection_time",
        translation_key="last_detection_time",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda d: d.get("last_detection_time"),
    ),
    BirdNetGoSensorDescription(
        key="last_detection_confidence",
        translation_key="last_detection_confidence",
        native_unit_of_measurement="%",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:percent",
        value_fn=lambda d: d.get("last_detection_confidence"),
    ),
    BirdNetGoSensorDescription(
        key="last_detection_image",
        translation_key="last_detection_image",
        icon="mdi:image",
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.get("last_detection_image"),
    ),
    BirdNetGoSensorDescription(
        key="detections_today",
        translation_key="detections_today",
        native_unit_of_measurement="detections",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:counter",
        value_fn=lambda d: d.get("detections_today"),
    ),
    BirdNetGoSensorDescription(
        key="species_today",
        translation_key="species_today",
        native_unit_of_measurement="species",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:format-list-numbered",
        value_fn=lambda d: d.get("species_today"),
    ),
    BirdNetGoSensorDescription(
        key="top_species",
        translation_key="top_species",
        icon="mdi:trophy-variant",
        value_fn=lambda d: d.get("top_species"),
    ),
    BirdNetGoSensorDescription(
        key="top_species_scientific",
        translation_key="top_species_scientific",
        icon="mdi:format-quote-close",
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.get("top_species_scientific"),
    ),
    BirdNetGoSensorDescription(
        key="top_species_count",
        translation_key="top_species_count",
        native_unit_of_measurement="detections",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:counter",
        value_fn=lambda d: d.get("top_species_count"),
    ),
    BirdNetGoSensorDescription(
        key="top_species_thumbnail",
        translation_key="top_species_thumbnail",
        icon="mdi:image",
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.get("top_species_thumbnail"),
    ),
    BirdNetGoSensorDescription(
        key="total_species",
        translation_key="total_species",
        native_unit_of_measurement="species",
        icon="mdi:owl",
        value_fn=lambda d: d.get("total_species"),
    ),
    BirdNetGoSensorDescription(
        key="total_detections",
        translation_key="total_detections",
        native_unit_of_measurement="detections",
        icon="mdi:counter",
        value_fn=lambda d: d.get("total_detections"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up BirdNET-Go sensors from a config entry."""
    coordinator: BirdNetGoCoordinator = entry.runtime_data
    async_add_entities(
        BirdNetGoSensor(coordinator, entry, description)
        for description in SENSOR_DESCRIPTIONS
    )


class BirdNetGoSensor(CoordinatorEntity[BirdNetGoCoordinator], SensorEntity):
    """A single BirdNET-Go stat/detection sensor."""

    entity_description: BirdNetGoSensorDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: BirdNetGoCoordinator,
        entry: ConfigEntry,
        description: BirdNetGoSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="BirdNET-Go",
            manufacturer="tphakala",
            model="Audio Analyzer",
            configuration_url=f"https://{entry.data[CONF_HOST]}",
        )

    @property
    def native_value(self):
        return self.entity_description.value_fn(self.coordinator.data)
