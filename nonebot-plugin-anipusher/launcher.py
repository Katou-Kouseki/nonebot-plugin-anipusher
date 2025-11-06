"""应用启动入口模块
作为Anipusher应用的核心启动点，此模块负责在NoneBot框架启动时初始化整个应用。
它按照正确的顺序启动应用组件，首先初始化系统配置和资源，然后启动监控服务。
通过NoneBot的驱动事件机制，确保所有组件在适当的时机被加载和启动。
"""
from nonebot import get_driver  # 导入NoneBot的驱动获取函数

# 获取NoneBot的驱动实例，用于注册启动事件
driver = get_driver()


@driver.on_startup
async def launch():
    """应用启动函数
    当NoneBot框架启动时，此异步函数会被自动调用。
    按照以下顺序启动应用组件：
    1. 导入并初始化系统初始化器(Initializer)
    2. 检查初始化状态，只有初始化成功才继续启动
    3. 导入并启动监控服务(Monitor)
    这种设计确保了系统依赖的正确加载顺序，并且在初始化失败时能够安全地退出启动流程。
    """
    # 导入初始化器并执行系统初始化
    from .initialize import initializer
    initialize_ = await initializer.Initializer.create_and_run()
    # 检查初始化状态，如果初始化失败则不再继续启动后续服务
    if not initialize_.is_ready:
        return
    # 初始化成功后，导入并启动监控服务
    from .core.monitor import Monitor
    await Monitor.create_and_run()
