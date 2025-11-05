#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Anime数据处理器模块
该模块负责处理来自不同数据源(如Emby、AniRSS)的动画信息，将其合并并更新到数据库中。
支持提取和整合TMDB ID、标题、评分、流派、URL链接等信息。
"""

# 第三方库
from nonebot import logger
# 项目内部模块
from ....config import APPCONFIG, FUNCTION
from ....database import DatabaseOperator, schema_manager
from ....exceptions import AppError
from ....mapping import TableName
from ....utils import (
    convert_db_list_first_row_to_dict,
    generate_emby_image_url,
    generate_emby_series_url
)


class AnimeProcessor:
    """
    Anime数据处理器类
    负责处理和整合来自不同数据源的动画信息，并将其更新到数据库中。
    支持数据格式化、数据库查询、数据合并和数据库更新等功能。
    """

    def __init__(self, source: TableName, structured_data: dict | None = None):
        """
        初始化Anime数据处理器
        Args:
            source: 数据源表名，如EMBY或ANIRSS
            structured_data: 结构化的动画数据字典，默认为None
        """
        self.source = source
        self.structured_data = structured_data
        self.tmdb_id = None

    async def process(self):
        """
        处理动画数据的主方法
        执行数据格式化、数据库查询、数据合并和数据库更新的完整流程。
        处理过程中包含异常捕获和日志记录。
        """
        try:
            if not self.source:
                AppError.MissingParameter.raise_("接收参数时 未提供参数 source")
            if not self.structured_data:
                AppError.MissingParameter.raise_("接收参数时 未提供参数 structured_data")
        except Exception as e:
            logger.opt(colors=True).error(
                f"<r>{self.source.value}</r>:Anime数据处理   |<r>Failed</r> —— {e}")
            return
        try:
            reformated_structured_data = await self._reformat()
        except Exception as e:
            logger.opt(colors=True).error(
                f"<r>{self.source.value}</r>:Anime数据处理   |<r>Failed</r> —— {e}")
            return
        try:
            if not self.tmdb_id:
                logger.opt(colors=True).warning(
                    f"<y>{self.source.value}</y>:未提供有效的TMDB ID —— 跳过Anime数据库更新")
                return
            db_data = await self._select_from_db()
            if db_data:
                db_structured_data = convert_db_list_first_row_to_dict(TableName.ANIME,
                                                                       db_data)
            else:
                db_structured_data = schema_manager.get_default_schema(TableName.ANIME).copy()
        except Exception as e:
            logger.opt(colors=True).error(
                f"<r>{self.source.value}</r>:{str(e)}"
            )
            logger.opt(colors=True).error(
                f"<r>{self.source.value}</r>:查询数据库失败,但TMDB ID有效 —— 尝试强制更新")
            db_structured_data = schema_manager.get_default_schema(TableName.ANIME).copy()
        try:
            merged_structured_data = self._merge_structured_data(db_structured_data, reformated_structured_data)
        except Exception:
            logger.opt(colors=True).error(
                f"<r>{self.source.value}</r>:Anime数据处理   |<r>FAILED</r> —— 合并数据失败,更新数据库已被跳过")
            return
        try:
            await self._update_db(merged_structured_data)
        except Exception as e:
            logger.opt(colors=True).error(
                f"<r>{self.source.value}</r>:更新ANIME数据库   |<r>FAILED</r> —— {str(e)}")
            logger.opt(colors=True).error(
                f"<r>{self.source.value}</r>:Anime数据处理   |<r>FAILED</r> —— 数据库更新失败")
            return

    class DataExtraction:
        """
        数据提取辅助类
        负责从不同数据源的结构化数据中提取各种动画信息字段。
        根据数据源类型选择不同的提取逻辑。
        """

        def __init__(self, source: TableName, structured_data: dict):
            """
            初始化数据提取类
            Args:
                source: 数据源表名，如EMBY或ANIRSS
                structured_data: 结构化的动画数据字典
            """
            self.source = source
            self.structured_data = structured_data

        def extract_tmdb_id(self) -> int | None:
            """
            提取TMDB ID
            根据数据源类型从结构化数据中提取TMDB ID。
            Returns:
                int | None: TMDB ID，如果不存在则返回None
            """
            if self.source == TableName.EMBY:
                return self.structured_data.get("tmdb_id")
            elif self.source == TableName.ANIRSS:
                return self.structured_data.get("tmdb_id")
            return None

        def extract_emby_title(self) -> str | None:
            """
            从Emby结构化数据中提取标题
            Returns:
                str | None: Emby标题，如果数据源不是EMBY或标题不存在则返回None
            """
            if self.source == TableName.EMBY:
                return self.structured_data.get("title")
            return None

        def extract_tmdb_title(self) -> str | None:
            """
            从AniRSS结构化数据中提取TMDB标题
            Returns:
                str | None: TMDB标题，如果数据源不是ANIRSS或标题不存在则返回None
            """
            if self.source == TableName.ANIRSS:
                return self.structured_data.get("title")
            return None

        def extract_score(self) -> float | None:
            """
            从结构化数据中提取评分
            Returns:
                float | None: 评分，如果数据源不是ANIRSS或评分不存在则返回None
            """
            if self.source == TableName.ANIRSS:
                return self.structured_data.get("score")
            return None

        def extract_genres(self) -> list[str] | None:
            """
            从结构化数据中提取流派
            Returns:
                list[str] | None: 流派列表，如果数据源不是EMBY或流派不存在则返回None
            """
            if self.source == TableName.EMBY:
                return self.structured_data.get("genres")
            return None

        def extract_tmdb_url(self) -> str | None:
            """
            从结构化数据中提取TMDB URL
            Returns:
                str | None: TMDB链接，如果数据源不是ANIRSS或链接不存在则返回None
            """
            if self.source == TableName.ANIRSS:
                return self.structured_data.get("tmdb_url")
            return None

        def extract_bgm_url(self) -> str | None:
            """
            从结构化数据中提取Bangumi URL
            Returns:
                str | None: Bangumi链接，如果数据源不是ANIRSS或链接不存在则返回None
            """
            if self.source == TableName.ANIRSS:
                return self.structured_data.get("bangumi_url")
            return None

        def extract_anirss_image_url(self) -> str | None:
            """
            从ANIRSS结构化数据中提取图片URL
            Returns:
                str | None: 图片链接，如果数据源不是ANIRSS或链接不存在则返回None
            """
            if self.source == TableName.ANIRSS:
                return self.structured_data.get("image_url")
            return None

        def extract_emby_image_url(self) -> str | None:
            """
            从Emby结构化数据中提取图片URL
            如果Emby功能未启用或生成链接失败，记录日志并返回None。
            Returns:
                str | None: Emby图片链接，如果数据源不是EMBY、Emby功能未启用或生成失败则返回None
            """
            if self.source == TableName.EMBY:
                if not FUNCTION.emby_enabled:
                    logger.opt(colors=True).info(
                        "<y>EMBY</y>:未启用Emby功能，无法提取Emby图片链接")
                    return None
                host = APPCONFIG.emby_host
                tag = self.structured_data.get("series_tag")
                series_id = self.structured_data.get("series_id")
                try:
                    return generate_emby_image_url(host, series_id, tag)
                except Exception as e:
                    logger.opt(colors=True).error(
                        f"<r>EMBY</r>:生成Emby图片链接失败 —— {str(e)}")
                    return None
            else:
                return None

        def extract_emby_series_url(self) -> str | None:
            """
            从Emby结构化数据中提取系列URL
            如果Emby功能未启用或生成链接失败，记录日志并返回None。
            Returns:
                str | None: Emby系列链接，如果数据源不是EMBY、Emby功能未启用或生成失败则返回None
            """
            if self.source == TableName.EMBY:
                if not FUNCTION.emby_enabled:
                    logger.opt(colors=True).info(
                        "<y>EMBY</y>:未启用Emby功能，无法生成Emby系列链接")
                    return None
                host = APPCONFIG.emby_host
                series_id = self.structured_data.get("series_id")
                server_id = self.structured_data.get("server_id")
                try:
                    return generate_emby_series_url(host, series_id, server_id)
                except Exception as e:
                    logger.opt(colors=True).error(
                        f"<r>EMBY</r>:生成Emby系列链接失败 —— {str(e)}")
                    return None
            else:
                return None

    async def _reformat(self):
        """
        重新格式化动画数据
        从数据源中提取各种动画信息，并将其填充到标准数据结构中。
        Returns:
            dict: 格式化后的动画数据字典
        Raises:
            AppError.UnknownError: 当数据结构转换失败时
        """
        try:
            if not self.structured_data:
                AppError.MissingParameter.raise_("接收参数时 未提供参数 structured_data")
            extract = self.DataExtraction(self.source, self.structured_data)
            default_schame = schema_manager.get_default_schema(TableName.ANIME).copy()
            default_schame.update({
                "tmdb_id": extract.extract_tmdb_id(),
                "emby_title": extract.extract_emby_title(),
                "tmdb_title": extract.extract_tmdb_title(),
                "score": extract.extract_score(),
                "genres": extract.extract_genres(),
                "tmdb_url": extract.extract_tmdb_url(),
                "bangumi_url": extract.extract_bgm_url(),
                "ainrss_image_url": extract.extract_anirss_image_url(),
                "emby_image_url": extract.extract_emby_image_url(),
                "emby_series_url": extract.extract_emby_series_url(),
            })
            self.tmdb_id = default_schame.get("tmdb_id")
            return default_schame
        except Exception as e:
            AppError.UnknownError.raise_(f"{self.source.value}->ANIME 数据结构转换失败 —— {str(e)}")

    async def _select_from_db(self):
        """
        从数据库中查询Anime数据
        根据TMDB ID从数据库中查询现有的动画数据。
        Returns:
            list: 查询结果列表，包含匹配的数据库记录
        Raises:
            AppError.Exception: 当数据库操作失败时
            AppError.UnknownError: 当发生未知错误时
        """
        try:
            db_operator = DatabaseOperator()
            return await db_operator.select_data(table_name=TableName.ANIME, where={"tmdb_id": self.tmdb_id}, limit=1)
        except AppError.Exception:
            raise
        except Exception as e:
            AppError.UnknownError.raise_(f"查询数据库失败 —— {str(e)}")

    def _merge_structured_data(self, db_data: dict, new_data: dict) -> dict:
        """
        合并数据库数据和新数据
        将数据库中的旧数据与新提取的数据进行合并，保留特定的强制维持字段。
        对于其他字段，优先使用新数据的值，如果新数据中不存在则使用旧数据的值。
        Args:
            db_data: 从数据库中获取的旧数据
            new_data: 新提取并格式化的数据
        Returns:
            dict: 合并后的数据字典
        Raises:
            AppError.MissingParameter: 当缺少必要参数时
            AppError.UnknownError: 当发生未知错误时
        """
        try:
            force_fields = ["group_subscriber",
                            "private_subscriber"]  # 强制维持字段，该些字段不会从新数据中获取
            merged_structured_data = schema_manager.get_default_schema(TableName.ANIME).copy()
            if not db_data:
                AppError.MissingParameter.raise_("合并数据时，未提供参数db_data")
            if not new_data:
                AppError.MissingParameter.raise_("合并数据时，未提供参数new_data")
            for key in merged_structured_data:
                if key in force_fields:
                    merged_structured_data[key] = db_data.get(key)
                    continue
                if new_data.get(key):
                    merged_structured_data[key] = new_data.get(key)
                else:
                    merged_structured_data[key] = db_data.get(key)
            logger.opt(colors=True).info(
                f"<g>{self.source.value}</g>:Anime数据合并   |<g>SUCCESS</g>")
            return merged_structured_data
        except AppError.Exception as e:
            logger.opt(colors=True).error(
                f"<r>{self.source.value}</r>:Anime数据合并   |<r>FAILED</r> - {str(e)}")
            raise e
        except Exception as e:
            logger.opt(colors=True).error(
                f"<r>{self.source.value}</r>:Anime数据合并   |<r>FAILED</r> - {str(e)}")
            AppError.UnknownError.raise_(f"{str(e)}")

    async def _update_db(self, data: dict):
        """
        更新数据库中的动画数据
        使用合并后的数据更新数据库，如果记录已存在则更新，不存在则插入。
        Args:
            data: 要更新到数据库的数据字典
        Raises:
            AppError.Exception: 当数据库操作失败时
            AppError.UnknownError: 当发生未知错误时
        """
        try:
            db_operator = DatabaseOperator()
            await db_operator.upsert_data(table_name=TableName.ANIME, data=data, conflict_column="tmdb_id")
            logger.opt(colors=True).info(
                f"<g>{self.source.value}</g>:Anime数据持久化 |<g>SUCCESS</g>")
        except AppError.Exception:
            raise
        except Exception as e:
            AppError.UnknownError.raise_(f"{str(e)}")
