# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Callable, Dict, List, Union, Literal, Iterable
import attr
import copy
import enum
import time
import socket
import struct
import logging
# from collections import namedtuple
# https://stackoverflow.com/questions/34269772/type-hints-in-namedtuple
from dataclasses import dataclass

from sys import platform
from functools import partial
from threading import Thread


_LOGGER = logging.getLogger(__package__)

# 德能森的设备地址是8位的16进制
Addr = Union[str, int, List[Union[str, int]]]


@dataclass
class Scene:
    name: str
    addr: int
    channel: int
    tasks: List[List[str, str]]  # 每一个task 都是 设备名 操作


@dataclass
class SceneTask:
    id: str
    name: str
    action: Callable[[], None]


def toInt(addr: Addr) -> int:
    """德能森的地址都是8位长度16进制
    地址格式形如:
        int 数组/原组:  [0xA, 0xB, 0xC, 0xD]
        str 数组/原组:  ['0xA', '0xB', 'C', '0xD'] # 0x prefix 是可选的
        int 或 str  :  0x0A0B0C0D
    返回值都是10进制的统一整数.
    """
    if isinstance(addr, (tuple, list)):
        if len(addr) != 4:
            raise ValueError('地址为数组时必须4位元素')
        addr = list(map(lambda x: int(x, 16)
                    if isinstance(x, str) else x, addr))
        # addr = (addr[0] << 24) + (addr[1] << 16) + (addr[2] << 8) + addr[3]
        addr = int('%02x' * len(addr) % tuple(addr), 16)
    else:
        addr = int(addr, 16) if isinstance(addr, str) else addr
    return addr


def bytes_debug_str(data: bytes):
    return '[%s]' % ' '.join([f'{x:02X}' for x in bytearray(data)])


def batch_action(iter: Iterable, *args, **kwargs):
    for callback in iter:
        if callable(callback):
            callback(*args, **kwargs)


