'''
Author: tiany
Date: 2021-10-13 22:23:04
LastEditors: tiany
LastEditTime: 2021-10-15 00:24:59
Description: 
'''

import logging
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.light import LightEntity, COLOR_MODE_BRIGHTNESS, COLOR_MODE_ONOFF

from .const import DOMAIN
from .api import DeoceanEntity

_LOGGER: logging.Logger = logging.getLogger(__package__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    client = hass.data[DOMAIN][entry.entry_id]
    lights = [
        DeoceanLight(client=client, **light) for light in hass.data[DOMAIN].get('light', [])
    ]
    _LOGGER.debug('found deocean lights: %s', lights)
    async_add_entities(lights)
    return True


class DeoceanLight(DeoceanEntity, LightEntity):

    @property
    def supported_color_modes(self):
        return {COLOR_MODE_ONOFF, COLOR_MODE_BRIGHTNESS}
    @property
    def color_mode(self):
        return COLOR_MODE_ONOFF

    async def async_turn_on(self, **kwargs):
        self._state.update(
            {
                'switch': 'on',
                'brightness': int(kwargs.get('brightness', 100))
            }
        )
        self._changed = True
        self.async_schedule_update_ha_state(True)
        

    async def async_turn_off(self, **kwargs):
        self._state['switch'] = 'off'
        self._changed = True
        self.async_schedule_update_ha_state(True)
        
