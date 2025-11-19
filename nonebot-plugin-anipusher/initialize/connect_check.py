"""
连接检查模块
提供异步网络连接测试功能，支持并发测试多个服务连接状态。
"""
from ..config import APPCONFIG
from ..external import get_request
from ..exceptions import AppError
from nonebot import logger
import asyncio
"""
# 使用示例1: 异步执行模式
# 创建检查器实例
checker = ConnectChecker()
# 启动检查但不等待结果
await checker.start_check()
# 执行其他任务
await do_something_else()
# 等待并获取检查结果
results = await checker.get_result()
print(results)

# 使用示例2: 直接获取结果（内部会自动启动检查）
checker = ConnectChecker()
results = await checker.get_result()  # 这会阻塞直到所有任务完成
print(results)
# 结果格式示例
# {
#     'ping_emby': {'success': True, 'error': None},
#     'info_emby': {'success': True, 'error': None},
#     'tmdb': {'success': False, 'error': '连接超时'},
#     'tmdb_with_proxy': {'success': True, 'error': None}
# }
"""


class ConnectChecker:
    """连接检查器类

    负责创建和管理网络连接测试任务，支持异步执行和结果收集。
    提供了创建任务、获取结果和解析结果的功能。
    """

    def __init__(self):
        """初始化连接检查器
        初始化任务存储字典，用于保存创建的网络测试任务。
        """
        self.connect_task = None  # 存储创建的网络测试任务

    # 创建网络测试任务
    def _create_network_task(self) -> dict:
        """创建网络测试任务
        创建一系列异步HTTP请求任务，用于测试与Emby和TMDB等外部服务的连接。
        这些任务将被异步执行，但不会立即等待其完成。
        Returns:
            dict: 包含所有创建的任务的字典，键为任务名称，值为任务对象
        """
        emby_base = (APPCONFIG.emby_host or "").rstrip("/")
        emby_key = APPCONFIG.emby_key or ""

        ping_emby_url = f"{emby_base}/emby/System/Ping?api_key={emby_key}"
        info_emby_url = f"{emby_base}/emby/System/Info?api_key={emby_key}"

        tmdb_headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {(APPCONFIG.tmdb_authorization or '')}"
        }
        tmdb_api = "https://api.themoviedb.org/3/authentication"
        tasks = {
            "ping_emby": asyncio.create_task(get_request(ping_emby_url)),
            "info_emby": asyncio.create_task(get_request(info_emby_url)),
            "tmdb": asyncio.create_task(get_request(tmdb_api,
                                                    headers=tmdb_headers)),
            "tmdb_with_proxy": asyncio.create_task(get_request(tmdb_api,
                                                               headers=tmdb_headers,
                                                               proxy=APPCONFIG.proxy))
        }
        return tasks

    # 获取网络测试任务结果
    async def _get_tasks_result(self) -> dict:
        """获取网络测试任务结果
        等待所有创建的网络测试任务完成，并收集它们的执行结果。
        支持异常处理，确保即使部分任务失败也能获取所有结果。
        Returns:
            dict: 包含所有任务执行结果的字典，键为任务名称，值为任务结果或异常
        Raises:
            AppError.MissingParameter: 当连接检查任务不存在时抛出
            AppError.NetworkConnectionFailed: 当任务执行过程中发生异常时抛出
        """
        # 检查连接检查任务是否存在
        if not self.connect_task:
            AppError.MissingParameter.raise_("连接检查任务未创建")
        try:
            # 使用asyncio.gather获取所有任务的执行结果
            results = await asyncio.gather(
                *self.connect_task.values(),
                return_exceptions=True
            )  # 获取所有任务的执行结果
            # 返回 {task_name: result} 字典
            return {
                name: res for name, res in zip(self.connect_task.keys(), results)
            }
        except asyncio.CancelledError:
            # 如果任务被取消，抛出异常
            AppError.NetworkConnectionFailed.raise_("连接检查任务已取消")
        except Exception as e:
            # 如果发生其他异常，抛出异常

            AppError.NetworkConnectionFailed.raise_(f"连接检查任务异常 —— {e}")

    # 解析任务结果
    def _parse_task_result(self, task_result: dict) -> dict:
        """解析任务结果

        分析任务执行结果，判断每个任务是否成功，并提取错误信息（如果有）。
        对于失败的任务，会记录警告日志，包含任务名称和错误类型。

        Args:
            task_result: 任务执行结果字典，由_get_tasks_result方法返回
        Returns:
            dict: 解析后的任务结果，包含每个任务的成功状态和错误信息（如果有）
        """
        parsed = {}
        for task_name, res in task_result.items():
            success = not isinstance(res, Exception)
            parsed[task_name] = {
                "success": success,
                "error": str(res) if not success else None
            }
            if not success:
                logger.opt(colors=True).debug(
                    f"<y>HealthCheck</y>:{task_name}连接失败 —— {type(res).__name__}")
        return parsed

    async def start_check(self) -> dict:
        """
        启动连接检查
        创建并启动网络测试任务，但不等待其完成，允许调用者继续执行其他任务。
        这是异步执行模式的入口点，适用于需要并发执行其他任务的场景。
        Returns:
            dict: 包含所有创建的任务的字典，键为任务名称，值为任务对象
        """
        self.connect_task = self._create_network_task()
        return self.connect_task

    async def get_result(self) -> dict:
        """
        等待并获取连接检查结果
        等待所有网络测试任务完成，获取并解析其执行结果。
        如果尚未启动检查，将自动先启动检查。
        Returns:
            dict: 解析后的任务结果，包含每个任务的成功状态和错误信息（如果有）
        """
        if not self.connect_task:
            # 自动启动检查
            await self.start_check()
        # 获取任务结果
        task_result = await self._get_tasks_result()
        # 解析任务结果
        return self._parse_task_result(task_result)
