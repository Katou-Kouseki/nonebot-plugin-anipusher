from sqlite3 import Row
from ..mapping import TableName
from .statement_generator import StatementGenerator
from .database_manager import DatabaseManager
from ..exceptions import AppError
import asyncio
import json
from typing import Iterable, Literal


class DatabaseOperator:
    """数据库操作类
    负责执行数据库语句和事务管理
    采用单例模式设计，确保全局只有一个实例，优化资源使用并提供统一的数据库操作接口。
    使用示例：
    ```python
    # 获取DatabaseOperator实例
    db_op = DatabaseOperator()
    # 多次调用返回同一个实例
    db_op2 = DatabaseOperator()  # db_op和db_op2是同一个实例
    # 获取表元数据示例
    async def example_get_metadata():
        metadata = await db_op.get_table_metadata(TableName.EMBY)
        print(f"表结构信息: {metadata}")
    # 创建表示例
    async def example_create_table():
        await db_op.create_table(TableName.ANIME)
        print("表创建成功")
    # 删除表示例
    async def example_drop_table():
        await db_op.drop_table(TableName.ANIRSS)
        print("表删除成功")
    # 插入或更新数据示例
    async def example_upsert():
        data = {"name": "测试动漫", "tmdb_id": 12345, "rating": 8.5}
        await db_op.upsert_data(TableName.ANIME, data, "tmdb_id")
        print("数据插入/更新成功")
    # 查询数据示例
    async def example_select():
        # 查询所有列
        results = await db_op.select_data(TableName.EMBY)
        print(f"查询所有结果: {results}")
        # 查询指定列并带条件
        filtered_results = await db_op.select_data(
            TableName.EMBY,
            columns=["id", "name"],
            where={"rating": 9.0},
            order_by="id DESC",
            limit=10
        )
        print(f"过滤后结果: {filtered_results}")
    # 执行自定义SQL
    async def example_execute_sql():
        sql = "SELECT COUNT(*) FROM emby WHERE rating > :rating"
        params = {"rating": 8.0}
        cursor = await db_op.execute_sql(sql, params)
        count = await cursor.fetchone()
        print(f"评分大于8.0的条目数: {count[0]}")
    ```
    """
    _instance = None
    _init_lock = asyncio.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # 防止重复初始化
        if not hasattr(self, 'db_manager'):
            self.db_manager = DatabaseManager()
            self.statement_generator = StatementGenerator()

    async def execute_sql(self, sql: str, params: dict | None = None) -> Iterable[Row] | int | None:
        """执行SQL语句
        Args:
            sql: SQL语句字符串
            params: 可选的参数字典，用于替换SQL语句中的占位符
        Returns:
            执行结果，根据不同的SQL语句类型可能是None、整数（影响行数）或结果集
        """
        if params is None:
            prepared_params = None
        else:
            prepared_params = {}
            # 参数预处理，将所有参数值转换为字符串
            for key, value in params.items():
                # 将字典或列表序列化为JSON字符串
                if isinstance(value, (dict, list)):
                    prepared_params[key] = json.dumps(
                        value, ensure_ascii=False)
                elif isinstance(value, bool):
                    # 将布尔值转换为整数（0/1）
                    prepared_params[key] = 1 if value else 0
                else:
                    prepared_params[key] = value
        try:
            async with self.db_manager.get_connection() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(sql, prepared_params)
                    if sql.strip().upper().startswith(('SELECT', 'PRAGMA', 'EXPLAIN', 'WITH')):
                        return await cursor.fetchall()
                    elif sql.strip().upper().startswith(('INSERT', 'UPDATE', 'DELETE', 'REPLACE')):
                        await conn.commit()
                        return cursor.rowcount
                    else:
                        await conn.commit()  # 对于其他操作，也提交事务
                        return None
        except Exception as e:
            AppError.DatabaseTransactionError.raise_(f"执行SQL语句 {sql} 失败: {e}")

    async def get_table_metadata(self, table_name: TableName) -> list[Row]:
        """获取表的元数据
        Args:
            table_name: 表名枚举值
        Returns:
            表的元数据列表，每个元素是一个包含列信息的字典，包含列名、数据类型、是否主键等
            例如：
            [
                (0, 'id', 'INTEGER', 1, None, 1),      # 主键，NOT NULL
                (1, 'name', 'TEXT', 1, None, 0),       # NOT NULL，无默认值
                (2, 'age', 'INTEGER', 0, None, 0),     # 允许 NULL
                (3, 'email', 'TEXT', 0, 'unknown', 0)  # 默认值为 'unknown'
            ]
        """
        sql = self.statement_generator.generate_metadata_query_statement(
            table_name)
        try:
            result = await self.execute_sql(sql)
            if isinstance(result, list):
                return result
            else:
                AppError.DatabaseTransactionError.raise_("表元数据查询未返回结果集")
        except AppError.Exception as e:
            raise e
        except Exception as e:
            AppError.DatabaseTransactionError.raise_(f"执行表元数据查询语句失败: {e}")

    async def drop_table(self, table_name: TableName) -> None:
        """删除表
        Args:
            table_name: 表名枚举值
        """
        sql = self.statement_generator.generate_drop_table_statement(
            table_name)
        try:
            await self.execute_sql(sql)
        except AppError.Exception as e:
            raise e
        except Exception as e:
            AppError.DatabaseTransactionError.raise_(f"执行删除表语句失败: {e}")

    async def create_table(self, table_name: TableName) -> None:
        """创建表
        Args:
            table_name: 表名枚举值
        """
        sql = self.statement_generator.generate_create_table_statement(
            table_name)
        try:
            await self.execute_sql(sql)
        except AppError.Exception as e:
            raise e
        except Exception as e:
            AppError.DatabaseTransactionError.raise_(f"执行创建表语句失败: {e}")

    async def upsert_data(self,
                          table_name: TableName,
                          data: dict,
                          conflict_column: str | None = None) -> None:
        """插入或更新数据
        Args:
            table_name: 表名枚举值
            data: 要插入或更新的数据字典，键为列名，值为对应的值
            conflict_column: 可选的冲突列名，用于指定在冲突时根据该列进行更新
        """
        sql = self.statement_generator.generate_upsert_statement(
            table_name, data, conflict_column)
        try:
            await self.execute_sql(sql, data)
        except AppError.Exception as e:
            raise e
        except Exception as e:
            AppError.DatabaseUpsertError.raise_(f"执行插入或更新数据语句失败: {e}")

    async def select_data(self,
                          table_name: TableName,
                          columns: list[str] | None = None,
                          where: dict | None = None,
                          order_by: str | None = None,
                          order_type: Literal["ASC", "DESC"] | None = None,
                          limit: int | None = None,
                          offset: int | None = None
                          ) -> list[Row]:
        """查询数据
        Args:
            table_name: 表名枚举值
            columns: 可选的列名列表，用于指定要查询的列，默认查询所有列
            where: 可选的WHERE子句条件字典，键为列名，值为对应的值，用于筛选数据
            order_by: 可选的ORDER BY子句字符串，用于指定排序方式
            limit: 可选的 LIMIT 子句整数，用于限制返回的行数
            offset: 可选的 OFFSET 子句整数，用于指定偏移量
        Returns:
            查询结果列表，每个元素是一个包含列值的元组
        """
        # 构建完整的参数字典
        parameters = {}
        # 添加 WHERE 条件参数
        if where:
            parameters.update(where)
        sql = self.statement_generator.generate_select_statement(
            table_name, columns, where, order_by, order_type, limit, offset)
        try:
            result = await self.execute_sql(sql, parameters)
            if isinstance(result, list):
                return result
            else:
                AppError.DatabaseTransactionError.raise_("查询数据未返回结果集")
        except AppError.Exception as e:
            raise e
        except Exception as e:
            AppError.DatabaseTransactionError.raise_(f"执行查询数据语句失败: {e}")
