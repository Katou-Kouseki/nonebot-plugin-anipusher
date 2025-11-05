
# 导入必要的模块
from ..mapping import TableName
from ..exceptions import AppError
from ..utils import convert_python_type_to_sqlite
from typing import Literal


class StatementGenerator:
    @staticmethod
    def generate_create_table_statement(table_name: TableName) -> str:
        """根据表名称生成创建表的SQL语句
        Args:
            table_name: TableName枚举值，表示要创建的表名
        Returns:
            生成的CREATE TABLE SQL语句
        Raises:
            AppError: 当无法生成表结构或SQL语句时
        """
        try:
            # 获取模型类
            model_class = table_name.get_model_class()
            # 解析字段定义
            column_definitions = []
            for field_name, field_info in model_class.model_fields.items():
                # 获取字段类型
                sqlite_type = convert_python_type_to_sqlite(field_info.annotation)
                parts = [f"{field_name} {sqlite_type}"]
                # 处理NOT NULL约束
                if field_info.is_required():
                    parts.append("NOT NULL")
                # 处理DEFAULT约束
                if field_info.default is not None and field_info.default != Ellipsis:
                    default_value = field_info.default
                    # 根据类型处理默认值的格式
                    if sqlite_type == 'TEXT':
                        default_value = f"'{default_value}'" if default_value is not None else "NULL"
                    elif isinstance(default_value, bool):
                        default_value = 1 if default_value else 0
                    elif default_value is None:
                        default_value = "NULL"
                    parts.append(f"DEFAULT {default_value}")
                # 处理PRIMARY KEY约束
                if field_info.json_schema_extra and field_info.json_schema_extra.get('primary_key', False):
                    parts.append("PRIMARY KEY")
                    # 如果是INTEGER类型且是主键，添加AUTOINCREMENT
                    if sqlite_type == 'INTEGER':
                        parts.append("AUTOINCREMENT")
                # 将列定义添加到列表中
                column_definitions.append(" ".join(parts))
            # 拼接CREATE TABLE语句
            sql = f"CREATE TABLE IF NOT EXISTS {table_name.value} ({', '.join(column_definitions)})"
            return sql
        except Exception as e:
            AppError.UnknownError.raise_(f"生成SQLCREATE TABLE语句时出现异常: {e}")

    @staticmethod
    def generate_metadata_query_statement(table_name: TableName) -> str:
        """根据表名称生成查询表元数据的SQL语句
        Args:
            table_name: TableName枚举值，表示要查询元数据的表名
        Returns:
            生成的PRAGMA table_info SQL语句
        Raises:
            AppError: 当无法生成查询语句时
        """
        try:
            sql = f"PRAGMA table_info({str(table_name.value)})"
        except Exception as e:
            AppError.UnknownError.raise_(f"生成PRAGMA table_info语句时出现异常: {e}")
        return sql

    @staticmethod
    def generate_drop_table_statement(table_name: TableName) -> str:
        """根据表名称生成删除表的SQL语句
        Args:
            table_name: TableName枚举值，表示要删除的表名
        Returns:
            生成的DROP TABLE IF EXISTS SQL语句
        Raises:
            AppError: 当无法生成删除语句时
        """
        try:
            sql = f"DROP TABLE IF EXISTS {str(table_name.value)}"
        except Exception as e:
            AppError.UnknownError.raise_(f"生成DROP TABLE IF EXISTS语句时出现异常: {e}")
        return sql

    @staticmethod
    def generate_upsert_statement(table_name: TableName, data: dict, conflict_column: str | None = None) -> str:
        """生成INSERT语句，可选择支持冲突时仅更新data中提供的字段
        Args:
            table_name: TableName枚举值，表示要操作的表名
            data: 要插入的数据字典，冲突时仅更新字典中提供的非None值字段
            conflict_columns: 用于检测冲突的列，当为None或空列表时只生成INSERT语句
        Returns:
            str: 当conflict_columns为空时返回简单INSERT语句，否则返回带ON CONFLICT DO UPDATE的INSERT语句
        Raises:
            AppError: 当生成语句过程中发生异常时
        """
        try:
            model_class = table_name.get_model_class()
            table_keys = list(model_class.model_fields.keys())
            # 提取所有有效字段（过滤掉None值和不存在于表中的字段）
            valid_data = {key: value for key, value in data.items() if value is not None and key in table_keys}
            # columns为所有有效字段（过滤掉None值和不存在于表中的字段）
            columns = list(valid_data.keys())  # 过滤掉None值和不存在于表中的字段后的有效列
            if not columns:
                AppError.InvalidParameter.raise_(f"生成UPSERT语句时出现异常,数据中没有有效字段可插入，请检查数据：{data}")
            # 找出所有主键列（假设可能有多个主键）
            primary_keys = [
                col for col in table_keys
                if (extra := getattr(model_class.model_fields[col], "json_schema_extra", None))
                and isinstance(extra, dict)
                and extra.get("primary_key", False)
            ]
            # 基础INSERT部分
            sql = f"INSERT INTO {str(table_name.value)} ({', '.join(columns)}) VALUES ({', '.join(f':{col}' for col in columns)})"
            if conflict_column:
                if conflict_column not in table_keys:
                    AppError.InvalidParameter.raise_(f"生成UPSERT语句时出现异常,指定的冲突列 {conflict_column} 不存在于表{table_name.value}的字段定义{table_keys}中")
                if conflict_column not in columns:
                    AppError.InvalidParameter.raise_(f"生成UPSERT语句时出现异常,未提供有效的冲突列 {conflict_column}数据，请检查参数：{data} ")
                # 更新时排除所有主键字段（无论是否提供了conflict_column）
                update_cols = [f"{col}=excluded.{col}" for col in columns if col != conflict_column and col not in primary_keys]
                sql += f" ON CONFLICT ({conflict_column}) DO UPDATE SET {', '.join(update_cols)}"
            return sql.strip()
        except AppError.Exception as e:
            raise e
        except Exception as e:
            AppError.UnknownError.raise_(f"生成UPSERT语句时出现异常: {e}")

    @staticmethod
    def generate_select_statement(table_name: TableName,
                                  columns: list[str] | None = None,
                                  where: dict | None = None,
                                  order_by: str | None = None,
                                  order_type: Literal["ASC", "DESC"] | None = None,
                                  limit: int | None = None,
                                  offset: int | None = None
                                  ) -> str:
        """生成SELECT SQL查询语句
        Args:
            table_name: TableName枚举值,表示要查询的表名
            columns: 要查询的列名列表,None表示所有列
            where: WHERE条件字典 {列名: 值}
            order_by: 排序字段，如 "id"
            order_type: 排序类型，"ASC" 或 "DESC"
            limit: 返回记录数限制
            offset: 偏移量
        Returns:
            str: 构造的SQL查询字符串
        Raises:
            AppError: 当生成语句过程中发生异常时
        """
        try:
            table_keys = list(table_name.get_model_class().model_fields.keys())
            # 处理列名
            if columns is None or len(columns) == 0:
                column_clause = "*"
            else:
                # 验证列名是否有效
                valid_columns = [col for col in columns if col in table_keys]
                if not valid_columns:  # 全部列无效时才报错
                    AppError.InvalidParameter.raise_(f"生成SELECT语句时出现异常,没有有效列可查询，请检查列名：{columns}")
                column_clause = ", ".join(valid_columns)  # 仅使用有效列
            sql = f"SELECT {column_clause} FROM {str(table_name.value)}"
            # 处理WHERE条件
            if where and len(where) > 0:
                # 验证WHERE条件中的列名是否有效
                valid_where = {col: val for col, val in where.items() if col in table_keys}
                if not valid_where:  # 全部WHERE条件列无效时才报错
                    AppError.InvalidParameter.raise_(f"生成SELECT语句时出现异常,没有有效WHERE条件列可查询，请检查条件：{where}")
                conditions = []
                for col, val in valid_where.items():
                    if isinstance(val, str):
                        conditions.append(f"{col} = :{col}")  # 使用参数化查询
                    else:
                        conditions.append(f"{col} = :{col}")
                sql += " WHERE " + " AND ".join(conditions)
            # 处理排序
            if order_by:
                if order_by not in table_keys:
                    AppError.InvalidParameter.raise_(f"生成SELECT语句时出现异常,排序参数 {order_by} 不是有效的表参数，请检查")
                elif order_type not in ["ASC", "DESC"]:
                    AppError.InvalidParameter.raise_(f"生成SELECT语句时出现异常,排序类型 {order_type} 不是有效的值，请检查")
                sql += f" ORDER BY {order_by} {order_type}"
            # 处理分页
            if limit is not None:
                if limit <= 0:
                    AppError.InvalidParameter.raise_(f"生成SELECT语句时出现异常,LIMIT值必须大于0，当前值: {limit}")
                sql += f" LIMIT {limit}"
                if offset is not None:
                    if offset < 0:
                        AppError.InvalidParameter.raise_(f"生成SELECT语句时出现异常,OFFSET值不能为负数，当前值: {offset}")
                    sql += f" OFFSET {offset}"
            return sql.strip()
        except AppError.Exception as e:
            raise e
        except Exception as e:
            AppError.SqlGenerationError.raise_(f"{e}")