class DeoceanGateway:
    """
    该网关并没有文档，通过日志分析(/home/deocean_v2/log/ebelong.log)猜测分析的方式。所以不能保证所有指令方式都支持.
    """

    def __init__(self, ip_addr: str, port: int = 9999, timeout: int = None):
        self.ip_addr = ip_addr
        self.port = port or 9999
        self.sock = None
        self.devices: Dict[str, DeoceanDevice] = {}
        # 场景配置.
        # 每一个key都是对应场景配置的addr
        # 值就是需要执行的操作.
        self.scenes: dict[str, SceneTask] = {}
        self._listening = False
        self._thread = None
        self.max_retry = 5
        self.timeout = timeout or 60

    def __get_socket(self) -> socket.socket:
        """
        工具函数,打开一个连接好的Socket.
        """
        _LOGGER.debug("Opening socket to (%s, %s)", self.ip_addr, self.port)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if platform in ('linux', 'linux2'):
            s.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE,
                         1)  # pylint: disable=E1101
        if platform in ('darwin', 'linux', 'linux2'):
            s.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            s.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 3)
            s.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 5)
        s.settimeout(self.timeout)
        s.connect((self.ip_addr, self.port))
        return s

    def open_socket(self):
        if self.sock:
            self.sock.close()
            self.sock = None
            time.sleep(1)

        self.sock = self.__get_socket()
        return self.sock

    def _listen_to_msg(self):
        while self._listening:
            data = self._get_data()
            if not data:
                continue
            _LOGGER.debug(f'recv <---{bytes_debug_str(data)}')
            for frame in parse_data(data):
                # 没有设备, 跳过
                if not frame.device_address:
                    continue
                if frame.func_code == FuncCode.SEARCH:
                    # 搜索貌似没有鸟用
                    continue
                device = self.get_device(frame.device_address)
                # 这里只会找到灯或者窗帘(被添加进去的设备)
                if device:
                    kwargs = {}
                    if frame.position is not None:
                        kwargs['position'] = frame.position
                    # 开关状态
                    if frame.ctrl_code in [ControlCode.COVER_OFF,  ControlCode.COVER_ON, ControlCode.LIGHT_OFF, ControlCode.LIGHT_ON]:
                        kwargs['switch_status'] = frame.ctrl_code.name
                    device.update(**kwargs)
                elif frame.channel is not None:
                    scene_task = self.scenes.get(self.generate_scene_id(
                        frame.device_address.mac_address, frame.channel))
                    if scene_task and callable(scene_task.action):
                        _LOGGER.debug(
                            f'触发场景:{scene_task.name}<id={scene_task.id}>')
                        scene_task.action()

    def generate_scene_id(self, addr: Addr, channel: int):
        """生成一个场景ID，场景ID由面板的唯一地址以及按键决定，按键在德能森里面叫channel.
        比如一个面板有回家/离家 则他们共有相同的addr,但 channel 不同
        按照德能森现在的情况。channel 都是 2的次方值。比如1/2/4/8 . 因为channel 就一个字节,最大只能到0xFF
        """
        return f'{toInt(addr):08X}:{channel}'

    def register_scene(self, addr: Addr, channel: int, action: Callable, name: str = None, force: bool = False):
        """
        注册场景,  该接口由网关收到面板的按钮之后，派送此场景可以做什么.

        需要注意的是，面板和灯具/窗帘ID不可重复.否则场景无效。
        一个面板上可以有多个按键。每一个按键对应一个channel。 同一个面板 addr 一样。 channel不一样 可以标注不同的按钮。

        举个例子:
        原德能森的配置文件如下:
        - 主卧床头布帘按键, panel, 44540400, 8
        即表示面板 主卧床头左(0x44540400) channel 为8 的按键(主卧床头布帘按键)
        他对应的业务逻辑在其数据库中明确事件为toggle 设备为xxx。
        所以我们可以这样:
            gw = DeoceanGateway('192.168.5.201', 50016)
            # 注册一个布帘
            cover = DeoceanDevice(gw, 0xABCDEF, TypeCode.COVER, '客厅布帘')
            # 注册地址.
            gw.register_scene(0x44540400, 8, cover.toggle, '主卧床头布帘按键')
            gw.start_listen()

        当gw收到消息发现是场景时，会自动触发cover.toggle API
        """
        if not isinstance(channel, int) or channel <= 0 or channel >= 256:
            raise ValueError('通道必须是1~255的数字值')
        if not callable(action):
            raise ValueError('action必须支持调用')
        id = self.generate_scene_id(addr, channel)
        if not force and id in self.scenes:
            raise '已有该场景'
        self.scenes[id] = SceneTask(id, name or f'场景-{id}', action)

    def start_listen(self):
        """Start listening."""
        if self._listening:
            return True

        if self.sock is None:
            self.open_socket()

        self._listening = True
        thread = Thread(target=self._listen_to_msg, args=())
        self._thread = thread
        thread.daemon = True
        thread.start()
        _LOGGER.info("Start message listen thread %s", thread.ident)
        return True

    def send(self, data: DeoceanData) -> None:
        if not self.sock:
            _LOGGER.debug('未建立Socket,假发送: %s' % data.hex())
            for frame in parse_data(data.encode()):
                _LOGGER.debug(frame)
            return

        def _send(retry_count):
            try:
                self.sock.settimeout(10.0)
                _LOGGER.debug("send >> %s", data.hex())
                self.sock.send(data.encode())
                self.sock.settimeout(None)

            except socket.timeout:
                _LOGGER.error("Connot connect to gateway %s:%s", self.ip_addr,
                              self.port)
                return

            except OSError as e:
                if e.errno == 32:  # Broken pipe
                    _LOGGER.error("OSError 32 raise, Broken pipe", exc_info=e)
                if retry_count < self.max_retry:
                    retry_count += 1
                    self.open_socket()
                    _send(retry_count)

        _send(0)

    def stop_listen(self):
        self._listening = False
        if self.sock:
            _LOGGER.info('Closing socket.')
            self.sock.close()
            self.sock = None
        self._thread.join()

    def _get_data(self):
        if self.sock is None:
            self.open_socket()

        try:
            return self.sock.recv(1024)

        except ConnectionResetError:
            _LOGGER.debug("Connection reset by peer")
            self.open_socket()

        except socket.timeout as e:
            _LOGGER.error("timeout error", exc_info=e)

        except OSError as e:
            if e.errno == 9:  # when socket close, errorno 9 will raise
                _LOGGER.debug("OSError 9 raise, socket is closed")

            else:
                _LOGGER.error("unknown error when recv", exc_info=e)

        except Exception as e:
            _LOGGER.error("unknown error when recv", exc_info=e)

        return None

    def discovery_devices(self):
        """自定义的设备发现不齐全"""

        _LOGGER.debug("search devices")
        if self.sock is None:
            self.open_socket()
        request_data = DeoceanData(FuncCode.SEARCH)
        request_data.type = TypeCode.LIGHT
        _LOGGER.debug("send discovery request: %s", request_data.hex())
        self.send(request_data)
        discovered = False
        while not discovered:
            data = self._get_data()
            if data is None:
                _LOGGER.error("No response from gateway")
                continue
            for frame in parse_data(data):
                _LOGGER.info('discovery new devices:', frame)
                if bytes_debug_str(data) == bytes_debug_str(request_data.encode()):
                    discovered = True
        _LOGGER.debug(f"discovery done! resutl={discovered}")

    def add_device(self, device: DeoceanDevice, force: bool = False):
        key = toInt(device.addr.mac_address)
        if key in self.devices and not force:
            _LOGGER.warning('已有相同设备')
            return
        self.devices[key] = device

    def get_device(self, addr):
        if isinstance(addr, DeviceAddr):
            addr = addr.mac_address
        return self.devices.get(toInt(addr))

    def list_devices(self, type) -> set:
        return {device for (_, device) in self.devices.items() if device.type == type}


