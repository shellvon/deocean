# -*- coding: utf-8 -*-

from homeassistant.components.cover import (
    CoverEntity,
    CoverDeviceClass,
    CoverEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
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

    def open_cover(self, **kwargs) -> None:
        kwargs["position"] = 100
        # 这样可以设置target_pos 从而准确判断是否开启/关闭
        self.set_cover_position(**kwargs)

    def close_cover(self, **kwargs) -> None:
        kwargs["position"] = 0
        self.set_cover_position(**kwargs)

    def set_cover_position(self, **kwargs):
        target_pos = kwargs.get("position")
        self.target_pos = target_pos
        self.dev.set_position(target_pos)
