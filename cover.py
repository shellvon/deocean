
from typing import Any
from homeassistant.components.cover import CoverEntity, ATTR_POSITION, SUPPORT_OPEN, SUPPORT_CLOSE, SUPPORT_SET_POSITION
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .hub import DeoceanDevice, DeoceanGateway, TypeCode

from .const import DOMAIN
import logging

_LOGGER = logging.getLogger(__package__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> bool:
    hub: DeoceanGateway = hass.data[DOMAIN][entry.entry_id]
    covers = hub.list_devices(TypeCode.COVER)
    _LOGGER.warning('发现德能森窗帘:%d 副' % len(covers))
    async_add_entities([DeoceanCover(cover) for cover in covers])
    return True


class DeoceanCover(CoverEntity):
    """德能森窗帘"""

    def __init__(self, dev: DeoceanDevice):
        assert dev.type == TypeCode.COVER
        self.dev = dev

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
        return self.dev.position or 0

    @property
    def is_closed(self):
        return self.current_cover_position == 0

    def open_cover(self, **kwargs: Any) -> None:
        return self.dev.turn_on()

    def close_cover(self, **kwargs: Any) -> None:
        return self.dev.turn_off()

    def set_cover_position(self, **kwargs):
        self.dev.set_position(kwargs.get(ATTR_POSITION))
