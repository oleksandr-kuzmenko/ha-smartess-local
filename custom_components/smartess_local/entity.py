"""Common device metadata and coordinator availability."""

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import SmartessConfigEntry
from .const import DOMAIN
from .coordinator import SmartessCoordinator


class SmartessEntity(CoordinatorEntity[SmartessCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, entry: SmartessConfigEntry, key: str) -> None:
        super().__init__(entry.runtime_data)
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
        )
