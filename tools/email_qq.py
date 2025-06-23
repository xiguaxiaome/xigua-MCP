# -*- coding: utf-8 -*-
import logging
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger('email_tools')

EMAIL_SENDER = os.environ.get("EMAIL_SENDER")
EMAIL_AUTHCODE = os.environ.get("EMAIL_AUTHCODE")

def register_email_tools(mcp: FastMCP):
    @mcp.tool()
    def send_email(recipient_email: str, subject: str, body: str) -> dict:
        """
        发送邮件工具。
        参数：
        - recipient_email: 收件人邮箱
        - subject: 邮件主题
        - body: 邮件正文
        返回：
        - 成功或失败的状态
        """
        logger.info(f"准备发送邮件到 {recipient_email}，主题：{subject}")

        try:
            # 创建邮件对象
            msg = MIMEMultipart()
            msg['From'] = EMAIL_SENDER
            msg['To'] = recipient_email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))

            # 连接 QQ 邮箱的 SMTP 服务器并发送邮件
            with smtplib.SMTP_SSL('smtp.qq.com', 465) as server:
                server.login(EMAIL_SENDER, EMAIL_AUTHCODE)
                server.send_message(msg)
                server.quit()

            logger.info(f"邮件成功发送到 {recipient_email}")
            return {"success": True, "result": "邮件发送成功"}
        except Exception as e:
            logger.error(f"发送邮件失败: {e}")
            return {"success": False, "result": str(e)}

