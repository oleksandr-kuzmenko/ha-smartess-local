"""SmartESS Local integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP, Platform
from homeassistant.core import Event, HomeAssistant

from .coordinator import SmartessCoordinator

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR]
type SmartessConfigEntry = ConfigEntry[SmartessCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: SmartessConfigEntry) -> bool:
    coordinator = SmartessCoordinator(hass, entry)
    try:
        await coordinator.async_config_entry_first_refresh()
        entry.runtime_data = coordinator
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    except BaseException:
        await coordinator.async_shutdown()
        raise

    async def async_stop(event: Event) -> None:
        await coordinator.async_shutdown()

    entry.async_on_unload(hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, async_stop))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: SmartessConfigEntry) -> bool:
    if await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        await entry.runtime_data.async_shutdown()
        return True
    return False
