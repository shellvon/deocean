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
from homeassistant.helpers import device_registry as dr
from .hub import DeoceanGateway, register_devices, register_scenes
from .const import DOMAIN, CONF_DEVICES, CONF_SCENES, DEFAULT_PORT, VERSION

PLATFORMS = ["light", "cover"]

_LOGGER = logging.getLogger(__package__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hub = DeoceanGateway(
        entry.data[CONF_HOST], entry.data.get(CONF_PORT, DEFAULT_PORT), 10
    )
    try:
        _LOGGER.debug(
            f"尝试监听 IP={entry.data[CONF_HOST]}, PORT={entry.data.get(CONF_PORT, DEFAULT_PORT)}"
        )
        hub.start_listen()
    except socket.error as err:
        _LOGGER.error(f"德能森监听失败啦:{err}")
        raise ConfigEntryNotReady from err

    # 从配置条目中获取设备和场景配置
    devices_config = entry.data.get(CONF_DEVICES, "")
    scenes_config = entry.data.get(CONF_SCENES, "")

    # 注册用户配置的设备
    if devices_config.strip():
        try:
            register_devices(hub, devices_config)
            _LOGGER.info(f"已注册 {len(hub.devices)} 个实体设备")
        except Exception as err:
            _LOGGER.error(f"注册设备失败: {err}")

    # 注册用户配置的场景
    if scenes_config.strip():
        try:
            register_scenes(hub, scenes_config)
            _LOGGER.info(f"已注册 {len(hub.scenes)} 个场景")
        except Exception as err:
            _LOGGER.error(f"注册场景失败: {err}")

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = hub

    # 注册网关设备 - 提供网关状态监控和逻辑层次结构
    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, f"gateway_{hub.ip_addr}")},
        name=f"德能森网关 ({hub.ip_addr})",
        manufacturer="德能森",
        model="智能网关",
        sw_version=VERSION,
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hub: DeoceanGateway = hass.data[DOMAIN].pop(entry.entry_id)
        hub.stop_listen()
    return unload_ok
