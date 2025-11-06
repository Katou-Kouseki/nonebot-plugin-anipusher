# -*- coding: utf-8 -*-
"""数据处理抽象基类模块
定义数据处理的通用接口和框架，为所有具体数据处理器提供基础结构。
实现了处理器注册机制、选择逻辑和通用处理流程。
"""

# 标准库
from abc import ABC, abstractmethod
# 第三方库
from nonebot import logger
# 项目内部模块
from ...exceptions import AppError
from ...mapping import TableName
from ...database import DatabaseOperator
from .processor.anime_processor import AnimeProcessor


class AbstractDataProcessor(ABC):
    """数据处理抽象基类
    定义数据处理的通用接口，强制要求实现数据处理方法。
    提供处理器注册机制、处理器选择和标准处理流程。
    Attributes:
        _registry: 存储已注册处理器的字典
    """
    _registry = {}

    def __init__(self, data, source: TableName):
        """初始化数据处理器
        Args:
            data: 原始数据，通常来自webhook
            source: 数据来源，来自TableName枚举
        """
        self.raw_data = data
        self.source: TableName = source
        self.structured_data = None
        self.tmdb_id = None

    @classmethod
    def register(cls, source_type):
        """装饰器：将子类注册到指定类型
        Args:
            source_type: 数据源类型，通常是TableName枚举值
        Returns:
            function: 装饰器函数
        """
        def wrapper(subclass):
            cls._registry[source_type] = subclass
            return subclass
        return wrapper

    @classmethod
    async def select_processor(cls, data, source):
        """根据数据源选择对应的处理器
        Args:
            data: 原始数据
            source: 数据来源
        Returns:
            AbstractDataProcessor or None: 匹配的处理器实例，如果未找到则返回None
        """
        subclass = cls._registry.get(source)
        if subclass:
            return subclass(data, source)
        return None

    async def execute(self):
        """执行完整的数据处理流程
        按照以下步骤执行处理：
        1. 重新格式化数据
        2. 存储接收到的数据
        3. 执行Anime数据处理（如果启用）
        4. 推送处理后的数据
        每个步骤都有独立的异常处理，确保单步失败不会导致整个系统崩溃。
        """
        try:
            await self._reformat()
            logger.opt(colors=True).info(
                f"<g>{self.source.value}</g>:TMDB ID: <c>{self.tmdb_id}</c> 记录格式化 |<g>SUCCESS</g>")
        except Exception as e:
            logger.opt(colors=True).error(
                f"<r>{self.source.value}</r>:{e}")
            logger.opt(colors=True).error(
                f"<r>{self.source.value}</r>:WEBHOOK记录格式化 |<r>FAIL</r> 后续操作将 <r>取消</r>")
            return
        try:
            await self._store_received_data()
            logger.opt(colors=True).info(
                f"<g>{self.source.value}</g>:TMDB ID: <c>{self.tmdb_id}</c> 记录持久化 |<g>SUCCESS</g>")
        except Exception as e:
            logger.opt(colors=True).error(
                f"<r>{self.source.value}</r>:{e}")
            logger.opt(colors=True).error(
                f"<r>{self.source.value}</r>:WEBHOOK记录持久化 |<r>FAIL</r> 后续操作将 <r>取消</r>")
            return
        # 进行Anime数据处理
        try:
            await self._anime_process()
        except Exception:
            return
        logger.opt(colors=True).info(
            f"<g>{self.source.value}</g>:TMDB ID: <c>{self.tmdb_id}</c> 数据处理 |<g>SUCCESS</g>")
        try:
            logger.opt(colors=True).info("————————————— 推送服务进行中 —————————————")
            await self._push()
            logger.opt(colors=True).info(
                f"<g>{self.source.value}</g>:TMDB ID: <c>{self.tmdb_id}</c> 数据推送 |<g>SUCCESS</g>")
        except Exception as e:
            logger.opt(colors=True).error(
                f"<r>{self.source.value}</r>:{e}")
            logger.opt(colors=True).error(
                f"<r>{self.source.value}</r>:TMDB ID: <c>{self.tmdb_id}</c> 数据推送 |<r>FAIL</r>")
            return

    @abstractmethod
    async def _reformat(self) -> bool:
        """重新格式化原始数据
        子类必须实现此方法，负责将原始数据转换为结构化格式。
        Returns:
            bool: 格式化是否成功
        """

    def _enable_anime_process(self):
        """检查是否启用Anime数据处理
        子类可以重写此方法以启用Anime数据处理功能。
        Returns:
            bool: 默认返回False，表示不启用
        """
        return False

    async def _store_received_data(self):
        """存储接收记录到数据库
        将结构化数据存储到对应的数据表中。
        Raises:
            AppError.InvalidParameter: 当结构化数据为空时
            AppError.UnknownError: 当存储过程发生未知错误时
        """
        if not self.structured_data:
            AppError.InvalidParameter.raise_(
                "准备存储数据时发现结构化数据为空")
        try:
            db_operator = DatabaseOperator()
            await db_operator.upsert_data(
                table_name=self.source,
                data=self.structured_data
            )
        except AppError.Exception:
            raise
        except Exception as e:
            AppError.UnknownError.raise_(f"未知的接收记录存储失败 —— {e}")

    async def _anime_process(self):
        """执行Anime数据处理
        只有当_enable_anime_process()返回True时才会执行。
        创建并执行AnimeProcessor实例进行额外的数据处理。
        Raises:
            AppError.UnknownError: 当处理过程发生错误时
        """
        if not self._enable_anime_process():
            return
        try:
            anime_processor = AnimeProcessor(self.source, self.structured_data)
            await anime_processor.process()
            logger.opt(colors=True).info(
                f"<g>{self.source.value}</g>:Anime数据处理   |<g>COMPLETE</g>")
        except Exception as e:
            logger.opt(colors=True).error(
                f"<r>{self.source.value}</r>:{e}")
            logger.opt(colors=True).error(
                f"<r>{self.source.value}</r>:生成Anime数据处理器实例 <r>FAIL</r>")
            AppError.UnknownError.raise_(f"{e}")

    async def _push(self):
        """推送处理后的数据
        调用PushManager进行数据推送操作。
        """
        from ..pushprocess.push_manager import PushManager
        await PushManager.create_and_execute(self.source)
