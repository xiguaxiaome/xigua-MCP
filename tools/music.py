from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.common.action_chains import ActionChains
import time
import ctypes
import os
from mcp.server.fastmcp import FastMCP

# 全局变量，用于存储WebDriver实例，以便在工具函数中重用
driver_instance = None
EDGE_DRIVER_PATH  = os.environ.get("EDGE_DRIVER_PATH")
def get_driver():
    """获取或初始化Edge WebDriver实例"""
    global driver_instance
    if driver_instance is None:
        edge_options = EdgeOptions()
        edge_options.add_argument("--disable-blink-features=AutomationControlled")
        edge_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        edge_options.add_argument("--start-maximized")
        service = EdgeService(executable_path=EDGE_DRIVER_PATH )
        driver_instance = webdriver.Edge(service=service, options=edge_options)
        print("WebDriver实例已初始化。")
    return driver_instance

def close_popup(driver):
    """关闭GD音乐台的公告弹窗"""
    try:
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".layui-layer-dialog"))
        )
        driver.find_element(By.CSS_SELECTOR, ".layui-layer-close1").click()
        print("已关闭公告弹窗")
        time.sleep(1)
    except:
        print("未检测到公告弹窗")

def register_music_tools(mcp: FastMCP):
    """
    注册音乐播放相关的MCP工具函数。
    """
    @mcp.tool()
    def play_web_music(song_name: str) -> dict:
        """
        在GD音乐台搜索并播放指定歌曲。
        浏览器在播放后不会关闭。

        参数:
        - song_name: 要搜索的歌曲名称。

        返回:
        - 操作结果状态和信息。
        """
        driver = get_driver()
        try:
            # 如果当前不在音乐台页面，则导航到该页面
            if "music.gdstudio.xyz" not in driver.current_url:
                driver.get("https://music.gdstudio.xyz/")
                print("正在打开GD音乐台...")
                close_popup(driver) # 导航后尝试关闭弹窗

            # 确保进入搜索界面
            try:
                WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-action="search"]'))
                ).click()
                print("已进入搜索界面")
            except Exception as e:
                print(f"未能点击搜索按钮，可能已在搜索界面或元素不可用: {e}")

            # 确保搜索输入框是可见且可交互的
            search_input = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.ID, "search-wd"))
            )
            search_input.clear()
            search_input.send_keys(song_name)
            print(f"正在搜索歌曲: {song_name}")

            # 确保搜索按钮是可见且可交互的
            submit_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, '.search-submit'))
            )
            submit_btn.click()

            # 等待搜索结果加载
            WebDriverWait(driver, 15).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, ".list-item[data-no]"))
            )
            print("搜索结果已加载")

            # 定位第一个可播放的音乐项的父元素（.list-item）
            first_song_item = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".list-item[data-no]"))
            )

            # 滚动到元素并高亮显示
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", first_song_item)
            driver.execute_script("arguments[0].style.border='2px solid red';", first_song_item)
            time.sleep(1)

            # 鼠标悬停在列表项上，使播放按钮可见
            ActionChains(driver).move_to_element(first_song_item).perform()
            print("已悬停鼠标，尝试显示播放按钮")
            time.sleep(3)

            # 现在等待播放按钮变为可点击
            play_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".list-item[data-no] .icon-play"))
            )

            # 使用JavaScript点击播放按钮
            driver.execute_script("arguments[0].click();", play_button)
            print("已点击播放按钮")

            # 验证是否播放成功（检查播放器状态）
            WebDriverWait(driver, 15).until(
                lambda d: "暂停" in d.find_element(By.CSS_SELECTOR, ".btn-play").get_attribute("title") or \
                          d.find_element(By.CSS_SELECTOR, ".btn-play").get_attribute("class").endswith("icon-pause")
            )
            print(f"歌曲 '{song_name}' 已开始播放。")
            return {"success": True, "message": f"歌曲 '{song_name}' 已成功播放。"}

        except Exception as e:
            print(f"播放失败: {str(e)}")
            # 保存截图和页面源码用于调试
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            
            return {"success": False, "message": f"播放歌曲 '{song_name}' 失败: {str(e)}", "debug_files": [f"error_{timestamp}.png", f"page_source_{timestamp}.html"]}

    @mcp.tool()
    def close_browser() -> dict:
        """
        关闭所有由该脚本打开的浏览器窗口。

        返回:
        - 操作结果状态。
        """
        global driver_instance
        if driver_instance:
            driver_instance.quit()
            driver_instance = None
            print("浏览器已关闭。")
            return {"success": True, "message": "浏览器已关闭。"}
        else:
            return {"success": False, "message": "没有活动的浏览器实例可关闭。"}

