"""模型映射配置模块

提供数据模型类和字符串标识符之间的映射关系，用于配置验证和数据处理
"""
from enum import Enum
from pydantic import BaseModel
from ..exceptions import AppError
"""
调用方法示例：python
# 获取EMBY表对应的模型类
emby_model = TableName.EMBY.get_model_class() # 返回: EmbyItem 类
# 直接使用枚举值
emby_table_name = TableName.EMBY.value # 返回: "EMBY"
# 获取所有枚举的value值
[table.value for table in TableName] # 返回: ["EMBY", "ANIRSS", "ANIME"]
# 获取所有枚举的name值
list(TableName.__members__.keys()) # 返回: ["EMBY", "ANIRSS", "ANIME"]
"""


class TableName(Enum):
    """
    数据表名称枚举类
    用于严格限制可用的表名参数，提供类型安全的表名引用
    """
    EMBY = "EMBY"
    ANIRSS = "ANIRSS"
    ANIME = "ANIME"

    def get_model_class(self) -> type[BaseModel]:
        """获取当前表名枚举值对应的模型类
        Returns:
            对应的模型类（EmbyItem、AniRssItem或AnimeItem）
        Raises:
            AppError.InvalidParameter: 当表名枚举值没有对应的模型类时
        """
        from ..model import EmbyItem, AniRssItem, AnimeItem
        model_class = {
            TableName.EMBY: EmbyItem,
            TableName.ANIRSS: AniRssItem,
            TableName.ANIME: AnimeItem
        }.get(self)

        if model_class is None:
            AppError.InvalidParameter.raise_(f"未找到表名 {self.value} 对应的模型类")
        return model_class
