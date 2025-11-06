"""监控器模块
该模块负责设置HTTP服务器，接收外部系统发送的webhook数据，并将其转发给数据处理模块进行处理。
作为系统的入口点之一，它监听指定路径的POST请求，并异步启动数据处理流程。
"""
from nonebot import get_driver
from nonebot.drivers import URL, Request, Response, ASGIMixin, HTTPServerSetup
from nonebot import logger
import asyncio
from .dataprocess.processing_manager import DataProcessor


class Monitor:
    """监控器类
    负责配置和启动HTTP服务器，处理传入的webhook请求，并将数据转发给数据处理模块。
    使用NoneBot的驱动系统来设置HTTP端点，实现异步请求处理。
    """

    def __init__(self):
        """初始化监控器
        获取NoneBot驱动实例，并从配置中提取主机和端口信息。
        """
        self.driver = get_driver()  # 获取NoneBot驱动实例
        self.host = self.driver.config.host  # 从驱动配置中获取主机地址
        self.port = self.driver.config.port  # 从驱动配置中获取端口号
        # 初始化&主入口

    @classmethod
    async def create_and_run(cls) -> 'Monitor':
        """创建并运行监控器的工厂方法
        这是监控器的主入口点，创建监控器实例并启动监控流程。
        Returns:
            Monitor: 创建并启动的监控器实例
        """
        monitor = cls()
        await monitor._monitor()
        return monitor

    async def _monitor(self):
        """监控器的配置方法
        设置HTTP服务器和webhook处理函数，用于接收和处理来自外部系统的webhook请求。
        该方法配置了监听路径、请求方法和请求处理逻辑。
        """
        async def handle_webhook(request: Request) -> Response:
            """处理webhook请求的内部函数
            解析请求体中的JSON数据，记录日志，并异步启动数据处理流程。
            立即返回200状态码，不阻塞webhook发送方。
            Args:
                request: HTTP请求对象
            Returns:
                Response: HTTP响应对象，状态码为200表示成功接收
            """
            # 解析请求体中的JSON数据
            received_data = request.json
            logger.opt(colors=True).info("<g>Monitor</g>: 接收到 WEBHOOK 数据")
            logger.opt(colors=True).debug(f"Webhook数据详情：{received_data}")
            # 构造并返回响应，立即确认接收
            response = Response(200,
                                headers={"Content-Type": "application/json"},
                                content="ok")
            # 异步启动数据处理流程，不阻塞响应返回
            asyncio.create_task(
                DataProcessor.create_and_execute(received_data))
            return response

        # 检查驱动是否支持ASGI协议（HTTP服务器功能）
        if isinstance(self.driver, ASGIMixin):
            # 设置HTTP服务器路由
            self.driver.setup_http_server(
                HTTPServerSetup(
                    path=URL("/webhook"),  # webhook路径
                    method="POST",  # 只接受POST请求
                    name="monitor_webhook",  # 路由名称
                    handle_func=handle_webhook,  # 请求处理函数
                )
            )
            # 记录监控服务启动信息
            logger.opt(colors=True).success(
                f"🔍 监控服务已启动，监听地址: <cyan>{self.host}:{self.port}/webhook</cyan>")
        else:
            logger.opt(colors=True).warning(
                "⚠️ 警告：当前驱动不支持HTTP服务器功能，插件无法接收Webhook数据。")
