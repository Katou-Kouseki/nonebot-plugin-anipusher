"""
功能开关管理模块
负责根据网络测试结果管理各个功能模块的启用状态。
"""
from ..config import APPCONFIG, FUNCTION
from nonebot import logger


"""
功能开关管理模块
负责根据网络测试结果管理各个功能模块的启用状态。
调用方式：
    parsed_result为ConnectChecker.get_result()返回的字典
    FunctionSwitchManager.set_function_switch(parsed_result)
"""


class FunctionSwitchManager:
    """功能开关管理器类
    负责根据网络测试结果，决定是否启用各种推送功能。
    目前支持管理Emby和TMDB功能的启用状态。
    """
    @staticmethod
    def set_function_switch(parsed_result: dict) -> None:
        """根据网络测试结果，决定是否启用推送功能
        Args:
            parsed_result: 网络测试结果,由ConnectChecker.get_result()返回
        Raises:
            AppError.Exception: 当解析结果为空时抛出
        """
        if not parsed_result:
            logger.opt(colors=True).error(
                "<r>HealthCheck</r>:意外的空解析结果,EMBY与TMDB相关功能被 <r>禁用</r>")
            return
        try:
            # Emby功能开关 (需要ping和info都成功)
            ping_emby_ok = parsed_result.get("ping_emby", {}).get("success", False)
            info_emby_ok = parsed_result.get("info_emby", {}).get("success", False)
            FUNCTION.emby_enabled = ping_emby_ok and info_emby_ok
            logger.opt(colors=True).info(
                f"<g>HealthCheck</g>:Emby功能: {'<g>已启用</g>' if FUNCTION.emby_enabled else '<r>已禁用</r> '}")
        except Exception as e:
            # 全局回退：确保关键功能被禁用
            FUNCTION.emby_enabled = False
            logger.opt(colors=True).error(
                f"<r>HealthCheck</r>:EMBY功能已 <r>禁用</r> 处理异常 —— {e}")
        try:
            # TMDB功能开关 (直连或代理任一成功即可)
            tmdb_direct_ok = parsed_result.get("tmdb", {}).get("success", False)
            tmdb_proxy_ok = parsed_result.get("tmdb_with_proxy", {}).get("success", False)
            FUNCTION.tmdb_enabled = tmdb_direct_ok or tmdb_proxy_ok
            # 如果直连成功，则禁用代理
            if tmdb_direct_ok:
                APPCONFIG.proxy = None
            status = (
                "直连 <g>已启用</g>" if tmdb_direct_ok else
                "代理连接 <g>已启用</g>" if tmdb_proxy_ok else
                "<r>已禁用</r> "
            )
            logger.opt(colors=True).info(
                f"<g>HealthCheck</g>:TMDB功能: {status}")
        except Exception as e:
            FUNCTION.tmdb_enabled = False
            logger.opt(colors=True).error(
                f"<r>HealthCheck</r>:TMDB功能已 <r>禁用</r> 处理异常 —— {e}")
