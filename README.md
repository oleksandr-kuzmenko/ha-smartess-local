# SmartESS Local

Local Home Assistant monitoring for **Aninerel / ANENJI and other compatible
SmartESS inverters** with an Eybond Wi-Fi dongle. Read-only, no cloud polling.

Battery readings and mains transitions were checked against an Aninerel / ANENJI
inverter's display. Other models must support the same holding-register protocol.
Tested in code with HA Core **2026.10.0**; installation on HA OS is not yet verified.
Supports one inverter.

## Install

Requires [HACS](https://www.hacs.xyz/docs/use/download/download/).

1. In **HACS → Custom repositories**, add
   `https://github.com/oleksandr-kuzmenko/ha-smartess-local` as an **Integration**.
2. Download **SmartESS Local** and restart Home Assistant.
3. In **Settings → Devices & services → Add integration**, select **SmartESS Local**.
4. Enter the dongle IP and Home Assistant's LAN IP.

The dongle connects back to HA on **TCP 8899**; HA contacts it on **UDP 58899**.
Stop other local clients using the dongle. Do not install another integration
with the same `smartess_local` domain. Change addresses using **Reconfigure**.
The Python library installs automatically; the first installation needs internet access.

## Entities

| Key | Values |
| --- | --- |
| `grid_present` | `on` when input voltage is above 50 V, otherwise `off` |
| `battery_percentage` | Integer, 0–100 % |
| `working_mode` | `power_on`, `standby`, `mains`, `off_grid`, `bypass`, `charging`, `fault` |
| `battery_discharging` | `on` when battery current is below −0.5 A, otherwise `off` |
| `output_power` | Load power, integer W |
| `battery_power` | Integer W; negative = discharge, positive = charge |
| `battery_voltage` | Decimal V |
| `grid_voltage` | Decimal V |

Updates every 10 seconds. Failed reads make entities `unavailable`; the integration
reconnects automatically. The binary sensor thresholds are fixed in this integration.
Mains voltage can return before the inverter switches to `mains`; `off_grid`
alone does not mean the battery is discharging.

Use HA history for graphs and automations for load control. These are instantaneous
measurements, not kWh counters for the Energy dashboard.

## Development

```bash
uv sync
uv run pytest
uv run ruff check custom_components tests
```
