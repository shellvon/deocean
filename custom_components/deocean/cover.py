# -*- coding: utf-8 -*-

from homeassistant.components.cover import (
    CoverEntity,
    CoverDeviceClass,
    CoverEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, VERSION
from .hub import DeoceanDevice, DeoceanGateway, TypeCode


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> bool:
    hub: DeoceanGateway = hass.data[DOMAIN][entry.entry_id]
    covers = hub.list_devices(TypeCode.COVER)
    async_add_entities([DeoceanCover(cover) for cover in covers])
    return True


class DeoceanCover(CoverEntity):
    """德能森窗帘"""

    _attr_device_class = CoverDeviceClass.CURTAIN

    def __init__(self, dev: DeoceanDevice):
        assert dev.type == TypeCode.COVER
        self.dev = dev
        self.target_pos = None
        self.should_poll = False

    async def async_added_to_hass(self) -> None:
        self.dev.register_update_callback(self._on_device_update)

    def _on_device_update(self, device):
        """设备状态更新回调"""
        # 当设备状态更新时，清除目标位置，避免一直显示opening/closing
        if self.target_pos is not None:
            current_pos = self.current_cover_position
            if current_pos is not None and abs(current_pos - self.target_pos) <= 5:
                self.target_pos = None
        self.schedule_update_ha_state()

    @property
    def name(self):
        return self.dev.name

    @property
    def unique_id(self):
        return self.dev.unique_id

    @property
    def device_info(self):
        """返回设备信息 - 所有窗帘都属于同一个网关设备"""
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
    def supported_features(self):
        return (
            CoverEntityFeature.OPEN
            | CoverEntityFeature.CLOSE
            | CoverEntityFeature.SET_POSITION
        )

    @property
    def current_cover_position(self):
        """返回当前位置,如果设置开关,并不会直接返回position"""
        # 如果有具体位置信息，优先使用位置信息
        if self.dev.position is not None:
            return self.dev.position
        # 否则根据开关状态推断位置
        if self.dev.is_on:
            return 100
        if self.dev.is_close:
            return 0
        return None

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

    async def async_open_cover(self, **kwargs) -> None:
        """异步打开窗帘"""
        kwargs["position"] = 100
        await self.async_set_cover_position(**kwargs)

    async def async_close_cover(self, **kwargs) -> None:
        """异步关闭窗帘"""
        kwargs["position"] = 0
        await self.async_set_cover_position(**kwargs)

    async def async_set_cover_position(self, **kwargs):
        """异步设置窗帘位置"""
        target_pos = kwargs.get("position")
        self.target_pos = target_pos
        await self.hass.async_add_executor_job(self.dev.set_position, target_pos)
