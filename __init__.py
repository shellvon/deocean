from typing import Dict, Any
from datetime import timedelta
from .const import DOMAIN

import logging
import voluptuous as vol
from homeassistant.core import HomeAssistant, callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import config_validation as cv, entity
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.const import CONF_HOST

from .api import DeoceanAPI

_LOGGER: logging.Logger  = logging.getLogger(__package__)

PLATFORMS = ['light', 'climate', 'cover']

SCAN_INTERVAL = timedelta(minutes=10)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_HOST): cv.string
            }
        )
    },
    extra=vol.ALLOW_EXTRA
)


async def async_setup_devices(hass: HomeAssistant, deoceanAPI: DeoceanAPI):
    devices = {}
    for device in await deoceanAPI.async_discovery_devices():
        devices.setdefault(device['deviceType'], []).append(device)
    hass.data[DOMAIN].update(devices)
    
async def async_setup(hass: HomeAssistant, config: Dict[str, Any]):
    hass.data[DOMAIN] = {}
    if DOMAIN not in config:
        return True
    await async_setup_devices(hass, DeoceanAPI(f'http://{config[DOMAIN].get(CONF_HOST)}', async_get_clientsession(hass, False)))
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    deoceanAPI = DeoceanAPI(f'http://{entry.data.get(CONF_HOST)}', async_get_clientsession(hass, False))
    hass.data[DOMAIN][entry.entry_id] = deoceanAPI
    await async_setup_devices(hass, deoceanAPI)
    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )
    return True
