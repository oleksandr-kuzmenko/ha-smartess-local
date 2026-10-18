import asyncio
from dataclasses import replace

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.helpers import entity_registry as er
from smartess_local.inverter import InverterError


async def setup(hass, entry):
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    registry = er.async_get(hass)
    return {
        entity.unique_id.removeprefix(entry.entry_id + "_"): entity.entity_id
        for entity in er.async_entries_for_config_entry(registry, entry.entry_id)
    }


async def test_entities_distinguish_grid_return_from_battery_discharge(hass, entry, inverter):
    entities = await setup(hass, entry)
    assert len(entities) == 8
    assert hass.states.get(entities["grid_present"]).state == "on"
    assert hass.states.get(entities["battery_discharging"]).state == "on"
    assert hass.states.get(entities["working_mode"]).state == "off_grid"
    assert hass.states.get(entities["battery_percentage"]).state == "96"
    assert hass.states.get(entities["battery_power"]).state == "-2721"
    assert (
        hass.states.get(entities["battery_percentage"]).attributes["state_class"] == "measurement"
    )
    await hass.config_entries.async_unload(entry.entry_id)
    inverter.return_value.__aexit__.assert_awaited_once()


async def test_failed_read_marks_all_entities_unavailable_and_reconnects(hass, entry, inverter):
    entities = await setup(hass, entry)
    coordinator = entry.runtime_data
    inverter.return_value.read.side_effect = TimeoutError()
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert all(hass.states.get(entity).state == "unavailable" for entity in entities.values())
    assert inverter.return_value.__aexit__.await_count == 3
    inverter.return_value.read.side_effect = None
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert inverter.call_count == 4
    assert hass.states.get(entities["battery_percentage"]).state == "96"
    await hass.config_entries.async_unload(entry.entry_id)


async def test_initial_failure_retries_setup_and_closes_client(hass, entry, inverter):
    inverter.return_value.__aenter__.side_effect = TimeoutError()
    assert not await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.SETUP_RETRY
    assert inverter.call_count == 3
    assert inverter.return_value.__aexit__.await_count == 3


async def test_invalid_soc_is_not_published(hass, entry, inverter, snapshot):
    entities = await setup(hass, entry)
    inverter.return_value.read.return_value = replace(snapshot, battery_percentage=65535)
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get(entities["battery_percentage"]).state == "unavailable"
    await hass.config_entries.async_unload(entry.entry_id)


async def test_repeated_reads_reuse_one_connection(hass, entry, inverter):
    await setup(hass, entry)
    await entry.runtime_data.async_refresh()
    assert inverter.call_count == 1
    assert inverter.return_value.read.await_count == 2
    await hass.config_entries.async_unload(entry.entry_id)


async def test_ha_stop_closes_connection(hass, entry, inverter):
    from homeassistant.const import EVENT_HOMEASSISTANT_STOP

    await setup(hass, entry)
    hass.bus.async_fire(EVENT_HOMEASSISTANT_STOP)
    await hass.async_block_till_done()
    inverter.return_value.__aexit__.assert_awaited_once()
    await hass.config_entries.async_unload(entry.entry_id)


async def test_off_grid_without_discharge(hass, entry, inverter, snapshot):
    inverter.return_value.read.return_value = replace(
        snapshot,
        battery_average_current=0,
        battery_power=0,
        grid_voltage=0,
    )
    entities = await setup(hass, entry)
    assert hass.states.get(entities["working_mode"]).state == "off_grid"
    assert hass.states.get(entities["grid_present"]).state == "off"
    assert hass.states.get(entities["battery_discharging"]).state == "off"
    await hass.config_entries.async_unload(entry.entry_id)


async def test_binary_thresholds(hass, entry, inverter, snapshot):
    entities = await setup(hass, entry)
    for volts, amps, grid, discharge in [
        (50.0, -0.5, "off", "off"),
        (50.1, -0.6, "on", "on"),
        (0.0, -0.1, "off", "off"),
        (230.0, 5.0, "on", "off"),
    ]:
        inverter.return_value.read.return_value = replace(
            snapshot,
            grid_voltage=volts,
            battery_average_current=amps,
        )
        await entry.runtime_data.async_refresh()
        await hass.async_block_till_done()
        assert hass.states.get(entities["grid_present"]).state == grid
        assert hass.states.get(entities["battery_discharging"]).state == discharge
    await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.parametrize("failures", [1, 2])
@pytest.mark.parametrize("error", [TimeoutError, InverterError, ValueError])
async def test_transient_failure_recovers_without_unavailable(
    hass, entry, inverter, snapshot, failures, error
):
    entities = await setup(hass, entry)
    inverter.return_value.read.side_effect = [error("bad frame")] * failures + [snapshot]
    observed = []
    unsubscribe = hass.bus.async_listen(
        "state_changed",
        lambda event: observed.append(event.data.get("new_state")),
    )
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    unsubscribe()
    assert inverter.call_count == failures + 1
    assert inverter.return_value.__aexit__.await_count == failures
    assert hass.states.get(entities["battery_percentage"]).state == "96"
    assert not any(
        state and state.entity_id in entities.values() and state.state == "unavailable"
        for state in observed
    )
    await hass.config_entries.async_unload(entry.entry_id)


async def test_cancelled_retry_does_not_open_another_connection(
    hass, entry, inverter, monkeypatch
):
    from custom_components.smartess_local import coordinator

    await setup(hass, entry)
    inverter.return_value.read.side_effect = TimeoutError()
    monkeypatch.setattr(coordinator, "RETRY_DELAY", 3600)
    task = asyncio.create_task(entry.runtime_data._async_update_data())
    for _ in range(20):
        await asyncio.sleep(0)
        if inverter.return_value.__aexit__.await_count:
            break
    assert inverter.return_value.__aexit__.await_count == 1
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert inverter.call_count == 1
    await hass.config_entries.async_unload(entry.entry_id)
