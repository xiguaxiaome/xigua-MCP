# -*- coding: utf-8 -*-
import webbrowser
import platform
import subprocess
import time # 用于演示，实际应用中可能不需要

from mcp.server.fastmcp import FastMCP

def register_web_tools(mcp: FastMCP):
    @mcp.tool()
    def open_webpage(url: str) -> dict:
        """
        打开指定的网页
        
        参数:
        - url: 要打开的网页地址
        
        返回:
        - 操作结果状态
        """
        try:
            # webbrowser.open_new_tab(url) 可以尝试在新标签页打开，但仍然无法控制
            webbrowser.open(url)
            return {"success": True, "result": f"成功打开网页: {url}"}
        except Exception as e:
            return {"success": False, "result": str(e)}

    @mcp.tool()
    def close_all_browser_process(browser_name: str = None) -> dict:
        """
        尝试关闭所有指定浏览器的进程。
        注意：这是一个非常粗暴的操作，会关闭所有该浏览器的窗口，
        可能导致用户数据丢失，且不保证能关闭通过 open_webpage 打开的特定标签页。
        
        参数:
        - browser_name: 要关闭的浏览器名称，例如 "chrome", "firefox", "safari", "edge"。
                        如果为 None，则尝试关闭常见的浏览器。
        
        返回:
        - 操作结果状态
        """
        system = platform.system()
        
        if browser_name:
            browsers_to_kill = [browser_name.lower()]
        else:
            # 默认尝试关闭一些常见的浏览器
            browsers_to_kill = ["chrome", "firefox", "safari", "msedge", "iexplore"]

        results = {}
        for b_name in browsers_to_kill:
            try:
                if system == "Windows":
                    # 对于 Windows，根据浏览器名称尝试不同的进程名
                    if b_name == "chrome":
                        process_name = "chrome.exe"
                    elif b_name == "firefox":
                        process_name = "firefox.exe"
                    elif b_name == "msedge":
                        process_name = "msedge.exe"
                    elif b_name == "iexplore":
                        process_name = "iexplore.exe"
                    else:
                        process_name = b_name + ".exe" # 尝试通用模式

                    subprocess.run(["taskkill", "/IM", process_name, "/F"], check=True, capture_output=True)
                    results[b_name] = {"success": True, "message": f"尝试关闭 {b_name} 进程成功。"}
                elif system == "Darwin": # macOS
                    if b_name == "chrome":
                        process_name = "Google Chrome"
                    elif b_name == "firefox":
                        process_name = "Firefox"
                    elif b_name == "safari":
                        process_name = "Safari"
                    else:
                        process_name = b_name # 尝试通用模式

                    subprocess.run(["killall", process_name], check=True, capture_output=True)
                    results[b_name] = {"success": True, "message": f"尝试关闭 {b_name} 进程成功。"}
                elif system == "Linux":
                    # Linux 类似 macOS，但进程名可能有所不同
                    if b_name == "chrome":
                        process_name = "chrome"
                    elif b_name == "firefox":
                        process_name = "firefox"
                    else:
                        process_name = b_name

                    subprocess.run(["killall", process_name], check=True, capture_output=True)
                    results[b_name] = {"success": True, "message": f"尝试关闭 {b_name} 进程成功。"}
                else:
                    results[b_name] = {"success": False, "message": f"不支持的操作系统: {system}"}
            except subprocess.CalledProcessError as e:
                results[b_name] = {"success": False, "message": f"关闭 {b_name} 进程失败: {e.stderr.decode().strip()}"}
            except Exception as e:
                results[b_name] = {"success": False, "message": f"关闭 {b_name} 进程时发生未知错误: {str(e)}"}
        
        return {"success": any(res["success"] for res in results.values()), "results": results}

# 示例用法 (假设 FastMCP 实例 mcp 已经创建)
# if __name__ == "__main__":
#     # 这是一个简化的 FastMCP 模拟，实际使用时需要 FastMCP 框架
#     class MockFastMCP:
#         def tool(self):
#             def decorator(func):
#                 print(f"Registered tool: {func.__name__}")
#                 return func
#             return decorator
#     
#     mock_mcp = MockFastMCP()
#     register_web_tools(mock_mcp)
#     
#     # 演示打开和关闭
#     print(mock_mcp.open_webpage("https://www.google.com"))
#     time.sleep(5) # 等待网页打开
#     print(mock_mcp.close_browser_process(browser_name="chrome")) # 尝试关闭 Chrome
#     # 或者尝试关闭所有常见的浏览器
#     # print(mock_mcp.close_browser_process())