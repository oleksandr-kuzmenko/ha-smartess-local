from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from smartess_local.registers import REGISTERS_201_234
from smartess_local.state import InverterState

from custom_components.smartess_local import connection


@pytest.fixture(autouse=True)
def custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture
def snapshot():
    values = {reg.name: 0 for reg in REGISTERS_201_234 if reg.name is not None}
    values.update(
        working_mode=3,
        battery_percentage=96,
        battery_voltage=48.6,
        battery_average_current=-56.0,
        battery_power=-2721,
        output_power=2544,
        grid_voltage=229.4,
        grid_frequency=50.02,
    )
    return InverterState.from_registers(values, timestamp=datetime.now(UTC))


@pytest.fixture
def inverter(snapshot):
    with patch.object(connection, "Inverter") as factory:
        client = factory.return_value
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock()
        client.read = AsyncMock(return_value=snapshot)
        yield factory


@pytest.fixture
def entry(hass):
    entry = MockConfigEntry(
        domain="smartess_local",
        title="SmartESS Local",
        data={"host": "192.168.3.100", "local_ip": "192.168.1.67"},
    )
    entry.add_to_hass(hass)
    return entry
