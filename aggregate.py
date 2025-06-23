# -*- coding: utf-8 -*-
from mcp.server.fastmcp import FastMCP
import sys
from tools.email_qq import register_email_tools
from tools.system import register_system_tools
from tools.web_tools import register_web_tools as register_new_web_tools  # 新增网页工具
from tools.sleep import register_power_tools as register_power_tools  
from tools.bilibili_search import register_bilibili_tool as  register_bilibili_tool
from tools.music import register_music_tools as  register_music_tools
from tools.vision import register_vision_tools as  register_vision_tools
from tools.note import register_sticky_notes_tools as  register_sticky_notes_tools
if sys.platform == 'win32':
    sys.stderr.reconfigure(encoding='utf-8')
    sys.stdout.reconfigure(encoding='utf-8')
import io
import os




# 创建MCP服务器
mcp = FastMCP("AggregateMCP", encoding='utf-8')

# 注册所有工具
register_email_tools(mcp)
register_system_tools(mcp)
register_new_web_tools(mcp)  # 注册新的网页工具
register_power_tools(mcp)
register_bilibili_tool(mcp)
register_music_tools(mcp)
register_vision_tools(mcp)
register_sticky_notes_tools(mcp)

if __name__ == "__main__":
    mcp.run(transport="stdio")