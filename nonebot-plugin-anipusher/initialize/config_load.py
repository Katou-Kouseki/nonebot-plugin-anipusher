"""配置加载器模块

负责应用程序启动时的配置初始化工作，按顺序加载和验证所有必要的配置信息。
"""

import nonebot_plugin_localstore as store
import json
from nonebot import get_plugin_config
from nonebot import logger
from pydantic import ValidationError
from ..exceptions import AppError
from ..config import WORKDIR, APPCONFIG, PUSHTARGET
from ..model import Config


class ConfigLoader:
    """配置加载器

    配置加载器负责按特定顺序初始化应用程序所需的所有配置：
    1. 本地存储路径:设置缓存目录、配置文件和数据库文件的路径
    2. 自定义配置:加载API密钥、服务器地址等核心配置参数
    3. 推送目标配置：加载群组和私聊消息的推送目标设置

    配置加载过程中会进行错误处理和日志记录，确保应用程序能够正确初始化。
    """

    @classmethod
    def create_and_load(cls) -> "ConfigLoader":
        """创建配置加载器实例并自动加载所有配置

        这是配置加载的入口方法，创建实例后自动执行完整的配置加载流程。

        Returns:
            ConfigLoader: 已成功加载所有配置的实例
        Raises:
            AppError: 配置加载过程中发生任何错误时抛出
        Example:
            >>> loader = ConfigLoader.create_and_load()
            >>> # 所有配置已自动加载完成
        """
        loader = cls()
        loader.load_all_configs()
        return loader

    def load_all_configs(self) -> None:
        """按固定顺序加载所有配置

        按照依赖关系顺序执行配置加载，确保先加载基础配置再加载依赖它的配置。
        执行顺序：
        1. 本地存储路径：为其他配置提供文件系统基础
        2. 自定义配置：加载API密钥、服务器地址等核心参数
        3. 推送目标配置：加载消息推送的目标设置

        Raises:
            AppError: 任一配置加载失败时抛出，阻止后续配置继续加载
        """
        self._load_localstore_path()
        self._load_custom_config()
        self._load_pushtarget()

    def _load_localstore_path(self) -> None:
        """加载本地配置存储路径
        设置应用程序所需的文件系统路径，包括缓存目录、配置文件和数据库文件。
        这些路径用于后续配置的存储和读取。
        Raises:
            AppError.ResourceNotFound: 当路径设置失败时抛出
        """
        try:
            WORKDIR.cache_dir = store.get_plugin_cache_dir()
            WORKDIR.config_file = store.get_plugin_config_file(
                filename="anipusheruser.json")
            WORKDIR.data_file = store.get_plugin_data_file(
                filename="anipusherdb.db")
            WORKDIR.message_template_dir = store.get_plugin_data_dir() / "message_template"
        except Exception as e:
            AppError.ResourceNotFound.raise_(
                f"Nonebot localstore配置路径加载异常 —— {e}")

    def _load_custom_config(self) -> None:
        """加载自定义配置
        从nonebot的配置系统中加载用户自定义的配置参数，包括：
        - Emby服务器地址和API密钥
        - TMDB API授权信息
        - 网络代理设置
        Raises:
            AppError.ResourceNotFound: 当配置验证失败时抛出，通常是因为缺少必要的配置项
        """
        try:
            config = get_plugin_config(Config).anipusher
            APPCONFIG.emby_host = config.emby_host
            APPCONFIG.emby_key = config.emby_key
            APPCONFIG.tmdb_authorization = config.tmdb_authorization
            APPCONFIG.proxy = config.proxy
        except ValidationError as e:
            logger.opt(colors=True).error(
                "<r>HealthCheck</r>:配置读取异常!请确认env文件是否已配置")
            logger.opt(colors=True).error(
                "<r>HealthCheck</r>:如果不知道如何填写,请阅读https://github.com/AriadusTT/nonebot-plugin-anipusher/blob/main/README.md")
            AppError.ResourceNotFound.raise_(
                f"配置读取异常 —— {e}")

    def _load_pushtarget(self) -> None:
        """加载推送目标配置
        从配置文件中读取群组和私聊的推送目标设置。如果配置文件不存在，
        会自动创建一个包含默认空配置的新文件。
        处理逻辑：
        1. 检查配置文件路径是否有效
        2. 如果文件不存在，创建新的配置文件
        3. 读取并解析配置文件内容
        4. 验证并设置群组推送目标
        5. 验证并设置私聊推送目标
        Raises:
            AppError.MissingConfiguration: 配置文件路径无效时抛出
            AppError.MissingParameter: 配置数据为空时抛出
            AppError.UnknownError: 读取或解析配置文件时发生未知错误
        """
        if not WORKDIR.config_file:
            AppError.ResourceNotFound.raise_("项目缓存目录缺失")
        # 检查配置文件是否存在, 如果不存在则创建
        if not WORKDIR.config_file.is_file():
            self._reset_pushtarget_data()
        try:
            target_text = WORKDIR.config_file.read_text(encoding="utf-8")
        except PermissionError as e:
            AppError.PermissionDenied.raise_(
                f"读取用户配置文件权限不足 —— {e}")
        except IOError as e:
            AppError.FileIOError.raise_(
                f"读取用户配置文件失败 —— {e}")
        except Exception as e:
            AppError.ConfigFileReadError.raise_(
                f"{e}")
        try:
            target = json.loads(target_text)
            if not target:
                AppError.MissingParameter.raise_("用户配置文件为空")
            if group_target := target.get("GroupPushTarget"):
                if not isinstance(group_target, dict):
                    logger.opt(colors=True).error(
                        f"<r>HealthCheck</r>:GroupPushTarget格式错误, 预期为dict, 实际为{type(group_target)}")
                    PUSHTARGET.GroupPushTarget = {}
                PUSHTARGET.GroupPushTarget = group_target
            if private_target := target.get("PrivatePushTarget"):
                if not isinstance(private_target, dict):
                    logger.opt(colors=True).error(
                        f"<r>HealthCheck</r>:PrivatePushTarget格式错误, 预期为dict, 实际为{type(private_target)}")
                    PUSHTARGET.PrivatePushTarget = {}
                PUSHTARGET.PrivatePushTarget = private_target
        except json.JSONDecodeError as e:
            AppError.InvalidConfiguration.raise_(f"配置文件JSON格式错误 —— {e}")
        except AppError.Exception:
            raise
        except Exception as e:
            AppError.ConfigFileReadError.raise_(f"{e}")

    def _reset_pushtarget_data(self) -> None:
        """重建用户推送目标配置文件
        当推送目标配置文件不存在时，创建一个包含默认空配置的新文件。
        会自动创建必要的父目录。
        处理流程：
        1. 检查并创建父目录（如果不存在）
        2. 创建新的配置文件，包含空的群组和私聊推送目标
        3. 记录日志信息，提示文件创建位置
        Raises:
            AppError.UnknownError: 创建文件或目录时发生错误
        """
        try:
            if not WORKDIR.config_file:
                AppError.ResourceNotFound.raise_("项目缓存目录缺失")
            if not WORKDIR.config_file.parent.is_dir():
                WORKDIR.config_file.parent.mkdir(parents=True)
            logger.opt(colors=True).info(
                f"<g>HealthCheck</g>:用户数据文件已重建于:{WORKDIR.config_file}")
        except PermissionError as e:
            AppError.PermissionDenied.raise_(f"创建配置文件权限不足 —— {e}")
        except IOError as e:
            AppError.FileIOError.raise_(f"配置文件读写失败 —— {e}")
        except Exception as e:
            AppError.ConfigFileResetError.raise_(f"{e}")
