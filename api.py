

from typing import Any, Dict, cast
import aiohttp
import asyncio
import logging
import async_timeout
from homeassistant.core import callback
from homeassistant.helpers.entity import Entity
from homeassistant.components import mqtt
import json


_LOGGER: logging.Logger = logging.getLogger(__package__)

class DeoceanAPI(object):
    '''德能森的简易API封装，注意，此API仅限内网
    如果需要外网使用的,您需要抓包APP看，请求的地址会是固定的 http://gateway.deocean.net
    外网的密码是弱口令: admin/admin
    '''
    def __init__(self, baseURI: str, clientSession: aiohttp.ClientSession) -> None:
        self.baseURI = baseURI or 'http://192.168.5.102'
        self.clientSession = clientSession
        self.timeout = 5
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.71 Safari/537.36',
            'Authorization': '7cec62b447217573ca992dfb6543ca9b', # == md5('deocean') #垃圾德能森的Auth头是写死的的~
        }

    async def async_request(self, method: str, endPoint: str, **kw):
        try:
            async with async_timeout.timeout(self.timeout, loop = asyncio.get_event_loop()):
                async with getattr(self.clientSession, method.lower())(f'{self.baseURI.rstrip("/")}/{endPoint.lstrip("/")}', headers = self.headers, **kw) as resp:
                    return cast(dict, await resp.json()).get('data')
        except asyncio.TimeoutError as exception:
            _LOGGER.error(
                "Timeout error fetching information from %s - %s",
                endPoint,
                exception,
            )
        except (KeyError, TypeError) as exception:
            _LOGGER.error(
                "Error parsing information from %s - %s",
                endPoint,
                exception,
            )
        except aiohttp.ClientError as exception:
            _LOGGER.error(
                "Error fetching information from %s - %s",
                endPoint,
                exception,
            )
        except Exception as exception:  # pylint: disable=broad-except
            _LOGGER.error("Something really wrong happened! - %s", exception)
    
    async def async_send_action(self, deviceId: str, action: dict):
        """
        发送控制指令给具体的德能森设备,比如
            a. 灯泡开关action的指令则为 {switch: 'on/off'}
            b. 空调的action指令则为{switch: 'on/off', 'mode': 'cool', 'target_temperature': 24}
            c. 窗帘的action指令为{switch: 'on/off', 'current_position': 30}
        """
        _LOGGER.error('send action: %s => %s', deviceId, action)
        return await self.async_request('POST', 'atom-host/dispatch/device/ctl', json = {
            'id': deviceId,
            'action': action
        })

    async def async_discovery_devices(self):
        """发现德能森设备下的所有设备,比如灯泡,窗帘，空调，新风等等...
        """
        devices = []
        for item in await self.async_request('GET', 'atom-host/api/space/mine/room/devices'):
            for device in item.get('devices', []):
                # 目前只支持 灯(light) / 窗帘(blind) / 空调 (airconditioner)
                if device.get('deviceType') not in ['light', 'blind', 'airconditioner']:
                    continue
                device.update({
                    'spaceName': item.get('name'),
                })
                devices.append(
                    device
                )
        _LOGGER.warning('all devices:%s', devices)
        return devices
        
    
    async def async_device_state(self, deviceIds: list[str]):
        """获取指定设备的具体状态,如果不存在则会被过滤"""
        return await self.async_request('POST', 'atom-host/api/device/state/query', json = [{'id': deviceId} for deviceId in deviceIds])


class DeoceanEntity(Entity):
    def __init__(self, id: str, name: str, state: Dict[str, Any], client: DeoceanAPI, **extra):
        self._id = id
        self._name = name
        self._client = client
        self._state = state
        self._extra = extra
        self._changed = False
        
    @property
    def unique_id(self):
        return self._id

    @property
    def name(self):
        return self._name
    
    @property
    def device_info(self):
        return {
            'id': self._id,
            'name': self._name,
            'type': self._extra.get('deviceType'),
            'state': self._state,
            'spaceName': self._extra.get('spaceName'),
            'meta': self._extra
        }

    @property
    def is_on(self):
        if 'switch' not in self._state:
          _LOGGER.warning('read faild:%s => %s', self._state, self.name)
        return self._state.get('switch') == 'on'

    @property
    def should_poll(self):
        return False
    
    async def async_added_to_hass(self):
        @callback
        def message_received(topic: str, payload: str, qos: int):
            content = json.loads(payload).get('content')
            if not content : return
            info = content[0]
            if info.get('id') != f'{self.unique_id}':
                return
            _LOGGER.error('mqtt刷新状态:%s => %s', self.unique_id, info)
            self._state = info.get('state')
            self.async_write_ha_state()

        await mqtt.async_subscribe(self.hass,  'v2.0.0/family/host/req/319/#', message_received)

    async def async_update(self):
        if self._changed:
          await self._client.async_send_action(self._id, self._state)
          self._changed = False
        # else:
        #   resp = await self._client.async_device_state([self._id])
        #   self._state = resp[0]['state']

