"""Grid voltage presence and measured battery discharge."""

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import SmartessConfigEntry
from .entity import SmartessEntity

SENSORS = (
    BinarySensorEntityDescription(
        key="grid_present",
        translation_key="grid_present",
        device_class=BinarySensorDeviceClass.POWER,
    ),
    BinarySensorEntityDescription(
        key="battery_discharging",
        translation_key="battery_discharging",
        icon="mdi:battery-arrow-down",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SmartessConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities(SmartessBinarySensor(entry, description) for description in SENSORS)


class SmartessBinarySensor(SmartessEntity, BinarySensorEntity):
    def __init__(
        self, entry: SmartessConfigEntry, description: BinarySensorEntityDescription
    ) -> None:
        super().__init__(entry, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool:
        state = self.coordinator.data
        if self.entity_description.key == "grid_present":
            return state.grid_voltage > 50
        return state.battery_average_current < -0.5
