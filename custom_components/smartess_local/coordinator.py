"""Poll all inverter readings together."""

import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from smartess_local.inverter import InverterError
from smartess_local.state import InverterState

from .connection import Connection
from .const import CONF_LOCAL_IP, DOMAIN, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)
CONNECTION_ERRORS = (InverterError, OSError, asyncio.IncompleteReadError, ValueError)
READ_ATTEMPTS = 3
RETRY_DELAY = 2


class SmartessCoordinator(DataUpdateCoordinator[InverterState]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass, _LOGGER, name=DOMAIN, config_entry=entry, update_interval=UPDATE_INTERVAL
        )
        self.connection = Connection(entry.data[CONF_HOST], entry.data[CONF_LOCAL_IP])

    async def _async_update_data(self) -> InverterState:
        for attempt in range(1, READ_ATTEMPTS + 1):
            try:
                return await self.connection.async_read()
            except CONNECTION_ERRORS as exc:
                if attempt == READ_ATTEMPTS:
                    raise UpdateFailed(f"{type(exc).__name__}: {exc}") from exc
                _LOGGER.debug(
                    "Inverter read failed (%s/%s), retrying: %s: %s",
                    attempt,
                    READ_ATTEMPTS,
                    type(exc).__name__,
                    exc,
                )
                await asyncio.sleep(RETRY_DELAY)
        raise AssertionError("No inverter read attempted")

    async def async_shutdown(self) -> None:
        await super().async_shutdown()
        await self.connection.async_close()
