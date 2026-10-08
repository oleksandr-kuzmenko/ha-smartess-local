from homeassistant.data_entry_flow import FlowResultType


async def test_user_flow_checks_connection(hass, inverter):
    result = await hass.config_entries.flow.async_init("smartess_local", context={"source": "user"})
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"host": "192.168.3.100", "local_ip": "192.168.1.67"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert inverter.return_value.read.await_count >= 1
    for entry in hass.config_entries.async_entries("smartess_local"):
        await hass.config_entries.async_unload(entry.entry_id)


async def test_unreachable_inverter_stays_in_form(hass, inverter):
    inverter.return_value.read.side_effect = TimeoutError()
    result = await hass.config_entries.flow.async_init(
        "smartess_local",
        context={"source": "user"},
        data={"host": "192.168.3.100", "local_ip": "192.168.1.67"},
    )
    assert result["errors"] == {"base": "cannot_connect"}
    inverter.return_value.__aexit__.assert_awaited_once()


async def test_duplicate_entry_is_rejected(hass, entry, inverter):
    result = await hass.config_entries.flow.async_init("smartess_local", context={"source": "user"})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"
    inverter.assert_not_called()


async def test_reconfigure_preserves_entity_ids(hass, entry, inverter):
    from homeassistant.helpers import entity_registry as er

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    registry = er.async_get(hass)
    before = {
        entity.entity_id for entity in er.async_entries_for_config_entry(registry, entry.entry_id)
    }
    result = await hass.config_entries.flow.async_init(
        "smartess_local",
        context={
            "source": "reconfigure",
            "entry_id": entry.entry_id,
        },
        data={"host": "192.168.3.101", "local_ip": "192.168.1.68"},
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    await hass.async_block_till_done()
    assert entry.data["host"] == "192.168.3.101"
    assert entry.state.name == "LOADED"
    assert before == {
        entity.entity_id for entity in er.async_entries_for_config_entry(registry, entry.entry_id)
    }
    await hass.config_entries.async_unload(entry.entry_id)


async def test_invalid_address_does_not_open_connection(hass, inverter):
    result = await hass.config_entries.flow.async_init(
        "smartess_local",
        context={"source": "user"},
        data={"host": "0.0.0.0", "local_ip": "bad-address"},
    )
    assert result["errors"] == {"base": "invalid_ip"}
    inverter.assert_not_called()
