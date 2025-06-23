# -*- coding: utf-8 -*-
import logging
import requests
import psutil
import os
import sys
import subprocess
import webbrowser
import tempfile
import time
import pyautogui
from pathlib import Path
from mcp.server.fastmcp import FastMCP
# 测试中，还没实现完


logger = logging.getLogger('system_tools')


# Fix UTF-8 encoding for Windows console (from original windows_controller.py)
if sys.platform == 'win32':
    sys.stderr.reconfigure(encoding='utf-8')
    sys.stdout.reconfigure(encoding='utf-8')

def get_desktop_path():
    """获取当前用户的桌面路径"""
    return Path.home() / "Desktop"

def register_system_tools(mcp: FastMCP):
    @mcp.tool()
    def get_server_status() -> dict:
        """
        获取服务器状态监控信息。
        返回:
        - 包含CPU、内存、磁盘等使用情况的字典
        """
        try:
            # CPU信息
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()

            # 内存信息
            memory = psutil.virtual_memory()
            memory_total = memory.total / (1024 * 1024 * 1024)  # GB
            memory_used = memory.used / (1024 * 1024 * 1024)    # GB
            memory_percent = memory.percent

            # 磁盘信息
            disk = psutil.disk_usage('/')
            disk_total = disk.total / (1024 * 1024 * 1024)      # GB
            disk_used = disk.used / (1024 * 1024 * 1024)        # GB
            disk_percent = disk.percent

            # 系统启动时间
            boot_time = psutil.boot_time()

            return {
                "success": True,
                "result": {
                    "cpu": {
                        "usage_percent": cpu_percent,
                        "core_count": cpu_count
                    },
                    "memory": {
                        "total_gb": round(memory_total, 2),
                        "used_gb": round(memory_used, 2),
                        "usage_percent": memory_percent
                    },
                    "disk": {
                        "total_gb": round(disk_total, 2),
                        "used_gb": round(disk_used, 2),
                        "usage_percent": disk_percent
                    },
                    "system": {
                        "boot_time": boot_time
                    }
                }
            }
        except Exception as e:
            logger.error(f"获取服务器状态失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    @mcp.tool()
    def open_notepad_with_text(text: str = "", filename: str = None) -> dict:
        """
        Open Notepad with text and optionally save to a specific file.
        Args:
            text: The text to display in Notepad
            filename: If provided, save to this file on desktop (e.g., "poem.txt")
        Returns:
            dict: {"success": bool, "filepath": str (if saved), "error": str (if failed)}
        """
        try:
            if filename:
                # 保存到桌面指定文件
                desktop = get_desktop_path()
                filepath = desktop / filename
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(text)
                subprocess.Popen(['notepad.exe', str(filepath)])
                logger.info(f"Opened Notepad with file: {filepath}")
                return {"success": True, "filepath": str(filepath)}
            else:
                # 创建临时文件
                with tempfile.NamedTemporaryFile(
                    mode='w',
                    encoding='utf-8',
                    suffix='.txt',
                    delete=False,
                    prefix='notepad_'
                ) as f:
                    f.write(text)
                    temp_path = f.name
                subprocess.Popen(['notepad.exe', temp_path])
                logger.info(f"Opened Notepad with temporary file: {temp_path}")
                return {"success": True, "filepath": temp_path}
        except Exception as e:
            logger.error(f"Failed to open Notepad with text: {str(e)}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    def open_program(program_name: str) -> dict:
        """
        Open common Windows programs. Supported programs:
        - 'notepad' (记事本)
        - 'explorer' (文件资源管理器)
        - 'cmd' (命令提示符)
        - 'calculator' (计算器)
        - 'control' (控制面板)
        - 'taskmgr' (任务管理器)
        - 'mspaint' (画图)
        - 'wordpad' (写字板)
        - 'wechat' (微信)
        """
        programs = {
            'notepad': 'notepad.exe',
            'explorer': 'explorer.exe',
            'cmd': 'cmd.exe',
            'calculator': 'calc.exe',
            'control': 'control.exe',
            'taskmgr': 'taskmgr.exe',
            'mspaint': 'mspaint.exe',
            'wordpad': 'write.exe',
            'wechat': r'"D:\\WeChat\\WeChat.exe"'
        }

        program_name_lower = program_name.lower()
        if program_name_lower not in programs:
            return {"success": False, "error": f"Unsupported program: {program_name}"}

        try:
            if program_name_lower == 'wechat':
                subprocess.Popen(programs['wechat'], shell=True)
            else:
                subprocess.Popen(programs[program_name_lower])

            logger.info(f"Successfully opened {program_name}")
            return {"success": True}
        except Exception as e:
            logger.error(f"Failed to open {program_name}: {str(e)}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    def close_program(program_name: str) -> dict:
        """
        Close a running program by its process name.
        Supported programs: 'calculator', 'notepad', 'mspaint', etc.
        """
        process_names = {
            'calculator': 'Calculator.exe',
            'notepad': 'notepad.exe',
            'mspaint': 'mspaint.exe',
            'wordpad': 'write.exe',
            'wechat': 'WeChat.exe'
        }

        program_name_lower = program_name.lower()
        if program_name_lower not in process_names:
            return {"success": False, "error": f"Unsupported program: {program_name}"}

        try:
            process_name = process_names[program_name_lower]
            for proc in psutil.process_iter(['name']):
                if proc.info['name'] == process_name:
                    proc.kill()

            logger.info(f"Successfully closed {program_name}")
            return {"success": True}
        except Exception as e:
            logger.error(f"Failed to close {program_name}: {str(e)}")
            return {"success": False, "error": str(e)}



    @mcp.tool()
    def show_desktop() -> dict:
        """Minimize all windows to show the desktop (Win+D equivalent)."""
        try:
            pyautogui.hotkey('win', 'd')
            logger.info("Showing desktop")
            return {"success": True}
        except Exception as e:
            logger.error(f"Failed to show desktop: {str(e)}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    def lock_screen() -> dict:
        """Lock the Windows screen immediately."""
        try:
            os.system('rundll32.exe user32.dll,LockWorkStation')
            logger.info("Screen locked successfully")
            return {"success": True}
        except Exception as e:
            logger.error(f"Failed to lock screen: {str(e)}")
            return {"success": False, "error": str(e)}



    @mcp.tool()
    def run_command(command: str) -> dict:
        """
        Run a Windows command or open a specific file/path.
        Examples:
        - 'C:\\Program Files\\MyApp\\app.exe'
        - 'shell:startup' (opens the startup folder)
        - 'ms-settings:' (opens Windows settings)
        """
        try:
            os.system(f'start {command}')
            logger.info(f"Executed command: {command}")
            return {"success": True}
        except Exception as e:
            logger.error(f"Failed to execute command {command}: {str(e)}")
            return {"success": False, "error": str(e)}