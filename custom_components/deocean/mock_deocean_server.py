#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
德能森网关Mock服务器
用于测试Home Assistant集成，模拟真实的德能森网关行为
"""

import socket
import threading
import time
import struct
import logging
from typing import Dict, Optional
from hub import (
    DeoceanData, FuncCode, ControlCode, TypeCode, DeviceAddr, 
    toInt, parse_data, STOP_BIT
)

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
    """模拟德能森网关服务器"""
    
    def __init__(self, host='localhost', port=9999):
        self.host = host
        self.port = port
        self.server_socket = None
        self.running = False
        self.clients = []
        
        # 预定义一些测试设备
        self.devices: Dict[int, MockDevice] = {
            0x001E9A5D: MockDevice(0x001E9A5D, TypeCode.LIGHT, '公卫灯'),
            0x7554C701: MockDevice(0x7554C701, TypeCode.COVER, '客厅布帘'),
            0x12345678: MockDevice(0x12345678, TypeCode.LIGHT, '测试灯'),
            0x87654321: MockDevice(0x87654321, TypeCode.COVER, '测试窗帘'),
        }
        
    def start(self):
        """启动服务器"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        self.running = True
        
        logger.info(f"Mock德能森服务器启动在 {self.host}:{self.port}")
        logger.info("预定义设备:")
        for device in self.devices.values():
            logger.info(f"  - {device}")
            
        while self.running:
            try:
                client_socket, addr = self.server_socket.accept()
                logger.info(f"客户端连接: {addr}")
                client_thread = threading.Thread(
                    target=self.handle_client, 
                    args=(client_socket, addr)
                )
                client_thread.daemon = True
                client_thread.start()
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
            while self.running:
                data = client_socket.recv(1024)
                if not data:
                    break
                    
                logger.info(f"收到数据: {' '.join([f'{x:02X}' for x in data])}")
                
                # 解析接收到的数据
                for frame in parse_data(data):
                    logger.info(f"解析帧: {frame}")
                    response = self.process_frame(frame)
                    if response:
                        logger.info(f"发送响应: {' '.join([f'{x:02X}' for x in response])}")
                        client_socket.send(response)
                        
        except Exception as e:
            logger.error(f"处理客户端 {addr} 时出错: {e}")
        finally:
            try:
                client_socket.close()
            except:
                pass
            if client_socket in self.clients:
                self.clients.remove(client_socket)
            logger.info(f"客户端 {addr} 断开连接")
            
    def process_frame(self, frame: DeoceanData) -> Optional[bytes]:
        """处理接收到的帧并生成响应"""
        if not frame.device_address:
            return None
            
        device_addr = frame.device_address.mac_address
        device = self.devices.get(device_addr)
        
        if not device:
            logger.warning(f"未知设备地址: {device_addr:08X}")
            return None
            
        logger.info(f"处理设备 {device.name} 的请求")
        
        # 根据不同的功能码处理
        if frame.func_code == FuncCode.SYNC:
            # 状态同步请求
            return self.create_status_response(device)
            
        elif frame.func_code == FuncCode.SWITCH:
            # 开关控制
            if frame.ctrl_code == ControlCode.LIGHT_ON:
                device.is_on = True
            elif frame.ctrl_code == ControlCode.LIGHT_OFF:
                device.is_on = False
            elif frame.ctrl_code == ControlCode.COVER_ON:
                device.is_on = True
                device.position = 100
            elif frame.ctrl_code == ControlCode.COVER_OFF:
                device.is_on = False
                device.position = 0
                
            logger.info(f"设备状态更新: {device}")
            return self.create_switch_response(device, frame.ctrl_code)
            
        elif frame.func_code == FuncCode.COVER_POSITION:
            # 窗帘位置设置
            if device.type == TypeCode.COVER and frame.position is not None:
                device.position = frame.position
                device.is_on = frame.position > 0
                logger.info(f"窗帘位置设置为: {frame.position}%, 设备状态: {device}")
                return self.create_position_response(device, frame.position)
                
        return None
        
    def create_status_response(self, device: MockDevice) -> bytes:
        """创建状态响应"""
        if device.type == TypeCode.COVER and device.position is not None and 0 < device.position < 100:
            # 如果是窗帘且有中间位置，发送位置更新响应
            response = DeoceanData(FuncCode.POSITION_UPDATED)
            response.type = device.type
            response.device_address = DeviceAddr(device.addr)
            response.position = device.position
        else:
            # 否则发送开关状态响应
            response = DeoceanData(FuncCode.SWITCH_UPDATED)
            response.type = device.type
            response.device_address = DeviceAddr(device.addr)
            
            if device.type == TypeCode.LIGHT:
                response.ctrl_code = ControlCode.LIGHT_ON if device.is_on else ControlCode.LIGHT_OFF
            elif device.type == TypeCode.COVER:
                response.ctrl_code = ControlCode.COVER_ON if device.is_on else ControlCode.COVER_OFF
                if device.position is not None:
                    response.position = device.position
                
        return response.encode()
        
    def create_switch_response(self, device: MockDevice, ctrl_code: ControlCode) -> bytes:
        """创建开关响应"""
        response = DeoceanData(FuncCode.SWITCH_UPDATED)
        response.type = device.type
        response.device_address = DeviceAddr(device.addr)
        response.ctrl_code = ctrl_code
        
        if device.type == TypeCode.COVER and device.position is not None:
            response.position = device.position
            
        return response.encode()
        
    def create_position_response(self, device: MockDevice, position: int) -> bytes:
        """创建位置设置响应"""
        response = DeoceanData(FuncCode.POSITION_UPDATED)
        response.type = device.type
        response.device_address = DeviceAddr(device.addr)
        response.position = position
        
        return response.encode()

if __name__ == '__main__':
    print("🚀 启动Mock德能森服务器...")
    print("📍 地址: localhost:9999")
    print("🔧 用于测试Home Assistant德能森集成")
    print("⚡ 按 Ctrl+C 停止服务器")
    print("-" * 50)
    
    server = MockDeoceanServer()
    
    try:
        server.start()
    except KeyboardInterrupt:
        print("\n🛑 正在停止服务器...")
        server.stop()
        print("✅ 服务器已停止")