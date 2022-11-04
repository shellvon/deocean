
# -*- coding: utf-8 -*-

from typing import Any
from homeassistant.components.cover import CoverEntity, DEVICE_CLASS_CURTAIN, ATTR_POSITION, SUPPORT_OPEN, SUPPORT_CLOSE, SUPPORT_SET_POSITION
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .hub import DeoceanDevice, DeoceanGateway, TypeCode

from .const import DOMAIN
import logging

_LOGGER = logging.getLogger(__package__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> bool:
    hub: DeoceanGateway = hass.data[DOMAIN][entry.entry_id]
    covers = hub.list_devices(TypeCode.COVER)
    _LOGGER.debug('发现德能森窗帘:%d 副' % len(covers))
    async_add_entities([DeoceanCover(cover) for cover in covers])
    return True


class DeoceanCover(CoverEntity):
    """德能森窗帘"""

    def __init__(self, dev: DeoceanDevice):
        assert dev.type == TypeCode.COVER
        self.dev = dev
        self._attr_device_class = DEVICE_CLASS_CURTAIN
        self.target_pos = None

    def added_to_hass(self) -> None:
        _LOGGER.debug(f'cover {self.dev} added')
        self.dev.register_update_callback(self.schedule_update_ha_state)

    @property
    def name(self):
        return self.dev.name

    @property
    def unique_id(self):
        return self.dev.unique_id

    @property
    def supported_features(self):
        return SUPPORT_OPEN | SUPPORT_CLOSE | SUPPORT_SET_POSITION

    @property
    def current_cover_position(self):
        """返回当前位置,如果设置开关,并不会直接返回position"""
        if self.dev.is_on:
            return 100
        if self.dev.is_close:
            return 0
        return self.dev.position

    @property
    def is_closed(self):
        return self.current_cover_position == 0

    @property
    def is_opening(self):
        if self.target_pos is None or self.current_cover_position is None:
            return None
        return self.target_pos > self.current_cover_position

    @property
    def is_closing(self):
        if self.target_pos is None or self.current_cover_position is None:
            return None
        return self.target_pos < self.current_cover_position

    def open_cover(self, **kwargs: Any) -> None:
        kwargs[ATTR_POSITION] = 100
        # 这样可以设置target_pos 从而准确判断是否开启/关闭
        self.set_cover_position(**kwargs)

    def close_cover(self, **kwargs: Any) -> None:
        kwargs[ATTR_POSITION] = 0
        self.set_cover_position(**kwargs)

    def set_cover_position(self, **kwargs):
        target_pos = kwargs.get(ATTR_POSITION)
        self.target_pos = target_pos
        self.dev.set_position(target_pos)
