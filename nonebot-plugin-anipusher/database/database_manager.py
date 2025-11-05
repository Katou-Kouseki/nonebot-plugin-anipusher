"""数据库连接池管理模块

该模块提供了一个异步SQLite数据库连接池管理器，实现了连接的创建、获取、复用和关闭的完整功能。
采用单例模式设计，确保应用程序中只有一个连接池实例，提高资源利用率和管理效率。

主要功能：
- 异步连接池管理，支持最大20个并发连接
- 自动连接初始化与资源回收
- 连接超时和异常处理机制
- 线程安全的连接池操作
"""
import aiosqlite
import asyncio
from typing import Optional
from contextlib import asynccontextmanager
from ..config import WORKDIR
from ..exceptions import AppError


class DatabaseManager:
    """异步数据库连接池管理器
    采用单例模式设计，负责SQLite数据库连接的创建、管理和释放，
    提供线程安全的连接池操作和异常处理机制。
    属性:
        _instance: 类的单例实例
        _init_lock: 初始化锁，确保线程安全
        _max_connections: 最大连接数
        _pool: 连接池，存储数据库连接对象
        _current_connections: 当前活跃连接数
    """
    _instance = None
    _init_lock = asyncio.Lock()
    _max_connections = 20
    _pool: Optional[asyncio.Queue[aiosqlite.Connection]] = None
    _current_connections = 0

    def __new__(cls):
        """单例模式实现，确保全局只有一个DatabaseManager实例
        Returns:
            DatabaseManager: 类的唯一实例
        """
        # 如果实例不存在，则创建一个实例
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        # 返回实例
        return cls._instance

    @classmethod
    async def initialize(cls) -> None:
        """初始化数据库连接池
        创建指定数量的数据库连接并放入连接池，使用双重检查锁定模式确保线程安全。
        连接池初始化后，可以通过get_connection()方法获取连接。
        Raises:
            AppError.DatabaseConnectionFailed: 连接创建失败时抛出
            AppError.ResourceNotFound: 数据库文件路径异常时抛出
        """
        if cls._pool is None:
            async with cls._init_lock:
                if cls._pool is None:
                    cls._pool = asyncio.Queue(maxsize=cls._max_connections)
                    for _ in range(cls._max_connections):
                        conn = await cls._create_connection()
                        await cls._pool.put(conn)  # 将连接放入连接池

    @classmethod
    @asynccontextmanager
    async def get_connection(cls):
        """获取数据库连接的异步上下文管理器
        自动初始化连接池（如果尚未初始化），从连接池中获取可用连接，
        使用完成后自动归还连接到池中，确保资源正确释放。
        Yields:
            aiosqlite.Connection: 数据库连接对象
        Raises:
            AppError.DatabaseConnectionFailed: 连接池未初始化或创建连接失败时抛出
            AppError.DatabaseTimeout: 获取连接超时（5秒）时抛出
        Example:
            ```python
            async with DatabaseManager().get_connection() as conn:
                async with conn.execute("SELECT * FROM table") as cursor:
                    # 处理查询结果
            ```
        """
        if cls._pool is None:  # 如果连接池为空，则初始化连接池
            await cls.initialize()
        try:
            if cls._pool is None:
                AppError.DatabaseConnectionFailed.raise_("数据库连接池未初始化")
            # 从连接池中获取连接，等待时间为5秒
            conn = await asyncio.wait_for(cls._pool.get(), timeout=5)
            cls._current_connections += 1
            try:
                yield conn
            finally:
                try:
                    # 尝试将连接归还到池中
                    await cls._pool.put(conn)
                except Exception:
                    # 如果归还失败，关闭连接
                    await conn.close()
                finally:
                    # 确保连接计数正确更新
                    cls._current_connections -= 1
        except asyncio.TimeoutError:
            # 如果获取连接超时，抛出数据库繁忙异常
            AppError.DatabaseTimeout.raise_("获取数据库连接超时，数据库可能繁忙")

    @classmethod
    async def close_pool(cls):
        """关闭连接池并释放所有连接资源
        适用于应用程序关闭或不再需要数据库连接时调用，确保所有连接被正确关闭，
        避免资源泄漏。使用锁确保线程安全，防止并发关闭操作导致的问题。
        """
        if cls._pool is not None:  # 如果连接池不为空，则关闭所有连接
            # 使用异步上下文管理器，保证在出现异常时，连接仍然能够关闭
            async with cls._init_lock:
                # 从连接池中取出所有连接并关闭
                while not cls._pool.empty():
                    conn = await cls._pool.get()
                    await conn.close()
                # 重置连接池状态
                cls._pool = None
                cls._current_connections = 0

    @staticmethod
    async def _create_connection() -> aiosqlite.Connection:
        """创建新的数据库连接
        配置并创建一个新的SQLite连接，设置优化参数以提高性能和稳定性。
        连接使用WAL模式以提高并发性能，并配置自动提交事务。
        Returns:
            aiosqlite.Connection: 配置好的数据库连接对象
        Raises:
            AppError.ResourceNotFound: 数据库文件路径异常时抛出
            AppError.DatabaseConnectionFailed: 连接创建失败时抛出
            AppError.UnknownError: 发生未知错误时抛出
        """
        try:
            if not WORKDIR.data_file:
                AppError.ResourceNotFound.raise_("数据库文件路径未获取！")
            conn = await aiosqlite.connect(
                database=WORKDIR.data_file,
                isolation_level=None,  # 自动提交事务
                check_same_thread=False  # 允许在不同线程之间共享数据库连接
            )
            # 设置WAL模式以提高并发性能
            await conn.execute("PRAGMA journal_mode=WAL")
            # 设置5000毫秒的繁忙超时时间
            await conn.execute("PRAGMA busy_timeout = 5000")
            return conn
        except aiosqlite.Error as e:
            AppError.DatabaseConnectionFailed.raise_(f"数据库连接创建失败: {e}")
        except Exception as e:
            AppError.DatabaseTransactionError.raise_(f"{e}")
