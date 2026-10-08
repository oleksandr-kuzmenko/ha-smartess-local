import asyncio
from unittest.mock import AsyncMock

import pytest

from custom_components.smartess_local.connection import Connection


async def test_cancelled_handshake_closes_resources(inverter):
    started = asyncio.Event()

    async def connect():
        started.set()
        await asyncio.Event().wait()

    inverter.return_value.__aenter__ = AsyncMock(side_effect=connect)
    connection = Connection("192.168.3.100", "192.168.1.67")
    task = asyncio.create_task(connection.async_read())
    await asyncio.wait_for(started.wait(), 1)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    inverter.return_value.__aexit__.assert_awaited_once()
    await connection.async_close()
    inverter.return_value.__aexit__.assert_awaited_once()
