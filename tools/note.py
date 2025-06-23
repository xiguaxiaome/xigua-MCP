# -*- coding: utf-8 -*-
import datetime
import json
import os
import logging
from selenium import webdriver
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.common.exceptions import WebDriverException, SessionNotCreatedException
import time

logger = logging.getLogger('sticky_notes_manager')

# Edge WebDriver 配置
EDGE_DRIVER_PATH  = os.environ.get("EDGE_DRIVER_PATH")
_edge_driver_instance = None
_browser_initialized = False  # 标记浏览器是否已初始化

class StickyNoteManager:
    def __init__(self, data_file="sticky_notes.json", html_output_file="sticky_notes.html"):
        self.data_file = data_file
        self.html_output_file = html_output_file
        self.notes = []
        self.next_id = 1
        self._load_notes()
        
    def _load_notes(self):
        """从文件中加载便签数据"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.notes = data.get("notes", [])
                    # 确保旧数据有 importance 和 category 字段
                    for note in self.notes:
                        if "importance" not in note:
                            note["importance"] = "普通"
                        if "category" not in note:
                            note["category"] = "未分类"
                    if self.notes:
                        self.next_id = max(note["id"] for note in self.notes) + 1
                    else:
                        self.next_id = 1
                logger.info(f"已从 '{self.data_file}' 加载 {len(self.notes)} 条便签")
            except json.JSONDecodeError:
                logger.warning("便签数据文件损坏或为空，将创建新文件")
                self.notes = []
                self.next_id = 1
            except Exception as e:
                logger.error(f"加载便签数据失败: {e}")
                self.notes = []
                self.next_id = 1
        else:
            logger.info("便签数据文件不存在，将创建新文件")
            self.notes = []
            self.next_id = 1

    def _save_notes(self):
        """将便签数据保存到文件"""
        try:
            data = {"notes": self.notes}
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            logger.info(f"已保存 {len(self.notes)} 条便签到 '{self.data_file}'")
        except IOError as e:
            logger.error(f"保存便签数据失败: {e}")

    def _generate_timestamp(self):
        """生成当前时间戳"""
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _get_edge_driver(self):
        """
        获取或初始化 Edge WebDriver 实例
        """
        global _edge_driver_instance, _browser_initialized
        
        if _edge_driver_instance is not None:
            try:
                # 检查浏览器是否仍然可用
                _edge_driver_instance.current_url
                return _edge_driver_instance
            except WebDriverException:
                # 浏览器已关闭或崩溃，需要重新初始化
                _edge_driver_instance = None
        
        if _edge_driver_instance is None:
            try:
                edge_options = EdgeOptions()
                edge_options.add_argument("--disable-blink-features=AutomationControlled")
                edge_options.add_experimental_option("excludeSwitches", ["enable-automation"])
                edge_options.add_argument("--start-maximized")
                
                service = EdgeService(executable_path=EDGE_DRIVER_PATH)
                _edge_driver_instance = webdriver.Edge(service=service, options=edge_options)
                _browser_initialized = True
                logger.info("Edge浏览器已启动")
                return _edge_driver_instance
            except SessionNotCreatedException as e:
                logger.error(f"Edge浏览器启动失败：版本不匹配。请确保Edge浏览器和驱动版本一致。错误: {e}")
            except WebDriverException as e:
                logger.error(f"Edge浏览器启动失败：{e}")
            except Exception as e:
                logger.error(f"Edge浏览器启动失败：未知错误: {e}")
        return _edge_driver_instance

    def _refresh_browser_page(self, file_path: str):
        """
        刷新浏览器中的HTML页面
        """
        driver = self._get_edge_driver()
        if not driver:
            return {"success": False, "error": "无法启动Edge浏览器，请检查Edge驱动配置"}
        
        try:
            target_url = f"file://{os.path.abspath(file_path)}"
            current_url = driver.current_url if driver.current_url else ""
            
            if current_url == target_url:
                driver.refresh()
                logger.info("便签页面已刷新")
            else:
                driver.get(target_url)
                logger.info("便签页面已打开")
            
            time.sleep(0.5)  # 等待页面加载
            return {"success": True, "message": "便签显示已更新"}
        except WebDriverException as e:
            logger.error(f"浏览器操作失败：{e}")
            global _edge_driver_instance
            _edge_driver_instance = None  # 重置浏览器实例
            return {"success": False, "error": f"浏览器操作失败：{e}"}

    def add_note(self, content: str, importance: str = "普通", category: str = "未分类") -> dict:
        """
        添加新便签
        """
        if not content:
            return {"success": False, "error": "便签内容不能为空"}
        
        if importance not in ["普通", "重要", "紧急"]:
            importance = "普通"
        
        note = {
            "id": self.next_id,
            "content": content,
            "timestamp": self._generate_timestamp(),
            "importance": importance,
            "category": category
        }
        
        self.notes.append(note)
        self.next_id += 1
        self._save_notes()
        
        # 更新HTML
        html_result = self.generate_html_report(notes_to_display=self.notes)
        if not html_result["success"]:
            return html_result
        
        return {
            "success": True,
            "message": f"已成功添加便签(ID: {note['id']})",
            "note": note
        }

    def modify_note(self, note_id: int, new_content: str = None, 
                   new_importance: str = None, new_category: str = None) -> dict:
        """
        修改现有便签
        """
        note_found = False
        for note in self.notes:
            if note["id"] == note_id:
                note_found = True
                if new_content is not None:
                    note["content"] = new_content
                    note["timestamp"] = self._generate_timestamp()
                if new_importance is not None:
                    note["importance"] = new_importance
                if new_category is not None:
                    note["category"] = new_category
                break
        
        if not note_found:
            return {"success": False, "error": f"未找到ID为 {note_id} 的便签"}
        
        self._save_notes()
        
        # 更新HTML
        html_result = self.generate_html_report(notes_to_display=self.notes)
        if not html_result["success"]:
            return html_result
        
        return {
            "success": True,
            "message": f"已成功修改便签(ID: {note_id})",
            "updated_note": next((note for note in self.notes if note["id"] == note_id), None)
        }

    def delete_note(self, note_id: int) -> dict:
        """
        删除便签
        """
        initial_count = len(self.notes)
        self.notes = [note for note in self.notes if note["id"] != note_id]
        
        if len(self.notes) == initial_count:
            return {"success": False, "error": f"未找到ID为 {note_id} 的便签"}
        
        self._save_notes()
        
        # 更新HTML
        html_result = self.generate_html_report(notes_to_display=self.notes)
        if not html_result["success"]:
            return html_result
        
        return {
            "success": True,
            "message": f"已成功删除便签(ID: {note_id})",
            "remaining_notes": len(self.notes)
        }

    def search_notes(self, keyword: str = None, importance: str = None, category: str = None) -> dict:
        """
        搜索便签
        """
        matching_notes = self.notes
        
        if keyword:
            matching_notes = [
                note for note in matching_notes 
                if keyword.lower() in note["content"].lower()
            ]
        
        if importance:
            matching_notes = [
                note for note in matching_notes 
                if note.get("importance", "").lower() == importance.lower()
            ]
        
        if category:
            matching_notes = [
                note for note in matching_notes 
                if note.get("category", "").lower() == category.lower()
            ]
        
        # 更新HTML
        html_result = self.generate_html_report(notes_to_display=matching_notes)
        if not html_result["success"]:
            return html_result
        
        return {
            "success": True,
            "message": f"找到 {len(matching_notes)} 条匹配的便签",
            "matches": matching_notes
        }

    def list_all_notes(self) -> dict:
        """
        列出所有便签
        """
        # 更新HTML
        html_result = self.generate_html_report(notes_to_display=self.notes)
        if not html_result["success"]:
            return html_result
        
        return {
            "success": True,
            "message": f"共 {len(self.notes)} 条便签",
            "notes": self.notes
        }

    def generate_html_report(self, notes_to_display: list) -> dict:
        """
        生成HTML报告
        """
        try:
            with open(self.html_output_file, 'w', encoding='utf-8') as f:
                f.write(self._generate_html_content(notes_to_display))
            return {"success": True, "message": "HTML报告已生成"}
        except IOError as e:
            return {"success": False, "error": f"生成HTML文件失败: {e}"}

    def _generate_html_content(self, notes_to_display: list) -> str:
        """
        生成HTML内容
        """
        html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>我的便签</title>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;400;500;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
    <style>
        :root {
            --primary-color: #4361ee;
            --secondary-color: #3f37c9;
            --success-color: #4cc9f0;
            --danger-color: #f72585;
            --warning-color: #f8961e;
            --info-color: #4895ef;
            --light-color: #f8f9fa;
            --dark-color: #212529;
            
            --work-color: #4361ee;
            --life-color: #4cc9f0;
            --study-color: #7209b7;
            --other-color: #6c757d;
        }
        
        body {
            font-family: 'Noto Sans SC', sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f7fa;
            color: #333;
            line-height: 1.6;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        header {
            text-align: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 1px solid #e0e0e0;
        }
        
        h1 {
            color: var(--primary-color);
            font-weight: 700;
            margin-bottom: 10px;
            font-size: 2.5rem;
        }
        
        .subtitle {
            color: #6c757d;
            font-weight: 300;
            font-size: 1.1rem;
        }
        
        .stats {
            display: flex;
            justify-content: center;
            gap: 20px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }
        
        .stat-card {
            background: white;
            border-radius: 8px;
            padding: 15px 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            min-width: 120px;
            text-align: center;
        }
        
        .stat-value {
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--primary-color);
            margin-bottom: 5px;
        }
        
        .stat-label {
            font-size: 0.85rem;
            color: #6c757d;
        }
        
        .note-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 25px;
            margin-top: 20px;
        }
        
        .note-card {
            background: white;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
            transition: all 0.3s ease;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            height: 100%;
        }
        
        .note-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 20px rgba(0, 0, 0, 0.1);
        }
        
        .note-header {
            padding: 15px 20px;
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .note-id {
            font-size: 0.85rem;
            color: #6c757d;
            font-weight: 500;
        }
        
        .note-content {
            padding: 20px;
            flex-grow: 1;
            font-size: 1rem;
            color: #495057;
            border-bottom: 1px solid #f1f1f1;
        }
        
        .note-footer {
            padding: 15px 20px;
            background-color: #f8f9fa;
        }
        
        .note-timestamp {
            font-size: 0.8rem;
            color: #6c757d;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
        }
        
        .note-timestamp i {
            margin-right: 5px;
            font-size: 0.9rem;
        }
        
        .note-tags {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 10px;
        }
        
        .tag {
            font-size: 0.75rem;
            padding: 4px 10px;
            border-radius: 50px;
            font-weight: 500;
            display: inline-flex;
            align-items: center;
        }
        
        .importance-stars {
            display: flex;
            gap: 3px;
        }
        
        .star {
            color: #ffc107;
            font-size: 0.9rem;
        }
        
        .star.empty {
            color: #e0e0e0;
        }
        
        /* 重要性星级样式 */
        .importance-1 .star:nth-child(1) { color: #ffc107; }
        .importance-1 .star:nth-child(n+2) { color: #e0e0e0; }
        
        .importance-2 .star:nth-child(-n+2) { color: #ffc107; }
        .importance-2 .star:nth-child(n+3) { color: #e0e0e0; }
        
        .importance-3 .star { color: #ffc107; }
        
        /* 类别标签颜色 */
        .category-work {
            background-color: rgba(67, 97, 238, 0.1);
            color: var(--work-color);
            border: 1px solid rgba(67, 97, 238, 0.2);
        }
        
        .category-life {
            background-color: rgba(76, 201, 240, 0.1);
            color: var(--life-color);
            border: 1px solid rgba(76, 201, 240, 0.2);
        }
        
        .category-study {
            background-color: rgba(114, 9, 183, 0.1);
            color: var(--study-color);
            border: 1px solid rgba(114, 9, 183, 0.2);
        }
        .category-other {
            background-color: rgba(108, 117, 125, 0.1);
            color: var(--other-color);
            border: 1px solid rgba(108, 117, 125, 0.2);
        }
        
        .no-notes {
            text-align: center;
            padding: 50px 20px;
            grid-column: 1 / -1;
        }
        
        .no-notes i {
            font-size: 3rem;
            color: #adb5bd;
            margin-bottom: 15px;
        }
        
        .no-notes h3 {
            color: #6c757d;
            font-weight: 400;
            margin-bottom: 10px;
        }
        
        .no-notes p {
            color: #adb5bd;
            font-size: 0.9rem;
        }
        
        .search-info {
            text-align: center;
            margin-bottom: 20px;
            color: #6c757d;
            font-size: 0.9rem;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>我的便签</h1>
            <p class="subtitle">记录生活中的每一个重要时刻</p>
        </header>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-value">""" + str(len(self.notes)) + """</div>
                <div class="stat-label">总便签数</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">""" + str(len(notes_to_display)) + """</div>
                <div class="stat-label">当前显示</div>
            </div>
        </div>
        
        """ + (f'<div class="search-info">正在显示 {len(notes_to_display)} 条便签</div>' if len(notes_to_display) != len(self.notes) else '') + """
        
        <div class="note-grid">
"""

        if not notes_to_display:
            html += """
            <div class="no-notes">
                <i class="far fa-sticky-note"></i>
                <h3>没有找到便签</h3>
                <p>尝试修改搜索条件或添加新便签</p>
            </div>
            """
        else:
            for note in notes_to_display:
                # 对内容进行HTML转义
                escaped_content = note['content'].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&#039;')
                
                importance = note.get("importance", "普通")
                category = note.get("category", "未分类")
                
                # 确定重要性星级 (1-3星)
                importance_level = 1
                if importance.lower() == "重要":
                    importance_level = 2
                elif importance.lower() == "紧急":
                    importance_level = 3
                    
                # 确定类别样式
                category_class = "category-other"
                if category.lower() == "工作":
                    category_class = "category-work"
                elif category.lower() == "生活":
                    category_class = "category-life"
                elif category.lower() == "学习":
                    category_class = "category-study"
                    
                html += f"""
                <div class="note-card">
                    <div class="note-header">
                        <span class="note-id">#{note['id']}</span>
                        <div class="importance-stars importance-{importance_level}">
                            <i class="fas fa-star star"></i>
                            <i class="fas fa-star star"></i>
                            <i class="fas fa-star star"></i>
                        </div>
                    </div>
                    
                    <div class="note-content">
                        {escaped_content}
                    </div>
                    
                    <div class="note-footer">
                        <div class="note-timestamp">
                            <i class="far fa-clock"></i>
                            {note['timestamp']}
                        </div>
                        
                        <div class="note-tags">
                            <span class="tag {category_class}">
                                <i class="fas fa-tag"></i> {category}
                            </span>
                        </div>
                    </div>
                </div>
                """

        html += """
        </div>
    </div>
</body>
</html>
"""
        return html

