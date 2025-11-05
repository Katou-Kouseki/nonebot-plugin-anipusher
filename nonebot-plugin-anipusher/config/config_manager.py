"""运行时配置管理模块

提供全局单例配置对象，用于在整个应用程序中共享配置状态。
该模块实现了配置的集中管理，确保在整个应用生命周期中配置的一致性。

包含的应用程序配置对象：
- APPCONFIG: 核心配置参数（API密钥、服务器地址等）
- FUNCTION: 功能开关状态（控制各模块启用/禁用）
- PUSHTARGET: 消息推送目标（群组和私聊推送配置）
- WORKDIR: 工作目录设置（缓存、数据库和配置文件路径）
"""

from ..model import AniPusherConfig, FeatureFlags, PushTarget, WorkDir

# 应用程序主配置对象
# 存储代理设置、API密钥等核心配置参数
APPCONFIG = AniPusherConfig()

# 功能开关配置对象
# 控制各个功能模块的启用/禁用状态
FUNCTION = FeatureFlags()

# 推送目标配置对象
# 管理群组和私聊推送的目标配置
PUSHTARGET = PushTarget()

# 工作目录配置对象
# 定义缓存、数据库和配置文件存储路径
WORKDIR = WorkDir()
