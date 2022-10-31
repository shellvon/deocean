"""
在manifest.json 中配置 config_flow为 true 既可以开启可视化UI配置.
参考文档:
    https://developers.home-assistant.io/docs/config_entries_config_flow_handler/
"""

import voluptuous as vol


from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from .const import DOMAIN


class DeoceanConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    async def async_step_user(self, info):
        if info is not None:
            return self.async_create_entry(
                title=f'德能森{info.get(CONF_HOST)}',
                data=info
            )
        if self._async_current_entries():
            return self.async_abort(reason='one_instance_allowed')
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_HOST, description="IP", default='192.168.201'): str,
                vol.Optional(CONF_PORT, description="PORT", default=50016): vol.All(vol.Coerce(int), vol.Range(min=0)),
            })
        )
