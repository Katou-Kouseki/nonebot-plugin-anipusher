"""配置管理模块

该模块提供应用程序的全局配置管理功能，包含所有运行时配置对象的统一访问接口。
通过该模块可以访问应用程序的核心配置、功能开关、推送目标和工作目录设置。

导入的配置对象包括：
- APPCONFIG: 应用程序核心配置
- FUNCTION: 功能开关配置
- PUSHTARGET: 推送目标配置
- WORKDIR: 工作目录配置
"""

from .config_manager import APPCONFIG, FUNCTION, PUSHTARGET, WORKDIR

__all__ = ["APPCONFIG", "FUNCTION", "PUSHTARGET", "WORKDIR"]
