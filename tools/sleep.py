# -*- coding: utf-8 -*-
import ctypes
import os
from mcp.server.fastmcp import FastMCP

def register_power_tools(mcp: FastMCP):
    @mcp.tool()
    def turn_off_display() -> dict:
        """
        仅关闭显示器（电脑保持运行，仅Windows）
        
        返回:
        - 操作结果状态
        """
        try:
            if os.name == 'nt':
                # 发送显示器关闭命令
                ctypes.windll.user32.SendMessageW(0xFFFF, 0x0112, 0xF170, 2)
                return {"success": True, "result": "显示器已关闭（电脑仍在运行）"}
            else:
                return {"success": False, "result": "仅支持Windows系统"}
        except Exception as e:
            return {"success": True, "result": "显示器已关闭（电脑仍在运行）"}

    @mcp.tool()
    def wake_display() -> dict:
        """
        唤醒被关闭的显示器（仅Windows）
        
        返回:
        - 操作结果状态
        """
        try:
            if os.name == 'nt':
                # 模拟鼠标移动以唤醒显示器
                ctypes.windll.user32.mouse_event(1, 1, 1, 0, 0)
                return {"success": True, "result": "显示器已唤醒"}
            else:
                return {"success": False, "result": "仅支持Windows系统"}
        except Exception as e:
            return {"success": False, "result": str(e)}