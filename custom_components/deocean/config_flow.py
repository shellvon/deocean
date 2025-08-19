# -*- coding: utf-8 -*-

"""
在manifest.json 中配置 config_flow为 true 既可以开启可视化UI配置.
参考文档:
    https://developers.home-assistant.io/docs/config_entries_config_flow_handler/
"""

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT

from .const import DOMAIN
from .hub import DeoceanGateway

class DeoceanConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, info):
        if info is not None:
            hub = DeoceanGateway(info[CONF_HOST], info[CONF_PORT], 5)
            try:
                hub.open_socket()
                hub.stop_listen()
                return self.async_create_entry(title="德能森", data=info)
            except Exception as e:
                return self.async_abort(reason="can_not_establish_connection", description_placeholders={'errmsg': str(e)})
        if self._async_current_entries():
            return self.async_abort(reason="one_instance_allowed")
    
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_HOST, description="IP", default="192.168.5.201"
                    ): str,
                    vol.Optional(CONF_PORT, description="PORT", default=50016): vol.All(
                        vol.Coerce(int), vol.Range(min=0)
                    ),
                }
            ),
        )
