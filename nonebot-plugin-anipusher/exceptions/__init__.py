"""应用程序异常处理模块

该模块提供了统一的异常处理机制，包含所有应用程序可能抛出的错误类型。

模块组成：
- AppError: 应用程序错误枚举类，定义了系统中所有可能的错误代码和消息
- AppError.Exception: 自定义异常类，用于抛出带有错误代码的异常

使用方法：
1. 导入异常类:
   from new_anipusher.exceptions import AppError

2. 抛出异常:
   # 使用预定义错误信息
   AppError.UnknownError.raise_()

   # 添加自定义错误信息
   AppError.FileIOError.raise_("配置文件不存在")

3. 捕获异常:
   try:
       AppError.UnknownError.raise_("操作失败")
   except AppError.Exception as e:
       print(f"错误码: {e.error_code.code}")
       print(f"错误信息: {e.error_code.msg}")
       print(f"额外信息: {e.extra_msg}")

4. 获取错误信息:
   error = AppError.get_by_code(1000)
   print(f"错误代码: {error.code}, 错误消息: {error.msg}")
"""

from .plugin_errors import AppError

__all__ = ["AppError"]
