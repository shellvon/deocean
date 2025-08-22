# -*- coding: utf-8 -*-

from homeassistant.components.light import LightEntity, ColorMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, VERSION
from .hub import DeoceanDevice, DeoceanGateway, TypeCode


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> bool:
    hub: DeoceanGateway = hass.data[DOMAIN][entry.entry_id]
    lights = hub.list_devices(TypeCode.LIGHT)
    async_add_entities([DeoceanLight(light) for light in lights])
    return True


class DeoceanLight(LightEntity):
    """德能森灯具"""

    def __init__(self, dev: DeoceanDevice):
        assert dev.type == TypeCode.LIGHT
        self.dev = dev
        self.should_poll = False

    async def async_added_to_hass(self) -> None:
        self.dev.register_update_callback(self.schedule_update_ha_state)

    @property
    def name(self):
        return self.dev.name

    @property
    def unique_id(self):
        return self.dev.unique_id

    @property
    def device_info(self):
        """返回设备信息 - 所有灯具都属于同一个网关设备"""
        return {
            "identifiers": {(DOMAIN, f"gateway_{self.dev.gw.ip_addr}")},
            "name": f"德能森网关 ({self.dev.gw.ip_addr})",
            "manufacturer": "德能森",
            "model": "智能网关",
            "sw_version": VERSION,
        }

    @property
    def available(self) -> bool:
        """设备是否可用"""
        return self.dev.gw._listening

    @property
    def color_mode(self):
        """德能森控制的只支持开、关"""
        return ColorMode.ONOFF

    @property
    def is_on(self) -> bool:
        return self.dev.is_on

    @property
    def supported_color_modes(self) -> set[str]:
        return {ColorMode.ONOFF}

    async def async_turn_on(self, **kwargs) -> None:
        """异步打开灯具"""
        await self.hass.async_add_executor_job(self.dev.turn_on)

    async def async_turn_off(self, **kwargs) -> None:
        """异步关闭灯具"""
        await self.hass.async_add_executor_job(self.dev.turn_off)
