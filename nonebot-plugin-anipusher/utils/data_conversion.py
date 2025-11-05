from typing import Any
import json
import base64
from pathlib import Path
from ..mapping import TableName
from ..exceptions import AppError


def convert_python_type_to_sqlite(python_type) -> str:
    """将Python类型转换为SQLite类型
    Args:
        python_type: Python类型
    Returns:
        对应的SQLite类型字符串
    """
    type_str = str(python_type)
    if 'str' in type_str:
        return 'TEXT'
    elif 'int' in type_str:
        return 'INTEGER'
    elif 'float' in type_str:
        return 'REAL'
    elif 'datetime' in type_str:
        return 'TEXT'
    elif 'bool' in type_str:
        return 'INTEGER'
    else:
        return 'TEXT'  # 默认使用TEXT类型


def convert_to_str(v: Any) -> str | None:
    """将任意类型转换为字符串，若为空则返回None
    Args:
        v: 任意类型的值
    Returns:
        转换后的字符串或None
    """
    if v is None:
        return None
    try:
        str_value = str(v).strip()
        return str_value if str_value else None
    except Exception:
        return None


def convert_db_list_first_row_to_dict(source: TableName, db_data: list) -> dict:
    try:
        from ..database import schema_manager
        default_schema = schema_manager.get_default_schema(source).copy()
        if not db_data:
            AppError.MissingParameter.raise_(
                f"DB TUPLE ——> DICT 转换失败 —— 未提供有效的{source.value}库数据")
        result = {}
        for (key, value) in zip(default_schema.keys(), db_data[0]):
            if isinstance(value, str):
                try:
                    if value.strip().startswith(('{', '[')):
                        result[key] = json.loads(value)
                    else:
                        result[key] = value
                except json.JSONDecodeError:
                    result[key] = value
            else:
                result[key] = value
        return result
    except AppError.Exception:
        raise
    except Exception as e:
        AppError.DataConversionError.raise_(f"数据库记录转换为字典失败: {str(e)}")


def convert_image_path_to_base64(image_path: str | Path) -> str:
    """将图片路径转换为Base64编码
    Args:
        image_path: 图片文件路径
    Returns:
        对应的Base64编码字符串
    """
    path = Path(image_path) if isinstance(
        image_path, str) else image_path
    if not path.exists():
        AppError.ResourceNotFound.raise_("图片文件路径不存在 —— 请检查图片CACHE下是否存在对应TMDB ID的图片")
    try:
        with open(image_path, "rb") as f:
            base64_data = base64.b64encode(f.read()).decode("utf-8")
        return f"base64://{base64_data}"
    except Exception as e:
        AppError.ImageConversionError.raise_(f"图片文件转换为Base64编码失败: {str(e)}")