#####################################
############ 协议相关 ################
#####################################
STOP_BIT = 0x0D


class TypeCode(enum.Enum):
    """
    猜测的格式,灯泡是7E,但窗帘似乎是0X55AA,AA不知道到底是个啥玩意儿.
    """
    LIGHT = 0x7E
    COVER = 0x55


class FuncCode(enum.Enum):
    # 日志里面有saerch mode 但似乎不起作用....
    SEARCH = 0X01
    # 查询状态,似乎都是0D
    SYNC = 0x0D
    # 控制开关(灯具/窗帘)都是0B
    SWITCH = 0x0B
    # 如果要设置百分比就是1B
    COVER_POSITION = 0x1B
    # 如果SWITCH 设置on/off 开关之后 收到的消息是0C,即 0B -> 0C, 1B->1C
    SWITCH_UPDATED = 0x0C
    # 如果设置窗帘位置是百分比之后，收到的消息是1C. 即 0B -> 0C, 1B->1C
    POSITION_UPDATED = 0x1C


class ControlCode(enum.Enum):
    # 灯泡开关
    LIGHT_ON = 0x0201
    LIGHT_OFF = 0x0200

    # 打开表示pos = 100
    COVER_ON = 0x0402
    # off = pos =0
    COVER_OFF = 0x0401

    # 请求窗帘状态用到控制码
    COVER_SYNC = 0x04FF


@attr.s
class DeoceanStructData:
    @staticmethod
    def _to_value(element):
        if isinstance(element, enum.Enum):
            return int(element.value)
        return int(element)

    def export(self):
        return list(map(self._to_value, attr.astuple(self)))

    def encode(self):
        length = len(self.export())
        return struct.pack("B" * length, * self.export())


@attr.s(slots=True, hash=True)
class DeviceAddr(DeoceanStructData):
    """设备地址占4字节"""
    mac_address: int = attr.ib(converter=toInt)

    @property
    def length(self):
        return 4

    def encode(self):
        return struct.pack('>i', self.mac_address)

    def __str__(self):
        return f'addr-{self.mac_address:08X}'


