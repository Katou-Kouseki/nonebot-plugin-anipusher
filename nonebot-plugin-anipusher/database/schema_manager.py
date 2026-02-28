# 导入必要的模块
from pydantic_core import PydanticUndefined
from typing import Any
from ..mapping import TableName
from ..exceptions import AppError


def get_table_names() -> list[str]:
    """
    获取所有表名
    Returns:
        所有表名的列表
    """
    return [table_name.value for table_name in TableName]


# 废弃 ！！！获取模型结构可用直接通过table_name.get_model_class()
def get_table_structure(table_name: TableName) -> dict[str, Any]:
    """
    获取指定表的结构
    Args:
        table_name: TableName枚举值
    Returns:
        表的结构字典
    Raises:
        ValueError: 当表名无效时
    """
    try:
        model_class = table_name.get_model_class()
        if hasattr(model_class, "model_json_schema"):
            return model_class.model_json_schema()
        else:
            return model_class.schema()
    except Exception as e:
        AppError.TableStructureError.raise_(f"{e}")


def get_default_schema(table_name: TableName) -> dict[str, Any]:
    """
    根据 Pydantic 模型生成带有默认值的空字典结构
    Args:
        table_name: TableName枚举值
    Returns:
        包含模型字段默认值的字典
    Raises:
        ValueError: 当表名无效时
    Example:
        >>> get_default_schema(TableName.EMBY)
        {
            'id': None,
            'send_status': 0,
            'timestamp': None,
            'type': None,
            ...
        }
    """
    try:
        # 获取对应的模型类
        model_class = table_name.get_model_class()
        # 创建包含默认值的字典
        default_schema = {}
        # 兼容 Pydantic V1 和 V2
        fields = getattr(model_class, "model_fields", getattr(model_class, "__fields__", {}))
        # 遍历模型的所有字段
        for field_name, field_info in fields.items():
            # 获取字段的默认值
            if hasattr(field_info, 'get_default'):
                default_schema[field_name] = field_info.get_default()
            else:
                default_val = getattr(field_info, 'default', PydanticUndefined)
                if default_val is not PydanticUndefined and default_val is not Ellipsis:
                    default_schema[field_name] = default_val
                elif getattr(field_info, 'default_factory', None) is not None:
                    # 处理使用default_factory设置默认值的情况
                    default_schema[field_name] = field_info.default_factory() if callable(field_info.default_factory) else field_info.default_factory
                else:
                    # 如果没有默认值，设置为None
                    default_schema[field_name] = None
        return default_schema
    except Exception as e:
        AppError.SchemaGenerationError.raise_(f"{e}")
