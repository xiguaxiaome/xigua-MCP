# vision_tool.py
import os
import cv2
import base64
import logging
import platform
import time
import threading
from typing import Optional
from mcp.server.fastmcp import FastMCP
from openai import OpenAI, APIConnectionError, APIError

# 配置结构化日志
logger = logging.getLogger("VisionTool")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
DASHSCOPE_API_KEY   = os.environ.get("DASHSCOPE_API_KEY")
# 带自动关闭的摄像头管理器
class CameraManager:
    _instance = None
    _lock = threading.Lock()
    _last_used = 0
    IDLE_TIMEOUT = 3  # 3秒无操作自动关闭
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._cap = None
                cls._instance._init_time = 0
                cls._instance._is_preview_active = False # 新增标志，用于跟踪预览窗口是否打开
                cls._instance._preview_thread = None # 用于存储预览线程
                cls._instance._preview_stop_event = threading.Event() # 用于控制预览线程的停止
        return cls._instance
    
    def get_camera(self):
        """获取摄像头实例，如果闲置超时则重新初始化"""
        current_time = time.time()
        
        # 检查是否需要重新初始化
        if self._cap is None or not self._cap.isOpened():
            self._init_camera()
        # 只有在预览不活跃且超时时才重新初始化，或者在预览线程已停止时
        elif current_time - self._last_used > self.IDLE_TIMEOUT and not self._is_preview_active and \
             (self._preview_thread is None or not self._preview_thread.is_alive()): 
            logger.info("摄像头闲置超时，重新初始化")
            self.release()
            self._init_camera()
        
        self._last_used = current_time
        return self._cap
    
    def _init_camera(self):
        """初始化摄像头"""
        if platform.system() == 'Darwin':
            os.environ['OBJC_DISABLE_INITIALIZE_FORK_SAFETY'] = 'YES'
        
        self._cap = cv2.VideoCapture(0)
        if not self._cap.isOpened():
            logger.error("摄像头访问被拒绝，请检查系统权限")
            raise PermissionError("Camera access denied")
        
        # 优化摄像头参数
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self._cap.set(cv2.CAP_PROP_FPS, 30)
        # 设置缓冲区大小为1，确保获取最新帧
        self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        logger.info("摄像头初始化完成")
    
    def get_frame(self) -> Optional[bytes]:
        """获取当前帧，确保刷新缓冲区获取最新图像"""
        cap = self.get_camera()
        
        # 刷新缓冲区，丢弃旧帧
        for _ in range(2):
            cap.grab()
        
        ret, frame = cap.read()
        if not ret:
            return None
        
        # 单次压缩
        _, buffer = cv2.imencode('.jpg', frame, [
            cv2.IMWRITE_JPEG_QUALITY, 75,
            cv2.IMWRITE_JPEG_OPTIMIZE, 1
        ])
        return buffer

    def get_raw_frame(self):
        """获取原始帧（用于预览）"""
        cap = self.get_camera()
        ret, frame = cap.read()
        if not ret:
            return None
        return frame
    
    def release(self):
        """释放摄像头资源"""
        if self._cap and self._cap.isOpened():
            self._cap.release()
            self._cap = None
            logger.info("摄像头资源已释放")
    
    def __del__(self):
        self.release()