@attr.s(slots=True)
class DeoceanData(DeoceanStructData):
    """德能森数据网关传输"""
    type: TypeCode = attr.ib(init=False)
    func_code: FuncCode = attr.ib()
    ctrl_code: ControlCode = attr.ib(default=None)
    device_address: DeviceAddr = attr.ib(default=None)
    channel: int = attr.ib(default=None)
    position: int = attr.ib(default=None)
    stop_bit = STOP_BIT

    def encode(self):
        msg = [self.type.value]
        size = 0
        size_index = 1
        if self.type == TypeCode.COVER:
            msg.append(0xAA)
            size += 1
            size_index += 1
        msg.append(0x00)  # 消息长度占位符,最后才知道消息多长
        msg.append(DeoceanStructData._to_value(self.func_code))  # 功能

        # 如有设备,将地址便入其中。
        if self.device_address:
            msg.append(self.device_address.encode())
            size += self.device_address.length

        padding = [0x01]
        if self.func_code == FuncCode.COVER_POSITION and self.position:
            # 设置位置的时候paddig 不是 0x01, 而是0x02 只有控制开关的时候才是0x01
            padding = [0x02, 0x04, self.position]
        elif (self.func_code == FuncCode.SYNC and self.type == TypeCode.COVER):
            # 因为Control Code 是2bit，append 俩次是为了计算size的时候正确，否则这里需要手动调用一次 size += 1
            v = ControlCode.COVER_SYNC.value
            padding.append(v >> 8)
            padding.append(v & 0xFF)
        elif self.ctrl_code:
            # 因为Control Code 是2bit，append 俩次是为了计算size的时候正确，否则这里需要手动调用一次 size += 1
            v = self.ctrl_code.value
            padding.append(v >> 8)
            padding.append(v & 0xFF)
        else:
            padding = []
        padding.append(self.stop_bit)
        size += len(padding)
        # 恢复数据长度
        msg[size_index] = size
        # 结束占位符
        msg.extend(padding)

        return b''.join([struct.pack('B', val) if isinstance(val, int) else val for val in msg])

    def hex(self):
        return bytes_debug_str(self.encode())

    def __str__(self):
        addr = None
        if self.device_address:
            addr = f'{self.device_address.mac_address:08X}'
        name = self.type.name if self.channel is None else 'SCENE'
        return 'DeoceanData(type=%s-%s, func=%s, status=%s, pos=%s, channel=%s)' % (name, addr, self.func_code.name, 'None' if not self.ctrl_code else self.ctrl_code.name, self.position, self.channel)


class DeoceanDevice:
    """
    德能森网关支持的设备
    """

    def __init__(self, gw: DeoceanGateway, addr: Addr, type: TypeCode, name: str = None):
        self.gw = gw
        self.addr = DeviceAddr(addr)
        self.type = type
        self.switch_status: Union[str, None] = None
        self.position: Union[int, None] = None  # 窗帘可能有位置.
        self.gw.add_device(self)

        self.status_callback: List[Callable[..., None]] = []
        self._name = name if name else self.type.name

    def _call_status_update(self):
        batch_action(self.status_callback, self)

    def send(self, data: DeoceanData) -> None:
        if self.gw:
            self.gw.send(data)

    def _ctrl_(self, func_code: FuncCode, ctrl_code: Union[ControlCode, None] = None, pos: Union[int, None] = None) -> None:
        payload = DeoceanData(func_code)
        payload.type = self.type
        payload.func_code = func_code
        payload.ctrl_code = ctrl_code
        payload.device_address = self.addr
        if pos is not None:
            pos = max(min(pos, 100), 0)

        if self.type == TypeCode.LIGHT:
            if func_code not in [FuncCode.SYNC, FuncCode.SWITCH]:
                raise ValueError('灯具仅支持查询/开关')
            if pos is not None:
                _LOGGER.warning('灯具位置参数忽略.')
        elif self.type == TypeCode.COVER:
            if func_code == FuncCode.COVER_POSITION:
                if pos is None:
                    raise ValueError('窗帘位置必须')
                elif pos == 0 or pos == 100:
                    payload.ctrl_code = ControlCode.COVER_ON if pos == 100 else ControlCode.COVER_OFF
                    payload.func_code = FuncCode.SWITCH
                else:
                    payload.position = pos
            elif func_code in [FuncCode.SWITCH, FuncCode.SYNC]:
                payload.ctrl_code = ctrl_code
            else:
                raise ValueError(f'不支持的设备类型:{self.type}')
        return self.send(payload)

    def register_update_callback(self, _callable: Callable) -> bool:
        if callable(_callable):
            self.status_callback.append(_callable)
            return True
        return False

    @property
    def is_on(self):
        """判断设备是否开"""
        return self.switch_status in [ControlCode.COVER_ON.name, ControlCode.LIGHT_ON.name]

    @property
    def is_close(self):
        """判断设备是否处于关"""
        return self.switch_status in [ControlCode.COVER_OFF.name, ControlCode.LIGHT_OFF.name]

    def toggle(self):
        """开关切换,在没有状态的情况下首次执行会是开"""
        if self.is_on:
            self.turn_off()
        else:
            self.turn_on()

    def turn_on(self):
        """打开设备"""
        self._ctrl_(FuncCode.SWITCH, ControlCode.COVER_ON if self.type ==
                    TypeCode.COVER else ControlCode.LIGHT_ON)

    def turn_off(self):
        """关闭设备"""
        self._ctrl_(FuncCode.SWITCH, ControlCode.LIGHT_OFF if self.type ==
                    TypeCode.LIGHT else ControlCode.COVER_OFF)

    def set_position(self, pos: int):
        """设置窗帘位置,hass称100表示完全打开。0是关闭"""
        if self.type != TypeCode.COVER:
            raise ValueError('仅窗帘支持设置位置')
        self._ctrl_(FuncCode.COVER_POSITION, None, pos)

    def sync(self):
        """状态同步, 网关搜到消息之后会告知当前灯具/窗帘开关状态"""
        self._ctrl_(FuncCode.SYNC)

    def update(self, **kwargs):
        """更新请使用此接口,方便状态同步"""
        dirty = False
        if (pos := kwargs.get('position')) is not None and self.type:
            dirty = self.position != pos
            self.position = pos
        if (switch_status := kwargs.get('switch_status')) is not None:
            if isinstance(switch_status, enum.Enum):
                switch_status = switch_status.name
            if not dirty:
                dirty = self.switch_status != switch_status
            self.switch_status = switch_status
        if dirty:
            _LOGGER.debug(f'{self} updated: {kwargs}', )
            self._call_status_update()
        else:
            _LOGGER.debug(f'{self} not update')

    def __str__(self) -> str:
        return f'{self.name}<type={self.type.name},addr={self.unique_id},status={self.switch_status}>'

    @property
    def name(self):
        return self._name

    @property
    def unique_id(self):
        """
        See https://www.home-assistant.io/faq/unique_id/
        """
        return f'{self.addr.mac_address:08X}'


