
import logging
from typing import Any
from homeassistant.components.light import LightEntity, COLOR_MODE_ONOFF

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .hub import DeoceanDevice, DeoceanGateway, TypeCode

from .const import DOMAIN
import logging

_LOGGER = logging.getLogger(__package__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> bool:
    hub: DeoceanGateway = hass.data[DOMAIN][entry.entry_id]
    lights = hub.list_devices(TypeCode.LIGHT)
    _LOGGER.debug('发现德能森灯具:%d 颗' % len(lights))
    async_add_entities([DeoceanLight(light) for light in lights])
    return True


class DeoceanLight(LightEntity):
    """德能森灯具"""

    def __init__(self, dev: DeoceanDevice):
        assert dev.type == TypeCode.LIGHT
        self.dev = dev

    async def async_added_to_hass(self) -> None:
        _LOGGER.debug(f'light {self.dev} added')
        self.dev.register_update_callback(self.schedule_update_ha_state)

    @property
    def name(self):
        return self.dev.name

    @property
    def unique_id(self):
        return self.dev.unique_id

    @property
    def color_mode(self):
        return COLOR_MODE_ONOFF

    @property
    def is_on(self) -> bool:
        return self.dev.is_on

    @property
    def supported_color_modes(self) -> set[str]:
        return {COLOR_MODE_ONOFF}

    def turn_on(self, **kwargs: Any) -> None:
        self.dev.turn_on()

    def turn_off(self, **kwargs: Any) -> None:
        return self.dev.turn_off()
