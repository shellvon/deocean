# -*- coding: utf-8 -*-

"""
在manifest.json 中配置 config_flow为 true 既可以开启可视化UI配置.
参考文档:
    https://developers.home-assistant.io/docs/config_entries_config_flow_handler/
"""

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    CONF_DEVICES,
    CONF_SCENES,
    DEFAULT_DEVICES,
    DEFAULT_SCENES,
    DEFAULT_HOST,
    DEFAULT_PORT,
)
from .hub import DeoceanGateway


class DeoceanConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            # 验证网关连接
            hub = DeoceanGateway(user_input[CONF_HOST], user_input[CONF_PORT], 5)
            try:
                hub.open_socket()
                hub.stop_listen()

                # 如果连接成功，进入设备配置步骤
                self._user_input = user_input
                return await self.async_step_devices()

            except Exception as e:
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
                    vol.Optional(CONF_PORT, default=DEFAULT_PORT): vol.All(
                        vol.Coerce(int), vol.Range(min=1, max=65535)
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_devices(self, user_input=None):
        if user_input is not None:
            self._user_input.update(user_input)
            return await self.async_step_scenes()

        return self.async_show_form(
            step_id="devices",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_DEVICES, default=DEFAULT_DEVICES
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.TEXT,
                            multiline=True,
                        )
                    ),
                }
            ),
            description_placeholders={
                "devices_format": "设备名, 设备类型(light|blind), 设备地址"
            },
        )

    async def async_step_scenes(self, user_input=None):
        if user_input is not None:
            self._user_input.update(user_input)

            # 创建配置条目
            return self.async_create_entry(
                title="德能森智能家居", data=self._user_input
            )

        return self.async_show_form(
            step_id="scenes",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_SCENES, default=DEFAULT_SCENES
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.TEXT,
                            multiline=True,
                        )
                    ),
                }
            ),
            description_placeholders={
                "scenes_format": "场景名, 面板地址, channel, 设备名, 操作"
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return DeoceanOptionsFlow()


class DeoceanOptionsFlow(config_entries.OptionsFlow):

    async def async_step_init(self, user_input=None):
        return await self.async_step_menu()

    async def async_step_menu(self, user_input=None):
        return self.async_show_menu(
            step_id="menu",
            menu_options=["devices", "scenes", "add_device", "add_scene"],
        )

    async def async_step_devices(self, user_input=None):
        if user_input is not None:
            # 更新设备配置
            new_data = dict(self.config_entry.data)
            new_data[CONF_DEVICES] = user_input[CONF_DEVICES]
            self.hass.config_entries.async_update_entry(
                self.config_entry, data=new_data
            )
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            return self.async_create_entry(title="", data={})

        current_devices = self.config_entry.data.get(CONF_DEVICES, DEFAULT_DEVICES)

        return self.async_show_form(
            step_id="devices",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_DEVICES, default=current_devices
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.TEXT,
                            multiline=True,
                        )
                    ),
                }
            ),
        )

    async def async_step_scenes(self, user_input=None):
        if user_input is not None:
            # 更新场景配置
            new_data = dict(self.config_entry.data)
            new_data[CONF_SCENES] = user_input[CONF_SCENES]
            self.hass.config_entries.async_update_entry(
                self.config_entry, data=new_data
            )
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            return self.async_create_entry(title="", data={})

        current_scenes = self.config_entry.data.get(CONF_SCENES, DEFAULT_SCENES)

        return self.async_show_form(
            step_id="scenes",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCENES, default=current_scenes
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.TEXT,
                            multiline=True,
                        )
                    ),
                }
            ),
        )

    async def async_step_add_device(self, user_input=None):
        if user_input is not None:
            # 添加新设备到现有配置
            current_devices = self.config_entry.data.get(CONF_DEVICES, "")
            new_device_line = f"{user_input['device_name']}, {user_input['device_type']}, {user_input['device_address']}"

            if current_devices.strip():
                updated_devices = current_devices + "\n" + new_device_line
            else:
                updated_devices = new_device_line

            new_data = dict(self.config_entry.data)
            new_data[CONF_DEVICES] = updated_devices
            self.hass.config_entries.async_update_entry(
                self.config_entry, data=new_data
            )
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="add_device",
            data_schema=vol.Schema(
                {
                    vol.Required("device_name"): str,
                    vol.Required("device_type", default="light"): vol.In(
                        ["light", "blind"]
                    ),
                    vol.Required("device_address"): str,
                }
            ),
        )

    async def async_step_add_scene(self, user_input=None):
        if user_input is not None:
            # 添加新场景到现有配置
            current_scenes = self.config_entry.data.get(CONF_SCENES, "")
            new_scene_line = f"{user_input['scene_name']}, {user_input['panel_address']}, {user_input['channel']}, {user_input['devices']}, {user_input['operation']}"

            if current_scenes.strip():
                updated_scenes = current_scenes + "\n" + new_scene_line
            else:
                updated_scenes = new_scene_line

            new_data = dict(self.config_entry.data)
            new_data[CONF_SCENES] = updated_scenes
            self.hass.config_entries.async_update_entry(
                self.config_entry, data=new_data
            )
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="add_scene",
            data_schema=vol.Schema(
                {
                    vol.Required("scene_name"): str,
                    vol.Required("panel_address"): str,
                    vol.Required("channel"): vol.All(
                        vol.Coerce(int), vol.Range(min=1, max=255)
                    ),
                    vol.Required("devices", default="all_light"): str,
                    vol.Required("operation", default="turn_on"): vol.In(
                        ["turn_on", "turn_off", "toggle"]
                    ),
                }
            ),
        )