def parse_data(data):
    data = copy.copy(data)
    while data:
        try:
            if len(data) < 3:
                return
            dev_type = TypeCode(struct.unpack('B', data[:1])[0])
            start_at = 2
            if dev_type == TypeCode.LIGHT:
                msg_size = struct.unpack('B', data[1:2])[0]
            elif dev_type == TypeCode.COVER:
                placeholder, msg_size = struct.unpack('BB', data[1:3])
                if placeholder != 0xAA:
                    _LOGGER.warning(f'占位符不是0xAA')
                    data = data[3:]
                    continue
                start_at += 1  # 多一个占位符AA.
                msg_size -= 1  # 但整体长度这里要少一位😂，有毒吧
            # 起始点包括header 1～2字节。消息体 size字节 + 结束符一字节.
            frame_size = start_at + msg_size + 1
            if len(data) < frame_size:
                _LOGGER.error(
                    f"数据长度不足,期望长度{frame_size},实际长度{len(data)}, 数据源:{bytes_debug_str(data)}")
                return data
            frame = data[start_at:frame_size]
            msg = struct.unpack('B' * len(frame), frame)
            if msg[-1] != STOP_BIT:
                _LOGGER.warning(f'没有发现终止符,跳过本数据: {bytes_debug_str(data)}')
                data = data[frame_size:]
                continue
            payload = DeoceanData(FuncCode(msg[0]))
            addr = None
            if payload.func_code != FuncCode.SEARCH:
                if len(msg) < 5:
                    _LOGGER.error('数据格式不合法')
                    data = data[frame_size:]
                    continue
                addr = toInt(msg[1:5])
                if addr == 0:
                    data = data[frame_size:]
                    continue
                addr = DeviceAddr(addr)
            payload.type = dev_type
            payload.device_address = addr
            ctrl_code_num = None
            if len(msg) > 6:  # 4 字节地址 + 2 字节功能 + 1 字节结束符0x0D
                if dev_type == TypeCode.LIGHT:
                    # 场景值功能区域似乎都是0xEFxx形式。所以后三位一定是0xEFxx0D, xx是channel.
                    if msg[-3] == 0xEF:
                        payload.channel = msg[-2]
                    else:
                        # 就是普通灯具.提取功能码
                        ctrl_code_num = (msg[-3] << 8) + msg[-2]
                elif msg[-2] != 0XFF:  # 窗帘有时候返回的0xFF不知道什么意思
                    payload.position = msg[-2] if payload.func_code not in [
                        FuncCode.SWITCH_UPDATED, FuncCode.SWITCH] else None
                    # 窗帘位置设置之后为0x02, 位置是没有控制码的.
                    if msg[-4] == 0x01 and payload.func_code != FuncCode.SYNC:
                        ctrl_code_num = (msg[-3] << 8) + msg[-2]
            try:
                if ctrl_code_num is not None:
                    payload.ctrl_code = ControlCode(ctrl_code_num)
                yield payload
            except ValueError:
                _LOGGER.error('Unknown Control Code: %s' %
                              bytes_debug_str(data))
            data = data[frame_size:]  # 等待新消息
        except Exception as e:
            data = data[1:]  # 往前迁移一字节处理.
            continue


