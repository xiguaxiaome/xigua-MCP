# -*- coding: utf-8 -*-
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.edge.service import Service as EdgeService
import json
import os
import time
from typing import Dict
from mcp.server.fastmcp import FastMCP

# 配置文件路径
COOKIES_FILE = "bilibili_cookies.json"

# ------------------------- 辅助函数 -------------------------
def save_cookies(driver: webdriver.Edge) -> bool:
    """保存当前Cookies到文件"""
    try:
        cookies = driver.get_cookies()
        with open(COOKIES_FILE, 'w') as f:
            json.dump(cookies, f)
        return True
    except Exception as e:
        print(f"保存Cookies失败: {e}")
        return False

def load_cookies(driver: webdriver.Edge) -> bool:
    """从文件加载Cookies"""
    if not os.path.exists(COOKIES_FILE):
        return False
        
    try:
        with open(COOKIES_FILE, 'r') as f:
            cookies = json.load(f)
        
        driver.get("https://www.bilibili.com")
        driver.delete_all_cookies()
        
        for cookie in cookies:
            # 确保cookie的domain与当前URL匹配，否则可能无法添加
            # Bilibili的domain通常是 .bilibili.com
            if 'bilibili.com' not in cookie.get('domain', ''):
                cookie['domain'] = '.bilibili.com'
            # Selenium的add_cookie方法要求'path'和'secure'键存在
            if 'path' not in cookie:
                cookie['path'] = '/'
            if 'secure' not in cookie:
                cookie['secure'] = False
            
            # 某些cookie可能没有expiry，需要处理
            if 'expiry' in cookie:
                cookie['expiry'] = int(cookie['expiry']) # 确保expiry是整数
            
            driver.add_cookie(cookie)
        return True
    except Exception as e:
        print(f"加载Cookies失败: {e}")
        return False


def auto_login(driver: webdriver.Edge) -> bool:
    """自动登录流程（优化版）"""
    if load_cookies(driver):
        driver.get("https://www.bilibili.com")
        # 短暂等待页面加载，以便cookie生效
        time.sleep(2) 
        
        try:
            # 快速检查是否已登录（通过检查右上角是否存在头像或用户名）
            # 增加对登录状态的更精确判断，例如检查用户中心链接
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".header-avatar, .header-avatar-wrap, .nav-user-center"))
            )
            # 再次访问B站主页，确保登录状态稳定
            driver.get("https://www.bilibili.com")
            time.sleep(1)
            return True
        except:
            # 如果检查失败，说明cookie可能失效
            if os.path.exists(COOKIES_FILE):
                os.remove(COOKIES_FILE)
            print("Cookie 已失效或未登录，需要重新登录")
    
    return manual_login(driver)

def manual_login(driver: webdriver.Edge) -> bool:
    """手动登录流程（优化版）"""
    try:
        print("请手动完成登录（30秒内完成）...")
        driver.get("https://passport.bilibili.com/login")
        
        # 等待登录成功（检查是否跳转到非登录页面且URL包含bilibili.com）
        WebDriverWait(driver, 30).until(
            lambda d: "login" not in d.current_url and "bilibili.com" in d.current_url
        )
        
        # 短暂等待确保登录状态完全加载
        time.sleep(2)
        save_cookies(driver)
        return True
    except Exception as e:
        print(f"登录失败或超时: {e}")
        return False

def init_driver() -> webdriver.Edge:
    """初始化浏览器驱动（防止自动关闭）"""
    options = webdriver.EdgeOptions()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_argument("--start-maximized")
    options.add_argument("--log-level=3")
    
    # 关键设置：防止浏览器自动关闭
    options.add_experimental_option("detach", True)  # 保持浏览器打开
    
    # 尝试指定msedgedriver.exe的路径，如果不在PATH中
    # service = EdgeService(executable_path="D:\\msedgedriver.exe")
    # driver = webdriver.Edge(service=service, options=options)
    
    # 推荐使用这种方式，如果msedgedriver.exe在系统PATH中，或者与脚本在同一目录
    driver = webdriver.Edge(options=options)
    driver.implicitly_wait(10) # 隐式等待，对所有查找元素生效
    return driver

def search_and_play_video(driver: webdriver.Edge, keyword: str) -> bool:
    """搜索并播放视频（只要打开视频就算成功）"""
    try:
        search_url = f"https://search.bilibili.com/all?keyword={keyword}"
        driver.get(search_url)
        
        # 确保搜索结果页面加载完成
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".bili-video-card"))
        )
        
        # 获取第一个视频卡片，并点击
        first_video = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, ".bili-video-card:first-child a"))
        )
        driver.execute_script("arguments[0].scrollIntoView();", first_video)
        time.sleep(1) # 短暂等待滚动完成
        driver.execute_script("arguments[0].click();", first_video)
        
        # 切换到新打开的视频页面窗口
        WebDriverWait(driver, 10).until(EC.number_of_windows_to_be(2))
        driver.switch_to.window(driver.window_handles[1])
        
        # 核心优化：只需确认视频播放器加载完成即可视为成功，立即返回True
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CLASS_NAME, "bpx-player-container"))
        )
        
        # 视频页面已加载，立即返回成功
        print("视频页面已成功加载。")
        
        # 后续操作（如全屏）是非阻塞的，即使失败也不影响函数返回的成功状态
        try:
            # 尝试点击播放按钮（如果视频未自动播放）
            play_button = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".bpx-player-ctrl-play"))
            )
            if play_button.get_attribute("data-state") == "pause": # 如果当前是暂停状态，则点击播放
                play_button.click()
                print("尝试点击播放按钮。")
        except:
            pass # 播放按钮可能不存在或已自动播放
            
        try:
            # 尝试全屏
            fullscreen_btn = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".bpx-player-ctrl-full"))
            )
            fullscreen_btn.click()
            print("尝试全屏播放。")
        except:
            print("全屏失败或已全屏。")
            pass # 即使全屏失败也不影响整体成功
        
        return True # 在视频播放器加载后立即返回成功
    
    except Exception as e:
        print(f"播放视频失败: {e}")
        return False

# ------------------------- MCP注册函数 -------------------------
def register_bilibili_tool(mcp: FastMCP):
    """注册B站视频播放功能到MCP"""
    
    @mcp.tool()
    def play_bilibili_video(keyword: str) -> Dict[str, str]:
        """
        在B站搜索并尝试全屏播放视频（成功后浏览器保持打开）
        
        参数:
        - keyword: 搜索关键词
        
        返回:
        - {"success": bool, "result": str}
        """
        driver = None
        try:
            # 初始化浏览器（设置detach=True防止自动关闭）
            driver = init_driver()
            
            # 登录
            if not auto_login(driver):
                # 登录失败时，关闭浏览器
                if driver:
                    driver.quit()
                return {"success": False, "result": "B站登录失败"}
            
            # 播放视频
            if not search_and_play_video(driver, keyword):
                # 视频播放失败时，关闭浏览器
                if driver:
                    driver.quit()
                return {"success": False, "result": "视频播放失败"}
            
            # 成功播放后，不关闭浏览器，直接返回成功
            # 因为 detach=True，浏览器会保持打开
            return {"success": True, "result": "视频已成功播放，浏览器保持打开"}
        
        except Exception as e:
            # 发生错误时仍然尝试关闭浏览器
            if driver:
                driver.quit()
            return {"success": False, "result": f"发生错误: {str(e)}"}