import logging

from homeassistant.components import climate
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate import TEMP_CELSIUS

from homeassistant.components.climate.const import (
    # 空调模式: 制冷/制热/送风
    HVAC_MODE_AUTO,
    HVAC_MODE_DRY,
    HVAC_MODE_OFF,
    HVAC_MODE_HEAT, 
    HVAC_MODE_COOL,
    HVAC_MODE_FAN_ONLY,
    HVAC_MODE_HEAT_COOL,

    # 风速
    FAN_ON,
    FAN_OFF,
    FAN_LOW,
    FAN_MEDIUM,
    FAN_HIGH,
    SWING_BOTH,
    SWING_HORIZONTAL,
    SWING_VERTICAL,

    # 吹风模式
    SWING_HORIZONTAL,
    SWING_VERTICAL,
    SWING_BOTH,


    SUPPORT_TARGET_TEMPERATURE,

    SUPPORT_FAN_MODE,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .api import DeoceanEntity


_LOGGER: logging.Logger = logging.getLogger(__package__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    client = hass.data[DOMAIN][entry.entry_id]
    climates = [
        DeoceanClimate(client=client, **climate) for climate in hass.data[DOMAIN].get('airconditioner', [])
    ]
    _LOGGER.debug('found deocean climates(airconditioner): %s', climates)
    async_add_entities(climates)
    return True


class DeoceanClimate(DeoceanEntity, ClimateEntity):

    @property
    def temperature_unit(self):
        return TEMP_CELSIUS

    @property
    def current_temperature(self):
        return float(self._state['current_temperature'])
    
    @property
    def target_temperature(self):
        return float(self._state['target_temperature'])

    @property
    def supported_features(self):
        return SUPPORT_TARGET_TEMPERATURE | SUPPORT_FAN_MODE
 
    @property
    def hvac_mode(self):
        if self._state.get('switch', 'on') == 'off':
            return HVAC_MODE_OFF
        return self._state['mode']
    
    @property
    def hvac_modes(self):
        return [HVAC_MODE_OFF, HVAC_MODE_COOL, HVAC_MODE_HEAT, HVAC_MODE_DRY, 'fan']

    @property
    def fan_mode(self):
        return self._state['fanspeed']

    @property
    def fan_modes(self):
        return [
            FAN_ON,
            FAN_OFF,
            FAN_LOW,
            FAN_MEDIUM,
            FAN_HIGH,
        ]

    def _update(self, new_state):
        self._state.update(new_state or {})
        self._changed = True
        self.async_schedule_update_ha_state(True)

    async def async_set_temperature(self, **kwargs):
        self._update({'target_temperature': kwargs[ATTR_TEMPERATURE]})
        
    async def async_set_hvac_mode(self, hvac_mode):
        self._update({
            'mode': hvac_mode if hvac_mode != HVAC_MODE_FAN_ONLY else 'fan',
            'switch': 'off' if hvac_mode == HVAC_MODE_OFF else 'on'
        })
        
    async def async_set_fan_mode(self, fan_mode):
        self._update({'fanspeed': fan_mode})
