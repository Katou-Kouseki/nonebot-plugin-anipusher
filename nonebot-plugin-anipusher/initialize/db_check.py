"""数据库健康检查模块

负责在应用程序启动时对数据库表进行健康检查，确保所有必要的数据表存在并且结构正确。
如果检测到表缺失或结构不一致，会自动重建表结构以保证数据完整性和应用程序正常运行。

主要功能：
- 检查表是否存在
- 验证表结构与模型定义是否一致
- 自动重建缺失或结构不一致的表
- 提供日志记录以便于问题追踪
"""
from ..mapping import TableName
from ..database import DatabaseOperator
from nonebot import logger
from ..exceptions import AppError


class DBHealthCheck:
    """数据库健康检查类
    提供数据库表的存在性检查和结构验证功能，当表缺失或结构不一致时自动执行修复操作。
    采用异步设计以配合应用程序的异步架构，并提供工厂方法便于使用。
    """
    @classmethod
    async def create_and_check(cls) -> 'DBHealthCheck':
        """创建并运行数据库健康检查实例的工厂方法
        Returns:
            DBHealthCheck: 已完成健康检查的实例对象
        Raises:
            AppError.Exception: 当健康检查过程中发生错误时抛出
        """
        instance = cls()
        await instance.run_validator()
        return instance

    async def run_validator(self):
        """运行数据库健康检查验证器
        遍历所有需要检查的表，验证表的存在性和结构正确性。
        对于缺失的表，自动创建；对于结构不一致的表，先删除再重建。
        Raises:
            AppError.Exception: 当表操作过程中发生应用程序定义的错误时抛出
            AppError.UnknownError: 当发生未预期的错误时抛出
        """
        try:
            # 创建数据库操作实例
            db_operator = DatabaseOperator()

            # 遍历所有表名枚举值
            for table_name in TableName:
                # 获取表的元数据信息
                result = await db_operator.get_table_metadata(table_name)
                # 检查元数据是否为空（表不存在）
                if not result:
                    try:
                        # 创建缺失的表
                        await db_operator.create_table(table_name)
                        logger.opt(colors=True).info(f"<g>HealthCheck</g>:数据表{table_name.value} <y>缺失</y> —— 重建 <g>SUCCESS</g>")
                        continue
                    except Exception:
                        # 重新抛出异常，保持原始错误上下文
                        raise
                # 验证表结构是否符合预期
                if not await self.validate_table_structure(result, table_name):
                    try:
                        # 重建结构不一致的表（先删除后创建）
                        await db_operator.drop_table(table_name)
                        await db_operator.create_table(table_name)
                        logger.opt(colors=True).warning(f"<y>HealthCheck</y>:数据表{table_name.value} <y>结构不一致</y> —— 重建 <g>SUCCESS</g>")
                    except Exception:
                        # 重新抛出异常，保持原始错误上下文
                        raise
        except AppError.Exception:
            # 直接重新抛出应用程序定义的错误
            raise
        except Exception as e:
            # 捕获其他未预期的错误并转换为应用程序错误
            AppError.ValidationError.raise_(f"数据库健康检查验证器运行失败 —— {e}")

    async def validate_table_structure(self, db_fetchall, table_name: TableName) -> bool:
        """验证数据库表结构是否符合模型定义
        通过比较数据库中表的字段集合与模型类定义的字段集合，判断表结构是否一致。
        Args:
            db_fetchall: 数据库查询返回的表元数据结果
            table_name: 要验证的表名枚举值
        Returns:
            bool: 表结构是否与模型定义一致，一致返回True，不一致返回False
        """
        # 从数据库返回的结果中提取字段名集合
        # 假设db_fetchall中每个元素的第二个值是字段名
        db_keys = set([column[1] for column in db_fetchall])
        # 获取表名对应的模型类
        model_class = table_name.get_model_class()
        # 从模型类的JSON schema中提取属性名集合
        model_keys = set(model_class.model_json_schema()['properties'].keys())
        # 比较数据库字段集合和模型字段集合是否完全一致
        if db_keys != model_keys:
            return False
        return True