# 实例化便签管理器
_sticky_note_manager = StickyNoteManager()

def register_sticky_notes_tools(mcp):
    """
    注册便签管理工具
    """
    @mcp.tool()
    def add_sticky_note(content: str, importance: str = "普通", category: str = "未分类") -> dict:
        """
        添加新便签
        :param content: 便签内容(必填)
        :param importance: 重要性(普通/重要/紧急)
        :param category: 分类(工作/生活/学习/其他)
        :return: 操作结果和便签信息
        """
        result = _sticky_note_manager.add_note(content, importance, category)
        if result["success"]:
            # 只有在添加成功后才会刷新浏览器
            browser_result = _sticky_note_manager._refresh_browser_page(_sticky_note_manager.html_output_file)
            if not browser_result["success"]:
                result["browser_message"] = browser_result.get("error", "浏览器刷新失败")
        return result

    @mcp.tool()
    def modify_sticky_note(note_id: int, new_content: str = None, 
                         new_importance: str = None, new_category: str = None) -> dict:
        """
        修改现有便签
        :param note_id: 要修改的便签ID(必填)
        :param new_content: 新内容(可选)
        :param new_importance: 新重要性(可选)
        :param new_category: 新分类(可选)
        :return: 操作结果和更新后的便签信息
        """
        result = _sticky_note_manager.modify_note(note_id, new_content, new_importance, new_category)
        if result["success"]:
            # 只有在修改成功后才会刷新浏览器
            browser_result = _sticky_note_manager._refresh_browser_page(_sticky_note_manager.html_output_file)
            if not browser_result["success"]:
                result["browser_message"] = browser_result.get("error", "浏览器刷新失败")
        return result

    @mcp.tool()
    def delete_sticky_note(note_id: int) -> dict:
        """
        删除便签
        :param note_id: 要删除的便签ID
        :return: 操作结果和剩余便签数
        """
        result = _sticky_note_manager.delete_note(note_id)
        if result["success"]:
            # 只有在删除成功后才会刷新浏览器
            browser_result = _sticky_note_manager._refresh_browser_page(_sticky_note_manager.html_output_file)
            if not browser_result["success"]:
                result["browser_message"] = browser_result.get("error", "浏览器刷新失败")
        return result

    @mcp.tool()
    def search_sticky_notes(keyword: str = None, importance: str = None, 
                          category: str = None) -> dict:
        """
        搜索便签
        :param keyword: 关键词搜索(可选)
        :param importance: 按重要性筛选(可选)
        :param category: 按分类筛选(可选)
        :return: 操作结果和匹配的便签列表
        """
        result = _sticky_note_manager.search_notes(keyword, importance, category)
        if result["success"]:
            # 只有在搜索成功后才会刷新浏览器
            browser_result = _sticky_note_manager._refresh_browser_page(_sticky_note_manager.html_output_file)
            if not browser_result["success"]:
                result["browser_message"] = browser_result.get("error", "浏览器刷新失败")
        return result

    @mcp.tool()
    def list_all_sticky_notes() -> dict:
        """
        列出所有便签
        :return: 操作结果和所有便签列表
        """
        result = _sticky_note_manager.list_all_notes()
        if result["success"]:
            # 只有在列出成功后才会刷新浏览器
            browser_result = _sticky_note_manager._refresh_browser_page(_sticky_note_manager.html_output_file)
            if not browser_result["success"]:
                result["browser_message"] = browser_result.get("error", "浏览器刷新失败")
        return result

    @mcp.tool()
    def show_sticky_notes_html() -> dict:
        """
        刷新便签HTML页面
        :return: 操作结果
        """
        html_result = _sticky_note_manager.generate_html_report(
            notes_to_display=_sticky_note_manager.notes)
        if not html_result["success"]:
            return html_result
        return _sticky_note_manager._refresh_browser_page(_sticky_note_manager.html_output_file)

def close_edge_driver():
    """
    关闭Edge浏览器驱动
    """
    global _edge_driver_instance
    if _edge_driver_instance:
        try:
            _edge_driver_instance.quit()
            logger.info("Edge浏览器已关闭")
        except WebDriverException as e:
            logger.error(f"关闭Edge浏览器失败: {e}")
        finally:
            _edge_driver_instance = None