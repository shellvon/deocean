# -*- coding: utf-8 -*-

"""替换掉德能森的Ebelong网关流程

目前本小区使用的网关一共就俩个
    A. 中弘 HVAC 用来控制中央空调
    B. Ebelong 用来控制家里灯具/窗帘
由于Hass已经内置了Zhonghong HVAC，所以不用自己写了，这里重点替换 B，但因为缺少文档，
所以大多是猜测模拟的。不保证所有功能都可用。

"""
import socket
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from .hub import DeoceanGateway, register_devices, register_scenes
from .const import BUILTIN_DEVICES_STR, DOMAIN, BUILTIN_SCENE_STR

PLATFORMS = ['light', 'cover']

_LOGGER = logging.getLogger(__package__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hub = DeoceanGateway(entry.data[CONF_HOST],
                         entry.data.get(CONF_PORT, 50016), 10)
    try:
        _LOGGER.debug(
            f'尝试监听 IP={entry.data[CONF_HOST]}, PORT={entry.data.get(CONF_PORT, 50016)}')
        hub.start_listen()
    except socket.error as err:
        _LOGGER.error(f'德能森监听失败啦:{err}')
        raise ConfigEntryNotReady from err

    # 注册内置设备
    register_devices(hub, BUILTIN_DEVICES_STR)
    # 注册内置场景(面板)
    register_scenes(hub, BUILTIN_SCENE_STR)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = hub

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hub: DeoceanGateway = hass.data[DOMAIN].pop(entry.entry_id)
        hub.stop_listen()
    return unload_ok
