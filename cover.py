'''
Author: tiany
Date: 2021-10-13 22:57:07
LastEditors: tiany
LastEditTime: 2021-10-15 00:40:00
Description: 
'''


import logging
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.cover import CoverEntity, ATTR_POSITION, SUPPORT_OPEN , SUPPORT_CLOSE , SUPPORT_SET_POSITION


from .const import DOMAIN
from .api import DeoceanEntity

_LOGGER: logging.Logger = logging.getLogger(__package__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    client = hass.data[DOMAIN][entry.entry_id]
    covers = [
        DeoceanCover(client=client, **cover) for cover in hass.data[DOMAIN].get('blind', [])
    ]
    _LOGGER.debug('found deocean blinds(covers): %s', covers)
    async_add_entities(covers)
    return True


class DeoceanCover(DeoceanEntity, CoverEntity):

    @property
    def supported_features(self):
        return SUPPORT_OPEN | SUPPORT_CLOSE | SUPPORT_SET_POSITION

    @property
    def current_cover_position(self):
        return self._state[ATTR_POSITION]
    
    @property
    def is_closed(self):
        return self._state[ATTR_POSITION] == 100

    async def async_open_cover(self, **kwargs):
        self._attr_is_opening = True
        self._state[ATTR_POSITION] = 0
        await self._client.async_send_action(self._id, {
            ATTR_POSITION: 0
        })
        self._attr_is_opening = False

    async def async_close_cover(self, **kwargs):
        self._attr_is_closing = True
        self._state[ATTR_POSITION] = 100
        await self._client.async_send_action(self._id, {
            ATTR_POSITION: 100
        })
        self._attr_is_closing = False
    
    async def async_set_cover_position(self, **kwargs):
        _LOGGER.debug('德能森窗帘控制:%s -> %s', self._state, kwargs)
        is_closing = kwargs[ATTR_POSITION] > self.current_cover_position
        if is_closing:
            self._attr_is_closing = True
        else:
            self._attr_is_opening = True
        self._state[ATTR_POSITION] = kwargs[ATTR_POSITION]
        await self._client.async_send_action(self._id, {
            ATTR_POSITION: kwargs[ATTR_POSITION]
        })
        if is_closing:
            self._attr_is_closing = False
        else:
            self._attr_is_opening = False