# 带时间验证的API客户端
class VisionAnalyzer:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._init_client()
        return cls._instance
    
    def _init_client(self):
        # 请替换为你的实际API密钥
        api_key = DASHSCOPE_API_KEY
        if not api_key:
            raise ValueError("未设置DASHSCOPE_API_KEY")
        
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        self.cache = {}
        self.cache_lock = threading.Lock()
        logger.info("API客户端初始化完成")

    def analyze_image(self, image_data: str, timestamp: float) -> dict:
        """带时间验证的图像分析"""
        # 使用图像哈希+时间戳作为缓存键
        cache_key = f"{hash(image_data)}-{timestamp}"
        
        with self.cache_lock:
            if cache_key in self.cache:
                logger.debug("使用缓存结果")
                return self.cache[cache_key]
        
        try:
            start_time = time.time()
            
            response = self.client.chat.completions.create(
                model="qwen-vl-plus",
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "用可爱的语气简单描述图片内容"},
                        {"type": "image_url", 
                         "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
                    ]
                }],
                timeout=8
            )
            
            result_text = response.choices[0].message.content[:500]
            
            # 添加不耐烦语气
            if "这不就是" not in result_text:
                result_text = "害，这不就是" + result_text.lstrip("这是")
            
            result = {
                "success": True,
                "result": result_text
            }
            
            with self.cache_lock:
                self.cache[cache_key] = result
                if len(self.cache) > 20:  # 限制缓存大小
                    self.cache.pop(next(iter(self.cache)))
            
            logger.info(f"API调用耗时: {time.time()-start_time:.2f}s")
            return result
        except (APIConnectionError, APIError) as e:
            logger.error(f"API错误: {str(e)}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"分析异常: {str(e)}")
            return {"success": False, "error": "分析失败"}

# 视觉系统
class VisionSystem:
    def __init__(self):
        self.camera = CameraManager()
        self.analyzer = VisionAnalyzer()
        self.preview_window_name = "Camera Preview" # 统一窗口名称
    
    def capture_image_with_preview(self, countdown_seconds: int = 3) -> Optional[str]:
        """
        显示实时预览窗口，进行倒计时，然后捕获图像。
        """
        try:
            # 在捕获图像前，关闭任何正在运行的预览窗口
            if self.camera._is_preview_active:
                logger.info("检测到活跃的预览窗口，正在关闭以进行图像捕获。")
                self.close_camera_preview()
                time.sleep(0.2) # 给予足够时间让窗口和线程关闭

            cap = self.camera.get_camera()
            if not cap.isOpened():
                logger.error("摄像头未打开，无法进行预览和捕获。")
                return None

            self.camera._is_preview_active = True # 设置预览活跃标志
            cv2.namedWindow(self.preview_window_name, cv2.WINDOW_AUTOSIZE)
            # 尝试将窗口置于最前（并非所有OS都支持）
            cv2.setWindowProperty(self.preview_window_name, cv2.WND_PROP_TOPMOST, 1)
            cv2.waitKey(1) # 强制刷新窗口，有时有助于显示

            start_time = time.time()
            captured_frame_buffer = None

            while True:
                ret, frame = cap.read()
                if not ret:
                    logger.warning("无法读取摄像头帧。")
                    break

                current_time = time.time()
                elapsed_time = current_time - start_time
                remaining_time = max(0, countdown_seconds - int(elapsed_time))

                # 在帧上显示倒计时
                font = cv2.FONT_HERSHEY_SIMPLEX
                text_position = (50, 50)
                font_scale = 1.5
                font_color = (0, 0, 255) # 红色
                line_type = 2

                if remaining_time > 0:
                    cv2.putText(frame, f"Capturing in: {remaining_time}s", text_position, font, font_scale, font_color, line_type)
                else:
                    cv2.putText(frame, "SMILE!", text_position, font, font_scale, (0, 255, 0), line_type) # 绿色

                cv2.imshow(self.preview_window_name, frame)

                if remaining_time <= 0 and captured_frame_buffer is None:
                    # 倒计时结束，捕获最终帧
                    _, buffer = cv2.imencode('.jpg', frame, [
                        cv2.IMWRITE_JPEG_QUALITY, 75,
                        cv2.IMWRITE_JPEG_OPTIMIZE, 1
                    ])
                    captured_frame_buffer = buffer
                    # 保持窗口显示一小段时间，让用户看到“SMILE!”
                    time.sleep(0.5) 
                    break # 捕获后退出循环

                # 检测按键，允许用户提前退出或取消
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q') or key == 27:  # 按 'q' 或 ESC 退出
                    logger.info("用户取消了图像捕获。")
                    break

            cv2.destroyWindow(self.preview_window_name) # 捕获完成后关闭窗口
            self.camera._is_preview_active = False # 重置预览活跃标志
            
            if captured_frame_buffer is not None:
                image_data = base64.b64encode(captured_frame_buffer).decode('utf-8')
                logger.info(f"图像捕获耗时: {time.time()-start_time:.2f}s (含预览)")
                return image_data
            else:
                logger.warning("未捕获到图像。")
                return None

        except Exception as e:
            logger.error(f"捕获异常: {str(e)}", exc_info=True)
            if cv2.getWindowProperty(self.preview_window_name, cv2.WND_PROP_VISIBLE) >= 1:
                cv2.destroyWindow(self.preview_window_name)
            self.camera._is_preview_active = False # 确保异常时也重置标志
            return None

    def _preview_loop(self):
        """
        在单独线程中运行的摄像头预览循环。
        """
        cap = self.camera.get_camera()
        if not cap.isOpened():
            logger.error("预览线程：摄像头未打开。")
            self.camera._is_preview_active = False
            return

        cv2.namedWindow(self.preview_window_name, cv2.WINDOW_AUTOSIZE)
        cv2.setWindowProperty(self.preview_window_name, cv2.WND_PROP_TOPMOST, 1)
        cv2.waitKey(1) # 强制刷新窗口

        logger.info("预览线程：摄像头预览循环启动。")
        while self.camera._is_preview_active and not self.camera._preview_stop_event.is_set():
            ret, frame = cap.read()
            if not ret:
                logger.warning("预览线程：无法读取摄像头帧，预览将关闭。")
                break
            
            cv2.imshow(self.preview_window_name, frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == 27: # 允许用户通过 'q' 或 ESC 关闭
                logger.info("预览线程：用户通过按键关闭了预览。")
                break
            
            # 检查窗口是否被用户关闭
            if cv2.getWindowProperty(self.preview_window_name, cv2.WND_PROP_VISIBLE) < 1:
                logger.info("预览线程：窗口被用户关闭。")
                break

        logger.info("预览线程：摄像头预览循环结束。")
        # 循环结束时，执行清理
        self.close_camera_preview()


    def open_camera_preview(self) -> dict:
        """
        打开摄像头实时预览窗口。此函数会立即返回成功，预览在后台运行。
        """
        try:
            if self.camera._is_preview_active and self.camera._preview_thread and self.camera._preview_thread.is_alive():
                logger.info("摄像头预览已打开且正在运行。")
                return {"success": True, "result": "摄像头预览已打开"}

            cap = self.camera.get_camera()
            if not cap.isOpened():
                logger.error("摄像头未打开，无法打开预览。")
                return {"success": False, "error": "摄像头未打开"}

            # 确保在启动新预览前停止旧的
            # 这一步在 _preview_loop 启动前执行，确保摄像头资源被正确释放
            if self.camera._is_preview_active:
                self.close_camera_preview()
                time.sleep(0.1) # 稍作等待

            self.camera._is_preview_active = True # 设置预览活跃标志
            self.camera._preview_stop_event.clear() # 清除停止事件

            # 在单独的线程中运行预览循环
            self.camera._preview_thread = threading.Thread(target=self._preview_loop, daemon=True)
            self.camera._preview_thread.start()
            
            logger.info("摄像头预览已成功启动（后台线程）。")
            return {"success": True, "result": "摄像头预览已成功打开"}

        except Exception as e:
            logger.error(f"打开摄像头预览异常: {str(e)}", exc_info=True)
            self.camera._is_preview_active = False # 确保异常时也重置标志
            self.camera._preview_stop_event.set() # 确保事件被设置
            # 尝试销毁窗口和释放资源，以防万一
            if cv2.getWindowProperty(self.preview_window_name, cv2.WND_PROP_VISIBLE) >= 1:
                cv2.destroyWindow(self.preview_window_name)
            self.camera.release()
            return {"success": False, "error": f"打开预览失败: {str(e)}"}

    def close_camera_preview(self) -> dict:
        """
        关闭摄像头实时预览窗口并释放资源。
        """
        try:
            if not self.camera._is_preview_active:
                logger.info("摄像头预览未打开。")
                return {"success": True, "result": "摄像头预览未打开"}

            self.camera._preview_stop_event.set() # 设置事件，通知预览循环停止
            
            # 等待预览线程结束（最多等待1秒）
            if self.camera._preview_thread and self.camera._preview_thread.is_alive():
                logger.info("等待预览线程结束...")
                self.camera._preview_thread.join(timeout=1)
                if self.camera._preview_thread.is_alive():
                    logger.warning("预览线程未能及时停止。")
            
            # 确保窗口被销毁
            if cv2.getWindowProperty(self.preview_window_name, cv2.WND_PROP_VISIBLE) >= 1:
                cv2.destroyWindow(self.preview_window_name)
                cv2.waitKey(1) # 确保事件被处理
                time.sleep(0.1) # 稍作等待

            self.camera._is_preview_active = False # 重置预览活跃标志
            self.camera.release() # 确保释放摄像头资源
            logger.info("摄像头预览窗口已关闭，资源已释放。")
            return {"success": True, "result": "摄像头预览已成功关闭"}
        except Exception as e:
            logger.error(f"关闭摄像头预览异常: {str(e)}", exc_info=True)
            return {"success": False, "error": f"关闭预览失败: {str(e)}"}


def register_vision_tools(mcp: FastMCP):
    @mcp.tool()
    def vision_assistant(command: str) -> dict:
        """
        视觉感知系统
        命令示例：看看这是什么/描述当前场景/睁开眼看看
        
        返回格式：
        {
            "success": bool,     # 是否执行成功
            "result": str,       # 分析结果文本
            "error": str         # 错误信息（可选）
        }
        """
        # 快速命令检查
        keywords = ("看", "查看", "睁开", "描述", "什么", "东西")
        if not any(kw in command for kw in keywords):
            return {"success": False, "error": "无效命令"}
        
        try:
            vs = VisionSystem()
            start_time = time.time()
            
            # 调用带预览和倒计时的捕获方法
            if image_data := vs.capture_image_with_preview(countdown_seconds=3):
                # 使用当前时间戳确保每次调用都是唯一的
                timestamp = time.time()
                result = vs.analyzer.analyze_image(image_data, timestamp)
                total_time = time.time() - start_time
                logger.info(f"总处理时间: {total_time:.2f}s")
                return result
            
            return {"success": False, "error": "图像捕获失败或用户取消"}
        except Exception as e:
            logger.error(f"系统错误: {str(e)}", exc_info=True)
            return {"success": False, "error": "内部错误"}

    @mcp.tool()
    def open_camera_preview_tool() -> dict:
        """
        打开摄像头实时预览窗口。此工具会立即返回成功，预览在后台运行。
        当用户说“打开摄像头”、“打开预览”等时调用。
        
        返回格式：
        {
            "success": bool,     # 是否执行成功
            "result": str,       # 操作结果文本
            "error": str         # 错误信息（可选）
        }
        """
        vs = VisionSystem()
        return vs.open_camera_preview()

    @mcp.tool()
    def close_camera_preview_tool() -> dict:
        """
        关闭摄像头实时预览窗口。
        当用户说“关闭摄像头”、“关闭预览”等时调用。
        
        返回格式：
        {
            "success": bool,     # 是否执行成功
            "result": str,       # 操作结果文本
            "error": str         # 错误信息（可选）
        }
        """
        vs = VisionSystem()
        return vs.close_camera_preview()