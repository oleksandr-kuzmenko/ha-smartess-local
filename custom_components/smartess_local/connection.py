"""Own one library connection and discard it after a failed read."""

import asyncio

from smartess_local import Inverter
from smartess_local.state import InverterState

from .const import REQUEST_TIMEOUT


class Connection:
    def __init__(self, host: str, local_ip: str) -> None:
        self.host = host
        self.local_ip = local_ip
        self._client: Inverter | None = None

    async def async_read(self) -> InverterState:
        try:
            async with asyncio.timeout(REQUEST_TIMEOUT):
                if self._client is None:
                    self._client = Inverter(
                        inverter_ip=self.host,
                        local_ip=self.local_ip,
                        timeout=5,
                    )
                    await self._client.__aenter__()
                state = await self._client.read()
                if not 0 <= state.battery_percentage <= 100:
                    raise ValueError("Battery percentage is outside 0..100")
                return state
        except BaseException:
            await self.async_close()
            raise

    async def async_close(self) -> None:
        client, self._client = self._client, None
        if client is not None:
            await client.__aexit__(None, None, None)
