# -*- coding: utf-8 -*-
"""
日期时间工具模块
提供与日期和时间相关的工具函数，主要用于生成和处理时间戳
"""
from datetime import datetime


def get_iso8601_timestamp() -> str:
    """获取 ISO 8601 格式的当前时间戳（精确到毫秒）
    Returns:
        str: ISO 8601 格式的时间戳字符串，格式为 YYYY-MM-DDTHH:MM:SS.sss
    """
    return datetime.now().isoformat(timespec='milliseconds')