def split_txt_to_lines(txt: str, sep: str = ',', field_cnt: Union[int, None] = None):
    """将字符串txt按照换行符分割之后,用 sep分割成多个list, 如果指定了field_cnt则分片成这么多(保证一定有这么多)"""
    for line in txt.split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        fields = list(map(lambda x: x.strip(), line.split(sep)))
        if field_cnt:
            if len(fields) < field_cnt:
                continue
            yield fields[:field_cnt]
        yield fields


def parse_scene_str(txt: str):
    """解析场景配置

    场景配置格式为: name, addr, channel, devices, op
    其中devices 是已经add 的设备名。多个名字使用|分割.
    """
    for fields in split_txt_to_lines(txt):
        size = len(fields)
        if size not in [4, 5]:
            _LOGGER.error(f'场景配置不合法(列数必须是4):{fields}')
            continue
        tasks = []
        for dev in fields[3].split('|'):
            if dev.count(':'):
                dev, op = dev.split(':')
            elif size == 5:
                op = fields[4]
            else:
                _LOGGER.error(f'场景配置不合法:{fields}')
                continue
            tasks.append([dev, op])
        yield Scene(fields[0], int(fields[1], 16), int(fields[2]), tasks)


def register_scenes(hub: DeoceanGateway, raw_txt: str):
    """
    工具函数. 注册场景.

    场景配置格式类似CSV。即以逗号隔开分组。如果是注释可以以 # 开头。
    name, addr, channel, devices, op
    其中devices 是已经add 的设备名。多个名字使用|分割.
    特殊设备名包括:
        all :不区分设备类型，所有设备
        all_light: 所有灯具
        all_cover: 所有窗帘
    比如配置可以是
    '
    # 这一行为注释，地址为16进制数字。0x前缀可以省略。 op目前支持 turn_on turn_off toggle 三种。
    # 表示按下回家按钮的时候, 所有灯以及客厅的布帘需要处于打开状态
    回家, 0x0A0B0C0D, 2, all_light|客厅布帘, turn_on
    '
    如果您想更骚气一点:
        如你所见，在同一个场景下把A设备打开,B设备关闭,C设备toggle的状态。
    但如果需要这么做,我们可以扩展格式:
    '
    # 所有灯具先turn_off关闭。然后窗帘没有指定则用默认值 turn_on, 过道灯虽然也在all_light中被先关闭了，此处你可以再toggle一次。
    # 实际情况下，可能因为 前面all_light灯具状态没有返回就已经执行toggle了，所以可能会出现toggle状态弄错的问题
    #
    回家, 0x0A0B0C0D, 2, all_light:turn_off|客厅布帘|过道灯:toggle, turn_on
    '
    """
    all_lights = hub.list_devices(TypeCode.LIGHT)
    all_cover = hub.list_devices(TypeCode.COVER)

    devices_map = {dev.name: dev for dev in hub.devices.values()}

    def operation_wrapper(dev: DeoceanDevice, op: str):
        """
        把场景的op转成设备可以支持的指令
        """
        if op in ['turn_on', 'turn_off', 'toggle', 'sync']:
            return getattr(dev, op)
        if dev.type != TypeCode.COVER:
            _LOGGER.warning(f'仅窗帘支持位置指令,但给定类型为:{dev.type}')
            return
        try:
            op = max(min(int(op), 100), 0)
        except:
            _LOGGER.error(f'不支持的指令:{op}')
            return
        return partial(dev.set_position, op)

    for scene in parse_scene_str(raw_txt):
        # 集合以去重
        callback = set()
        for (dev_name, op) in scene.tasks:
            if dev_name in ['all_light', 'all_cover', 'all']:
                if dev_name != 'all_cover':
                    callback.update({operation_wrapper(dev, op)
                                     for dev in all_lights})
                if dev_name != 'all_light':
                    callback.update({operation_wrapper(dev, op)
                                     for dev in all_cover})
            elif dev_name in devices_map:
                callback.add(operation_wrapper(devices_map.get(dev_name), op))
            else:
                _LOGGER.warning(f'设备:{dev_name}找不到')
        # 过滤掉所有不支持的回调
        callback = {cb for cb in callback if cb is not None}
        if (size := len(callback)) == 0:
            continue
        _LOGGER.debug(f'注册场景:{scene},设备数:{size}')

        hub.register_scene(scene.addr, scene.channel,
                           partial(batch_action, callback), scene.name, True)


