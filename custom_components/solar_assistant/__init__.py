"""SolarAssistant — Home Assistant integration entry points."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import (
    AUTH_MODBUS,
    CONF_AUTH_METHOD,
    CONF_ENABLED_TOPICS,
    DOMAIN,
)
from .coordinator import SolarAssistantCoordinator
from .modbus_coordinator import ModbusCoordinator

PLATFORMS = ["binary_sensor", "number", "select", "sensor", "switch"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    auth_method = entry.data.get(CONF_AUTH_METHOD)
    
    if auth_method == AUTH_MODBUS:
        coordinator = ModbusCoordinator(hass, entry.data)
        await coordinator.async_refresh()
    else:
        coordinator = SolarAssistantCoordinator(hass, entry)
        await coordinator.async_start()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        coordinator = hass.data[DOMAIN].pop(entry.entry_id)
        auth_method = entry.data.get(CONF_AUTH_METHOD)
        
        if auth_method == AUTH_MODBUS:
            await coordinator.async_stop()
        else:
            await coordinator.async_stop()
    return unloaded


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Drop sensors that fall outside the new enabled-topic selection, then reload the entry.

    Only read-only sensor entities are governed by the topic selection. The
    settings platforms (number/select/switch) and the connection binary_sensor
    are always created by their own platforms, so they are left untouched.
    """
    if entry.options.get(CONF_ENABLED_TOPICS) is not None:
        registry = er.async_get(hass)
        coordinator: SolarAssistantCoordinator = hass.data[DOMAIN][entry.entry_id]
        prefix = f"{entry.unique_id}_"
        for ent in list(er.async_entries_for_config_entry(registry, entry.entry_id)):
            if ent.domain != "sensor" or not ent.unique_id.startswith(prefix):
                continue
            topic = ent.unique_id[len(prefix):]
            if not coordinator.should_create_sensor(topic):
                registry.async_remove(ent.entity_id)
    await hass.config_entries.async_reload(entry.entry_id)
