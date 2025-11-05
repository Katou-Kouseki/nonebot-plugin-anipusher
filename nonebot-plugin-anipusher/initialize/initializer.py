"""初始化协调器模块
此模块是Anipusher应用的核心初始化引擎，负责协调各个子系统的初始化流程，确保所有组件按照正确的依赖顺序启动。
它管理整个应用的启动过程，包括配置加载、资源准备、网络连接验证、数据库初始化以及功能模块的动态导入。
通过精心设计的初始化流程，确保应用能够在各种环境下稳定启动，同时提供清晰的启动状态反馈和错误处理机制。
"""
from nonebot import logger
from .config_load import ConfigLoader  # 配置加载器
from .resouse_release import ResourceCopier  # 资源复制工具
from .connect_check import ConnectChecker  # 网络连接检查器
from .function_switch import FunctionSwitchManager  # 功能开关管理器
from .db_check import DBHealthCheck  # 数据库健康检查器
from .processor_import import ProcessorImport  # 处理器动态导入器


class Initializer:
    """应用初始化协调器
    作为应用启动的中央协调器，负责编排和执行所有初始化任务。
    采用依赖注入和异步编程模式，确保初始化任务按照正确的顺序执行，
    并对整个过程进行监控和异常处理，为应用提供可靠的启动机制。
    Attributes:
        connect_task: 存储网络连接检查任务的引用，用于异步状态管理
        _initialized: 标记初始化是否成功完成的状态标志
    """

    def __init__(self) -> None:
        """初始化协调器实例
        初始化内部状态变量，为后续的初始化流程做准备。
        这里会创建存储网络连接检查任务的引用和初始化状态标志。
        """
        self.connect_task = None  # 存储网络连接检查任务的引用
        self._initialized = False  # 初始化状态标志，标记应用是否初始化成功

    @classmethod
    async def create_and_run(cls) -> 'Initializer':
        """工厂方法：创建并运行初始化协调器
        这是初始化流程的入口点，使用工厂模式创建初始化器实例并执行初始化过程。
        整个过程是异步的，不会阻塞主线程的执行。
        Returns:
            Initializer: 初始化完成的协调器实例，可以通过is_ready属性检查初始化状态
        """
        instance = cls()
        instance._initialized = await instance.initialize()
        return instance

    async def initialize(self):
        """执行完整的初始化流程
        按照预定义的依赖顺序执行所有初始化步骤，每一步都有日志记录和异常处理：
        1. 加载并解析应用配置
        2. 复制必要的静态资源文件
        3. 异步启动网络连接检查
        4. 执行数据库健康检查和结构初始化
        5. 动态导入所有已注册的数据处理器
        6. 获取网络检查结果并据此设置功能开关
        如果任何初始化步骤失败，将记录详细错误信息并立即终止初始化过程，
        返回False表示初始化失败。
        Returns:
            bool: 初始化是否成功完成，成功返回True，失败返回False
        """
        try:
            # 初始化开始日志，使用彩色输出增强可读性
            logger.opt(colors=True).info(
                "<g>HealthCheck</g>:Anipusher自检         |<g>Start</g>")
            # 1. 加载应用配置 - 优先级最高，其他组件依赖配置
            ConfigLoader.create_and_load()
            logger.opt(colors=True).info(
                "<g>HealthCheck</g>:Anipusher配置加载     |<g>SUCCESS</g>")
            # 2. 复制必要的资源文件 - 确保应用运行所需的静态资源可用
            ResourceCopier.copy_resources()
            logger.opt(colors=True).info(
                "<g>HealthCheck</g>:Anipusher资源复制     |<g>SUCCESS</g>")
            # 3. 创建并启动网络连接检查 - 异步执行，不阻塞后续初始化
            checker = ConnectChecker()
            await checker.start_check()  # 启动异步网络检查任务
            logger.opt(colors=True).info(
                "<g>HealthCheck</g>:Anipusher网络任务创建 |<g>SUCCESS</g>")
            # 4. 执行数据库健康检查 - 验证数据库连接并创建必要的表结构
            await DBHealthCheck.create_and_check()
            logger.opt(colors=True).info(
                "<g>HealthCheck</g>:Anipusher数据库检查   |<g>SUCCESS</g>")
            # 5. 动态导入所有数据处理器 - 确保所有处理逻辑可用
            await ProcessorImport.import_processors()
            logger.opt(colors=True).info(
                "<g>HealthCheck</g>:Anipusher处理器导入   |<g>SUCCESS</g>")
            # 6. 获取网络检查结果并设置功能开关 - 根据网络状态启用或禁用特定功能
            results = await checker.get_result()  # 等待网络检查完成
            FunctionSwitchManager.set_function_switch(results)  # 根据检查结果设置功能开关
        except Exception as e:
            # 捕获并记录初始化过程中的所有异常
            logger.opt(colors=True).error(
                f"<r>HealthCheck</r>:插件初始化 <r>失败</r> —— {e}")
            logger.opt(colors=True).error(
                "<r>HealthCheck</r>:Anipusher自检 <r>ERROR</r> 插件载入已跳过")
            return False
        # 初始化成功完成
        logger.opt(colors=True).info(
            "<g>HealthCheck</g>:Anipusher自检         |<g>ALL SUCCESS</g>")
        return True

    @property
    def is_ready(self) -> bool:
        """获取初始化状态
        提供一个只读属性来检查应用是否已经成功初始化。
        其他组件可以通过这个属性来确定是否可以安全地使用应用功能。
        Returns:
            bool: True表示初始化成功完成，False表示初始化未完成或失败
        """
        return self._initialized