def register_devices(hub: DeoceanGateway, raw_txt: str):
    """工具函数,注册给定的设备到网关"""
    for (name, typ, addr) in split_txt_to_lines(raw_txt, ',', 3):
        if typ not in ['light', 'blind']:
            _LOGGER.warning('设备仅支持灯具/窗帘')
            continue
        dev = DeoceanDevice(hub, addr, TypeCode.COVER if typ ==
                            'blind' else TypeCode.LIGHT, name)
        hub.add_device(dev)  # 加入当前设备
        dev.sync()  # 网关有此设备后同步一次状态
        _LOGGER.debug(f'德能森: {dev} added to {hub}')


######## 测试方法 #####


def test_light(gw: DeoceanGateway):
    light = DeoceanDevice(gw, 0x001E9A5D, TypeCode.LIGHT, '公卫灯')

    print('--------------------模拟灯具发送指令--------------------')
    print('同步:')
    light.sync()
    print('开灯:')
    light.turn_on()
    print('关灯:')
    light.turn_off()


def test_cover(gw: DeoceanGateway):
    print('--------------------模拟窗帘发送指令--------------------')
    cover = DeoceanDevice(gw, 0x7554C701, TypeCode.COVER, '客厅布帘')
    print('同步:')
    cover.sync()

    print('打开窗帘')
    cover.turn_on()
    print('关闭窗帘')
    cover.turn_off()
    position = 0x19
    print(f'设置位置(posHex={hex(position)},pos={position})')
    cover.set_position(position)


def test_scene(gw: DeoceanGateway):
    print('--------------------模拟场景--------------------')
    from .const import BUILTIN_SCENE_STR, BUILTIN_DEVICES_STR
    register_devices(gw, BUILTIN_DEVICES_STR)
    register_scenes(gw, BUILTIN_SCENE_STR)
    scene_id = gw.generate_scene_id('F7540400', 8)
    scene = gw.scenes.get(scene_id)
    if scene:
        print('执行场景:', scene.name)
        scene.action()
    else:
        print(
            f'-->需要配置场景后才可以执行, scene_id={scene_id},已存在的场景:', gw.scenes.keys())


def test_decode():
    # 命令文本来自:
    # grep -E 'Set(Position|Switch)' ebelong.log | cut -d : -f7-8
    sendCmdText = '''
    data: 55 AA 09 0D 74 C1 5D 78 01 04 61 0D
    '''.split('\n')

    no = 0
    for line in sendCmdText:
        if not line or not line.strip():
            continue
        name, cmd = line.split('data:')
        cmd = cmd.strip()
        no += 1
        print('try parse ->', cmd)
        cmd = b''.join([struct.pack('B', int(val, 16))
                        for val in cmd.strip().split(' ')])

        for frame in parse_data(cmd):
            print('\t', frame)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    gw = DeoceanGateway('192.168.5.201', 50016)

    gw.start_listen()

    test_light(gw)

    test_cover(gw)

    test_scene(gw)

    test_decode()
