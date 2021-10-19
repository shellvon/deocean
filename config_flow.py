import logging
import voluptuous as vol


from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from .const import DOMAIN


_LOGGER: logging.Logger  = logging.getLogger(__package__)

class DeoceanConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    async def async_step_user(self, info):
        if info is not None:
            return self.async_create_entry(
                title=f'德能森{info.get(CONF_HOST)}',
                data=info,
            )
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_HOST, description="德能森IP地址"): str,
            })
        )
