"""Configure the inverter and Home Assistant LAN addresses."""

import ipaddress
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST

from .connection import Connection
from .const import CONF_LOCAL_IP, DOMAIN
from .coordinator import CONNECTION_ERRORS


def ipv4(value: str) -> str:
    try:
        address = ipaddress.IPv4Address(value)
        if address.is_unspecified or address.is_multicast or address.is_loopback:
            raise ValueError
        return str(address)
    except ValueError as exc:
        raise vol.Invalid("Enter a LAN IPv4 address") from exc


class SmartessConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        return await self._async_form("user", user_input)

    async def async_step_reconfigure(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        return await self._async_form("reconfigure", user_input)

    async def _async_form(
        self,
        step: str,
        user_input: dict[str, Any] | None,
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        defaults = self._get_reconfigure_entry().data if step == "reconfigure" else {}
        if user_input is not None:
            defaults = user_input
            try:
                data = {key: ipv4(user_input[key]) for key in (CONF_HOST, CONF_LOCAL_IP)}
            except vol.Invalid, KeyError:
                errors["base"] = "invalid_ip"
            else:
                # The active entry owns the listener; reconfiguration reloads it once.
                if step == "reconfigure":
                    return self.async_update_reload_and_abort(
                        self._get_reconfigure_entry(),
                        data_updates=data,
                    )
                connection = Connection(data[CONF_HOST], data[CONF_LOCAL_IP])
                try:
                    await connection.async_read()
                except CONNECTION_ERRORS:
                    errors["base"] = "cannot_connect"
                else:
                    return self.async_create_entry(title="SmartESS Local", data=data)
                finally:
                    await connection.async_close()
        return self.async_show_form(
            step_id=step,
            errors=errors,
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default=defaults.get(CONF_HOST, "")): str,
                    vol.Required(CONF_LOCAL_IP, default=defaults.get(CONF_LOCAL_IP, "")): str,
                }
            ),
        )
