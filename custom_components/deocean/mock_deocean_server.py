#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
德能森网关Mock服务器 - 简化版
用于测试Home Assistant集成，使用const.py中的设备配置
"""

import socket
import threading
import logging
from typing import Dict, Optional
from hub import (
    DeoceanData,
    FuncCode,
    ControlCode,
    TypeCode,
    DeviceAddr,
    toInt,
    parse_data,
    split_txt_to_lines,
)
from const import DEFAULT_DEVICES

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MockDevice:
    """模拟设备状态"""

    def __init__(self, addr: int, device_type: TypeCode, name: str):
        self.addr = addr
        self.type = device_type
        self.name = name
        self.is_on = False
        self.position = 0 if device_type == TypeCode.COVER else None

    def __str__(self):
        return f"MockDevice({self.name}, addr={self.addr:08X}, type={self.type.name}, on={self.is_on}, pos={self.position})"


class MockDeoceanServer:
    """简化的德能森网关模拟服务器"""

    def __init__(self, host="localhost", port=9999):
        self.host = host
        self.port = port
        self.server_socket = None
        self.running = False
        self.clients = []
        self.devices: Dict[int, MockDevice] = {}

        # 直接从 const.py 加载设备配置
        self._load_devices_from_const()
        logger.info(f"Mock服务器初始化完成，加载了 {len(self.devices)} 个设备")

    def _load_devices_from_const(self):
        """从 const.py 的 DEFAULT_DEVICES 加载设备配置"""
        for name, typ, addr in split_txt_to_lines(DEFAULT_DEVICES, ",", 3):
            try:
                device_type = (
                    TypeCode.LIGHT if typ.lower() == "light" else TypeCode.COVER
                )
                device_addr = toInt(addr)
                self.devices[device_addr] = MockDevice(device_addr, device_type, name)
                logger.info(f"加载设备: {name} ({typ}) - {addr}")
            except Exception as e:
                logger.error(f"加载设备失败: {name} - {e}")

    def start(self):
        """启动服务器"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        self.running = True

        logger.info(f"🚀 Mock服务器启动: {self.host}:{self.port}")

        while self.running:
            try:
                client_socket, addr = self.server_socket.accept()
                logger.info(f"📱 客户端连接: {addr}")
                threading.Thread(
                    target=self.handle_client, args=(client_socket, addr), daemon=True
                ).start()
                self.clients.append(client_socket)
            except OSError:
                break

    def stop(self):
        """停止服务器"""
        self.running = False
        for client in self.clients:
            try:
                client.close()
            except:
                pass
        if self.server_socket:
            self.server_socket.close()

    def handle_client(self, client_socket, addr):
        """处理客户端连接"""
        try:
            client_socket.settimeout(1.0)  # 设置超时避免阻塞
            while self.running:
                try:
                    data = client_socket.recv(1024)
                    if not data:
                        break

                    for frame in parse_data(data):
                        response = self.process_frame(frame)
                        if response:
                            client_socket.send(response)
                except socket.timeout:
                    continue  # 超时继续循环

        except Exception as e:
            logger.error(f"客户端 {addr} 错误: {e}")
        finally:
            try:
                client_socket.close()
                if client_socket in self.clients:
                    self.clients.remove(client_socket)
            except:
                pass
            logger.info(f"📱 客户端 {addr} 断开")

    def process_frame(self, frame: DeoceanData) -> Optional[bytes]:
        """处理帧并生成响应"""
        if not frame.device_address:
            return None

        device_addr = frame.device_address.mac_address
        device = self.devices.get(device_addr)

        if not device:
            return None

        # 处理不同的功能码
        if frame.func_code == FuncCode.SYNC:
            return self._create_status_response(device)

        elif frame.func_code == FuncCode.SWITCH:
            self._update_device_state(device, frame.ctrl_code)
            return self._create_switch_response(device, frame.ctrl_code)

        elif (
            frame.func_code == FuncCode.COVER_POSITION and device.type == TypeCode.COVER
        ):
            if frame.position is not None:
                device.position = frame.position
                device.is_on = frame.position > 0
                return self._create_position_response(device, frame.position)

        return None

    def _update_device_state(self, device: MockDevice, ctrl_code: ControlCode):
        """更新设备状态"""
        if ctrl_code == ControlCode.LIGHT_ON:
            device.is_on = True
        elif ctrl_code == ControlCode.LIGHT_OFF:
            device.is_on = False
        elif ctrl_code == ControlCode.COVER_ON:
            device.is_on = True
            device.position = 100
        elif ctrl_code == ControlCode.COVER_OFF:
            device.is_on = False
            device.position = 0

    def _create_status_response(self, device: MockDevice) -> bytes:
        """创建状态响应"""
        if (
            device.type == TypeCode.COVER
            and device.position is not None
            and 0 < device.position < 100
        ):
            response = DeoceanData(FuncCode.POSITION_UPDATED)
            response.position = device.position
        else:
            response = DeoceanData(FuncCode.SWITCH_UPDATED)
            if device.type == TypeCode.LIGHT:
                response.ctrl_code = (
                    ControlCode.LIGHT_ON if device.is_on else ControlCode.LIGHT_OFF
                )
            else:  # COVER
                response.ctrl_code = (
                    ControlCode.COVER_ON if device.is_on else ControlCode.COVER_OFF
                )
                if device.position is not None:
                    response.position = device.position

        response.type = device.type
        response.device_address = DeviceAddr(device.addr)
        return response.encode()

    def _create_switch_response(
        self, device: MockDevice, ctrl_code: ControlCode
    ) -> bytes:
        """创建开关响应"""
        response = DeoceanData(FuncCode.SWITCH_UPDATED)
        response.type = device.type
        response.device_address = DeviceAddr(device.addr)
        response.ctrl_code = ctrl_code

        if device.type == TypeCode.COVER and device.position is not None:
            response.position = device.position

        return response.encode()

    def _create_position_response(self, device: MockDevice, position: int) -> bytes:
        """创建位置响应"""
        response = DeoceanData(FuncCode.POSITION_UPDATED)
        response.type = device.type
        response.device_address = DeviceAddr(device.addr)
        response.position = position
        return response.encode()


if __name__ == "__main__":
    print("🚀 德能森Mock服务器")
    print("📍 localhost:9999")
    print("📋 使用 const.py 中的设备配置")
    print("开启 Ctrl+C 停止")
    print("-" * 40)

    server = MockDeoceanServer()
    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()
        print("All done!")
