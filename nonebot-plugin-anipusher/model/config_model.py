# 导入必要的模块
from pathlib import Path
from typing import Optional, Dict, List
from pydantic import BaseModel, Field, validator
from ..mapping import TableName


class AniPusherConfig(BaseModel):
    """应用程序核心配置模型，存储全局配置参数

    包含API密钥、服务器地址等关键配置信息，用于连接外部服务
    """
    proxy: Optional[str] = Field(default=None, description="代理服务器地址")
    tmdb_authorization: Optional[str] = Field(default=None, description="TMDB API密钥")
    emby_host: Optional[str] = Field(default=None, description="Emby服务器地址")
    emby_key: Optional[str] = Field(default=None, description="Emby API密钥")
    
    @validator('proxy', 'tmdb_authorization', 'emby_host', 'emby_key', pre=True)
    def convert_none_str(cls, v):
        """将字符串'None' 转换为 None"""
        if isinstance(v, str):
            if v.strip().lower() == 'none' or v.strip() == '':
                return None
        return v


class Config(BaseModel):
    """
    配置映射
    简化配置命名
    """
    anipusher: AniPusherConfig


class FeatureFlags(BaseModel):
    """功能开关配置模型，控制各功能模块的启用状态

    用于管理应用程序中各种功能的启用/禁用，方便配置和调试
    """
    emby_enabled: bool = Field(default=False, description="Emby功能开关")
    tmdb_enabled: bool = Field(default=False, description="TMDB功能开关")


class PushTarget(BaseModel):
    """推送目标配置模型，管理消息推送的目标群组和用户

    包含群组推送目标和私聊推送目标，用于控制不同类型消息的分发范围
    """
    GroupPushTarget: Dict[str, List[str]] = Field(default_factory=dict, description="工作群组推送目标")
    PrivatePushTarget: Dict[str, List[str]] = Field(default_factory=dict, description="工作私聊推送目标")

    @validator('GroupPushTarget', 'PrivatePushTarget', pre=True)
    def check_push_target(cls, v: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """
        检查推送目标配置的合法性
        验证规则:
        1. 确保推送目标字典中的键（模型类型）在系统支持的范围内
        2. 使用 TableName 枚举作为有效键的参考标准
        参数:
            v: 推送目标字典，格式为 {模型类型: [目标ID列表]}
                例如: {"EMBY": ["group1", "group2"], "ANIME": ["private1"]}
        返回:
            验证后的推送目标字典
        抛出:
            ValueError: 当发现不支持的模型类型时
        注意:
            - 此验证器同时应用于 GroupPushTarget 和 PrivatePushTarget 字段
        """
        valid_targets = [table_name.value for table_name in TableName]
        for key in v:
            if key not in valid_targets:
                raise ValueError(f"推送队列结构错误，不支持来源为：{key}")
        return v


class WorkDir(BaseModel):
    """工作目录配置模型，定义应用程序使用的各种文件路径

    管理缓存目录、数据库文件和配置文件的存储位置
    """
    cache_dir: Optional[Path] = Field(default=None, description="图片缓存的路径")
    data_file: Optional[Path] = Field(default=None, description="db数据库文件的路径")
    config_file: Optional[Path] = Field(default=None, description="推送对象json文件的路径")
    message_template_dir: Optional[Path] = Field(default=None, description="默认消息模板")
