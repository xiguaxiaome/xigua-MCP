# MCP Aggregate | MCP 集合项目

A powerful interface for extending AI capabilities through remote control, note, email operations, knowledge search, and more.

一个强大的接口，用于通过远程控制、笔记、邮件操作、知识搜索等方式扩展AI能力。

## Overview | 概述

MCP (Model Context Protocol) is a protocol that allows servers to expose tools that can be invoked by language models. Tools enable models to interact with external systems, such as querying databases, calling APIs, or performing computations. Each tool is uniquely identified by a name and includes metadata describing its schema.

MCP（模型上下文协议）是一个允许服务器向语言模型暴露可调用工具的协议。这些工具使模型能够与外部系统交互，例如查询数据库、调用API或执行计算。每个工具都由一个唯一的名称标识，并包含描述其模式的元数据。

## Quick Start | 快速开始

1. Install dependencies | 安装依赖:

```bash
python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt
```

2. Set up environment variables | 设置环境变量:

```bash
修改这个文件： .env.xiaozhi1
```

3. Run the example | 运行示例:

```bash
# You can run different XiaoZhi MCP access points through different configuration files
# 可以通过不同的配置文件，来运行到不同的多个小智MCP接入点
python mcp_pipe.py aggregate.py --env-file .env.xiaozhi1
```

## Creating Your Own MCP Tools | 创建自己的MCP工具

Here's a simple example of creating an MCP tool | 以下是一个创建MCP工具的简单示例:

- According to the example in the tools folder, create your own tool | 根据 tools 文件夹中的示例创建自己的工具
- The tool name is distinguished by function_channel, for example, email_google indicates that it is a Google Mail MCP tool | 工具命名以 功能_渠道区分，例如 email_google 表明是谷歌邮箱的MCP工具
- Register your tool in aggregate.py | 在 aggregate.py 中注册你的工具
- Configure the environment variables for your tool in the .env.xxx file (if any) | 在 .env.xxx 文件中配置你的工具的环境变量(如果有的话)
- If you want to contribute code, you also need to add the environment variables for your tool (if any) in the .env.example file | 如果要贡献代码的话还需要在 .env.example 文件中添加你的工具的环境变量（如果有的话）

## Requirements | 环境要求

- Python 3.10+
- websockets>=11.0.3
- python-dotenv>=1.0.0
- mcp>=1.8.1
- pydantic>=2.11.4
- 。。。

## FAQ | 常见问题

- MCP_PIPE - ERROR - Connection error: python-socks is required to use a SOCKS proxy

```text
关闭电脑的系统代理
Close the system proxy on your computer
```

## Acknowledgments | 致谢

- https://github.com/78/mcp-calculator | 完全根据78前辈的计算器mcp，做的外扩
- Thanks to all contributors who have helped shape this project | 感谢所有帮助塑造这个项目的贡献者
- Inspired by the need for extensible AI capabilities | 灵感来源于对可扩展AI能力的需求
