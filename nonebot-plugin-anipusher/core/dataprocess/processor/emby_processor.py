#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EMBY数据处理器模块
该模块负责处理来自EMBY媒体服务器的webhook数据，提取媒体信息并进行格式化，
支持电影(Movie)、电视剧(Series)和剧集(Episode)等多种媒体类型的处理，
并提供TMDB ID验证和转换功能。
"""

# 标准库
import asyncio
import json
import re
import aiohttp
from typing import Any, Literal
# 第三方库
from nonebot import logger
# 项目内部模块
from ..abstract_processor import AbstractDataProcessor
from ....config import FUNCTION
from ....database import schema_manager
from ....exceptions import AppError
from ....external import TmdbApiRequest
from ....mapping import TableName
from ....utils import get_iso8601_timestamp


@AbstractDataProcessor.register(TableName.EMBY)
class EmbyDataProcessor(AbstractDataProcessor):
    """
    EMBY数据处理器类
    通过装饰器注册到EMBY数据源，负责处理EMBY webhook数据的格式化和提取。
    支持提取媒体标题、描述、评分、ID等信息，并可进行TMDB ID验证和转换。
    """

    async def _reformat(self):
        """
        重新格式化EMBY webhook数据
        从原始数据中提取各种媒体信息，并将其填充到标准数据结构中。
        支持验证TMDB ID和转换外部ID。
        Raises:
            AppError.MissingParameter: 当缺少必要参数时
            AppError.InvalidParameter: 当参数类型错误时
            AppError.UnknownError: 当发生未知错误时
        """
        try:
            if not self.raw_data:
                AppError.MissingParameter.raise_(
                    "WEBHOOK数据为空，无法进行格式化")
            if not isinstance(self.raw_data, dict):
                AppError.InvalidParameter.raise_(
                    f"WEBHOOK数据格式错误，期望类型：dict，实际类型：{type(self.raw_data)}")
        except Exception as e:
            raise e
        try:
            default_schema = schema_manager.get_default_schema(
                TableName.EMBY).copy()
        except Exception as e:
            raise e
        try:
            extract = self.DataExtraction(self.raw_data)
            send_status = False
            timestamp = extract.extract_timestamp()
            item = extract.extract_item()
            if not item:
                AppError.MissingParameter.raise_(
                    "WEBHOOK数据缺少重要字段 Item 数据处理将被 <r>取消</r>")
            item_type = extract.extract_item_type(item)
            if not item_type:
                AppError.MissingParameter.raise_(
                    "WEBHOOK数据缺少重要字段 Item Type 数据处理将被 <r>取消</r>")
            title = extract.extract_title(item_type, item)
            description = extract.extract_description(item)
            season = extract.extract_season(item_type, item)
            episode = extract.extract_episode(item_type, item)
            episode_title = extract.extract_episode_title(item_type, item)
            genres = extract.extract_genres(item)
            score = extract.extract_score(item_type, item)
            tmdb_id, imdb_id, tvdb_id = await extract.extract_id(item_type, item)
            series_id = extract.extract_series_id(item_type, item)
            episode_id = extract.extract_episode_id(item_type, item)
            series_tag = extract.extract_series_tag(item_type, item)
            episode_tag = extract.extract_episode_tag(item_type, item)
            season_tag = extract.extract_season_tag(item_type, item)
            server_id = extract.extract_server_id()
            server_name = extract.extract_server_name()
            merged_episode = extract.extract_merged_episode(item_type)
            raw_data = extract.extract_raw_data()
        except AppError.Exception as e:
            raise e
        except Exception as e:
            AppError.UnknownError.raise_(
                f"提取WEBHOOK数据字段 FAIL —— {e}")
        try:
            default_schema.update({
                "send_status": send_status,
                "timestamp": timestamp,
                "type": item_type,
                "title": title,
                "description": description,
                "season": season,
                "episode": episode,
                "episode_title": episode_title,
                "genres": genres,
                "score": score,
                "tmdb_id": tmdb_id,
                "imdb_id": imdb_id,
                "tvdb_id": tvdb_id,
                "series_id": series_id,
                "episode_id": episode_id,
                "series_tag": series_tag,
                "episode_tag": episode_tag,
                "season_tag": season_tag,
                "server_id": server_id,
                "server_name": server_name,
                "merged_episode": merged_episode,
                "raw_data": raw_data,
            })
            self.structured_data = default_schema
            self.tmdb_id = tmdb_id
        except Exception as e:
            AppError.UnknownError.raise_(f"生成格式化数据 FAIL —— {e}")

    class DataExtraction:
        """
        数据提取辅助类
        负责从EMBY webhook原始数据中提取各种媒体信息字段。
        """

        def __init__(self, data: dict):
            """
            初始化数据提取类
            Args:
                data: EMBY webhook原始数据字典
            """
            self.data = data

        def extract_timestamp(self) -> str:
            """
            提取时间戳
            Returns:
                str: ISO 8601格式的当前时间戳
            """
            return get_iso8601_timestamp()

        def extract_item(self) -> Any | None:
            """
            提取媒体项目
            Returns:
                Any | None: 媒体项目数据，如果不存在则返回None
            """
            return self.data.get("Item")

        def extract_server(self) -> Any | None:
            """
            提取服务器信息
            Returns:
                Any | None: 服务器信息数据，如果不存在则返回None
            """
            return self.data.get("Server")

        def extract_item_type(self, item) -> Any | None:
            """
            提取媒体类型
            Args:
                item: 媒体项目数据
            Returns:
                Any | None: 媒体类型（Movie、Series、Episode等），提取失败返回None
            Raises:
                AppError.MissingParameter: 当未提供item参数时
            """
            try:
                if not item:
                    AppError.MissingParameter.raise_(
                        "处理extract_item_type FAIL 未提供参数 Item")
                return item.get("Type")
            except Exception as e:
                logger.opt(colors=True).warning(
                    f"<y>EMBY</y>:{e}")
                return None

        def extract_title(self, item_type, item) -> Any | None:
            """
            提取媒体标题
            根据不同的媒体类型提取对应的标题。
            Args:
                item_type: 媒体类型
                item: 媒体项目数据
            Returns:
                Any | None: 媒体标题，提取失败返回None
            Raises:
                AppError.MissingParameter: 当缺少必要参数时
            """
            try:
                if not item:
                    AppError.MissingParameter.raise_(
                        "处理extract_title FAIL 未提供参数 Item")
                if not item_type:
                    AppError.MissingParameter.raise_(
                        "处理extract_title FAIL 未提供参数 Item Type")
                if item_type == "Series":
                    return item.get("Name")
                elif item_type == "Episode":
                    return item.get("SeriesName")
                elif item_type == "Movie":
                    return item.get("Name")
                else:
                    return None
            except Exception as e:
                logger.opt(colors=True).warning(
                    f"<y>EMBY</y>:{e}")
                return None

        def extract_description(self, item) -> Any | None:
            """
            提取媒体描述
            Args:
                item: 媒体项目数据
            Returns:
                Any | None: 媒体概述或描述，提取失败返回None
            Raises:
                AppError.MissingParameter: 当未提供item参数时
            """
            try:
                if not item:
                    AppError.MissingParameter.raise_(
                        "处理extract_description FAIL 未提供参数 Item")
                return item.get("Overview")
            except Exception as e:
                logger.opt(colors=True).warning(
                    f"<y>EMBY</y>:{e}")
                return None

        def extract_season(self, item_type, item) -> Any | None:
            """
            提取季数
            Args:
                item_type: 媒体类型
                item: 媒体项目数据
            Returns:
                Any | None: 季数，非剧集类型返回None，提取失败返回None
            Raises:
                AppError.MissingParameter: 当缺少必要参数时
            """
            try:
                if not item:
                    AppError.MissingParameter.raise_(
                        "处理extract_season FAIL 未提供参数 Item")
                if not item_type:
                    AppError.MissingParameter.raise_(
                        "处理extract_season FAIL 未提供参数 Item Type")
                if item_type == "Episode":
                    return item.get("ParentIndexNumber")
                else:
                    return None
            except Exception as e:
                logger.opt(colors=True).warning(
                    f"<y>EMBY</y>:{e}")
                return None

        def extract_episode(self, item_type, item) -> Any | None:
            """
            提取集数
            Args:
                item_type: 媒体类型
                item: 媒体项目数据
            Returns:
                Any | None: 集数，非剧集类型返回None，提取失败返回None
            Raises:
                AppError.MissingParameter: 当缺少必要参数时
            """
            try:
                if not item:
                    AppError.MissingParameter.raise_(
                        "处理extract_episode FAIL 未提供参数 Item")
                if not item_type:
                    AppError.MissingParameter.raise_(
                        "处理extract_episode FAIL 未提供参数 Item Type")
                if item_type == "Episode":
                    return item.get("IndexNumber")
                else:
                    return None
            except Exception as e:
                logger.opt(colors=True).warning(
                    f"<y>EMBY</y>:{e}")
                return None

        def extract_episode_title(self, item_type, item) -> Any | None:
            """
            提取剧集标题
            Args:
                item_type: 媒体类型
                item: 媒体项目数据
            Returns:
                Any | None: 剧集标题，非剧集类型返回None，提取失败返回None
            Raises:
                AppError.MissingParameter: 当缺少必要参数时
            """
            try:
                if not item:
                    AppError.MissingParameter.raise_(
                        "处理extract_episode_title FAIL 未提供参数 Item")
                if not item_type:
                    AppError.MissingParameter.raise_(
                        "处理extract_episode_title FAIL 未提供参数 Item Type")
                if item_type == "Episode":
                    return item.get("Name")
                else:
                    return None
            except Exception as e:
                logger.opt(colors=True).warning(
                    f"<y>EMBY</y>:{e}")
                return None

        def extract_genres(self, item) -> Any | None:
            """
            提取流派
            将媒体的流派信息提取并格式化为|分隔的字符串。
            Args:
                item: 媒体项目数据
            Returns:
                Any | None: 流派字符串，提取失败返回None
            Raises:
                AppError.MissingParameter: 当未提供item参数时
            """
            try:
                if not item:
                    AppError.MissingParameter.raise_(
                        "处理extract_genres FAIL 未提供参数 Item")
                genres = item.get("Genres", [])
                return "|".join(genres) if genres else None
            except Exception as e:
                logger.opt(colors=True).warning(
                    f"<y>EMBY</y>:{e}")
                return None

        def extract_score(self, item_type, item) -> Any | None:
            """
            提取评分
            Args:
                item_type: 媒体类型
                item: 媒体项目数据
            Returns:
                Any | None: 社区评分，非剧集类型返回None，提取失败返回None
            Raises:
                AppError.MissingParameter: 当缺少必要参数时
            """
            try:
                if not item:
                    AppError.MissingParameter.raise_(
                        "处理extract_score FAIL 未提供参数 Item")
                if not item_type:
                    AppError.MissingParameter.raise_(
                        "处理extract_score FAIL 未提供参数 Item Type")
                if item_type == "Series":
                    return item.get("CommunityRating")
                else:
                    return None
            except Exception as e:
                logger.opt(colors=True).warning(
                    f"<y>EMBY</y>:{e}")
                return None

        async def extract_id(self, item_type, item):
            """
            提取媒体ID
            提取并验证TMDB ID，如果TMDB ID无效或不存在，尝试将IMDB或TVDB ID转换为TMDB ID。
            Args:
                item_type: 媒体类型
                item: 媒体项目数据
            Returns:
                tuple: (tmdb_id, imdb_id, tvdb_id)，提取失败时对应值为None
            Raises:
                AppError.MissingParameter: 当缺少必要参数时
            """
            try:
                if not item:
                    AppError.MissingParameter.raise_(
                        "处理extract_id FAIL 未提供参数 Item")
                if not item_type:
                    AppError.MissingParameter.raise_(
                        "处理extract_id FAIL 未提供参数 Item Type")
                provider_ids = item.get("ProviderIds", {})
                imdb_id = provider_ids.get("Imdb")
                tmdb_id = provider_ids.get("Tmdb")
                tvdb_id = provider_ids.get("Tvdb")
            except Exception as e:
                logger.opt(colors=True).warning(
                    f"<y>EMBY</y>:{e}")
                return None, None, None
            if FUNCTION.tmdb_enabled is False:
                logger.opt(colors=True).warning(
                    "<y>TMDB</y>:功能 <y>未启用</y> —— 无法验证 TMDB ID，已置空TMDB ID")
                tmdb_id = None
                return tmdb_id, imdb_id, tvdb_id
            try:
                if tmdb_id:
                    if await self._verify_id_from_response(tmdb_id, item_type):
                        logger.opt(colors=True).info(
                            f"<g>TMDB</g>:验证TMDB ID <g>SUCCESS</g> —— TMDB ID:<b>{tmdb_id}</b>")
                        return tmdb_id, imdb_id, tvdb_id
                    else:
                        logger.opt(colors=True).warning(
                            f"<y>TMDB</y>:无效的TMDB ID: <c>{tmdb_id}</c> —— 对应页面不存在")
                        tmdb_id = None
            except Exception as e:
                logger.opt(colors=True).error(
                    f"<r>TMDB</r>:{e}")
                tmdb_id = None
                return tmdb_id, imdb_id, tvdb_id
            tasks = [
                self._convert_external_id_to_tmdb(imdb_id, "imdb_id"),
                self._convert_external_id_to_tmdb(tvdb_id, "tvdb_id")
            ]
            tasks_result = await asyncio.gather(*tasks, return_exceptions=True)
            for result in tasks_result:
                if result is not None and not isinstance(result, Exception):
                    logger.opt(colors=True).info(
                        f"<g>TMDB</g>:第三方 ID ——> TMDB ID 转换 <g>SUCCESS</g> TMDB ID: <c>{result}</c>")
                    return result, imdb_id, tvdb_id

            logger.opt(colors=True).warning(
                "<y>TMDB</y>:第三方 ID ——> TMDB ID 转换 <r>FAIL</r>，已置空TMDB ID")
            return None, imdb_id, tvdb_id

        def extract_series_id(self, item_type, item) -> Any | None:
            """
            提取系列ID
            根据不同的媒体类型提取对应的系列ID。
            Args:
                item_type: 媒体类型
                item: 媒体项目数据
            Returns:
                Any | None: 系列ID，提取失败返回None
            Raises:
                AppError.MissingParameter: 当缺少必要参数时
            """
            try:
                if not item:
                    AppError.MissingParameter.raise_(
                        "处理extract_series_id FAIL 未提供参数 Item")
                if not item_type:
                    AppError.MissingParameter.raise_(
                        "处理extract_series_id FAIL 未提供参数 Item Type")
                if item_type == "Series":
                    return item.get("Id")
                elif item_type == "Episode":
                    return item.get("SeriesId")
                elif item_type == "Movie":
                    return item.get("Id")
                else:
                    return None
            except Exception as e:
                logger.opt(colors=True).warning(
                    f"<y>EMBY</y>:{e}")
                return None

        def extract_season_id(self, item_type, item) -> Any | None:
            """
            提取季ID
            Args:
                item_type: 媒体类型
                item: 媒体项目数据
            Returns:
                Any | None: 季ID，提取失败返回None
            Raises:
                AppError.MissingParameter: 当缺少必要参数时
            """
            try:
                if not item:
                    AppError.MissingParameter.raise_(
                        "处理extract_season_id FAIL 未提供参数 Item")
                if not item_type:
                    AppError.MissingParameter.raise_(
                        "处理extract_season_id FAIL 未提供参数 Item Type")
                if item_type == "Episode":
                    return item.get("ParentId")
                elif item_type == "Series":
                    return item.get("Id")
                else:
                    return None
            except Exception as e:
                logger.opt(colors=True).warning(
                    f"<y>EMBY</y>:{e}")
                return None

        def extract_episode_id(self, item_type, item) -> Any | None:
            """
            提取剧集ID
            Args:
                item_type: 媒体类型
                item: 媒体项目数据
            Returns:
                Any | None: 剧集ID，非剧集类型返回None，提取失败返回None
            Raises:
                AppError.MissingParameter: 当缺少必要参数时
            """
            try:
                if not item:
                    AppError.MissingParameter.raise_(
                        "处理extract_episode_id FAIL 未提供参数 Item")
                if not item_type:
                    AppError.MissingParameter.raise_(
                        "处理extract_episode_id FAIL 未提供参数 Item Type")
                if item_type == "Episode":
                    return item.get("Id")
                else:
                    return None
            except Exception as e:
                logger.opt(colors=True).warning(
                    f"<y>EMBY</y>:{e}")
                return None

        def extract_series_tag(self, item_type, item) -> Any | None:
            """
            提取系列图片标签
            获取用于构建图片URL的标签。
            Args:
                item_type: 媒体类型
                item: 媒体项目数据
            Returns:
                Any | None: 图片标签，提取失败返回None
            Raises:
                AppError.MissingParameter: 当缺少必要参数时
            """
            try:
                if not item:
                    AppError.MissingParameter.raise_(
                        "处理extract_series_tag FAIL 未提供参数 Item")
                if not item_type:
                    AppError.MissingParameter.raise_(
                        "处理extract_series_tag FAIL 未提供参数 Item Type")
                if item_type == "Series":
                    return (item.get('ImageTags') or {}).get("Primary")
                elif item_type == "Episode":
                    return item.get("SeriesPrimaryImageTag")
                elif item_type == "Movie":
                    return (item.get('ImageTags') or {}).get("Primary")
                else:
                    return None
            except Exception as e:
                logger.opt(colors=True).warning(
                    f"<y>EMBY</y>:{e}")
                return None

        def extract_season_tag(self, item_type, item) -> None:
            """
            提取季图片标签
            预留方法，目前始终返回None。
            Args:
                item_type: 媒体类型
                item: 媒体项目数据
            Returns:
                None: 始终返回None
            """
            return None

        def extract_episode_tag(self, item_type, item) -> None:
            """
            提取剧集图片标签
            Args:
                item_type: 媒体类型
                item: 媒体项目数据
            Returns:
                Any | None: 剧集图片标签，非剧集类型返回None，提取失败返回None
            Raises:
                AppError.MissingParameter: 当缺少必要参数时
            """
            try:
                if not item:
                    AppError.MissingParameter.raise_(
                        "处理extract_episode_tag FAIL 未提供参数 Item")
                if not item_type:
                    AppError.MissingParameter.raise_(
                        "处理extract_episode_tag FAIL 未提供参数 Item Type")
                if item_type == "Series":
                    return None
                elif item_type == "Episode":
                    return (item.get('ImageTags') or {}).get("Primary")
                elif item_type == "Movie":
                    return None
                else:
                    return None
            except Exception as e:
                logger.opt(colors=True).warning(
                    f"<y>EMBY</y>:{e}")
                return None

        def extract_server_id(self) -> str | None:
            """
            提取服务器ID
            Returns:
                str | None: 服务器ID，提取失败返回None
            Raises:
                AppError.MissingParameter: 当未获取到Server参数时
            """
            try:
                server = self.data.get("Server")
                if not server:
                    AppError.MissingParameter.raise_(
                        "处理extract_server_id FAIL 未获取到参数 Server")
                return server.get("Id")
            except Exception as e:
                logger.opt(colors=True).warning(
                    f"<y>EMBY</y>:{e}")
                return None

        def extract_server_name(self) -> str | None:
            """
            提取服务器名称
            Returns:
                str | None: 服务器名称，提取失败返回None
            Raises:
                AppError.MissingParameter: 当未获取到Server参数时
            """
            try:
                server = self.data.get("Server")
                if not server:
                    AppError.MissingParameter.raise_(
                        "处理extract_server_name FAIL 未获取到参数 Server")
                return server.get("Name")
            except Exception as e:
                logger.opt(colors=True).warning(
                    f"<y>EMBY</y>:{e}")
                return None

        def extract_merged_episode(self, item_type) -> int | None:
            """
            提取合并推送集数
            从标题中提取批量添加的剧集数量。
            Args:
                item_type: 媒体类型
            Returns:
                int | None: 合并推送的集数，非Series类型返回None，提取失败返回None
            Raises:
                AppError.MissingParameter: 当缺少必要参数时
            """
            try:
                if not item_type:
                    AppError.MissingParameter.raise_(
                        "处理merged_episode FAIL 未提供参数 Item Type")
                if item_type == "Series":
                    webhook_title = self.data.get("Title")
                    if not webhook_title:
                        AppError.MissingParameter.raise_(
                            "处理merged_episode FAIL 未获取到参数 Title")
                    match = re.search(r'已添加了\s*(\d+)\s*项', webhook_title)
                    if match:
                        return int(match.group(1))
                    else:
                        logger.opt(colors=True).warning(
                            "<y>EMBY</y>:提取合并推送集数 <r>FAIL</r>")
                        return None
                else:
                    return None
            except Exception as e:
                logger.opt(colors=True).warning(
                    f"<y>EMBY</y>:{e}")
                return None

        def extract_raw_data(self) -> str | None:
            """
            提取原始数据
            将原始数据序列化为JSON字符串。
            Returns:
                str | None: JSON格式的原始数据，序列化失败返回None
            """
            try:
                return json.dumps(self.data, ensure_ascii=False)
            except Exception as e:
                logger.opt(colors=True).warning(
                    f"<y>EMBY</y>:{e}")
                return None

        async def _verify_id_from_response(self, tmdb_id: str, type: Literal["Movie", "Episode", "Series"]) -> bool:
            """
            验证TMDB ID是否存在
            通过TMDB API验证提供的ID是否有效。
            Args:
                tmdb_id: TMDB ID
                type: 媒体类型
            Returns:
                bool: ID是否有效
            Raises:
                AppError.UnknownError: 当验证过程中发生未知错误时
            """
            try:
                response = await TmdbApiRequest.get_id_details(tmdb_id, type)
                if not response:
                    logger.opt(colors=True).warning(
                        "<y>TMDB</y>: TMDB API 响应返回空值，请检查！")
                    return False
                if response.get("status_code") == 34 or response.get("success") is False:
                    return False
                return True
            except AppError.Exception as e:
                logger.opt(colors=True).warning(
                    f"<y>TMDB</y>:TMDB API 验证 ID {tmdb_id} <r>FAIL</r> —— {e}")
                return False
            except aiohttp.ClientError:
                return False
            except Exception as e:
                AppError.UnknownError.raise_(f"TMDB ID 验证失败 —— {e}")

        async def _convert_external_id_to_tmdb(self, external_id: str | None, source: str) -> str | None:
            """
            将外部ID转换为TMDB ID
            使用TMDB API将IMDB、TVDB等外部ID转换为TMDB ID。
            Args:
                external_id: 外部ID
                source: ID来源（如"imdb_id"、"tvdb_id"）
            Returns:
                str | None: 转换后的TMDB ID，转换失败返回None
            Raises:
                AppError.MissingParameter: 当未提供source参数时
            """
            if not source:
                AppError.MissingParameter.raise_(
                    "转换外部ID为TMDB ID时未提供参数 source")
            if not external_id:
                return None
            try:
                response = await TmdbApiRequest.find_by_external_id(
                    external_id, source)
                if not response:
                    logger.opt(colors=True).warning(
                        f"<y>TMDB</y>:外部ID {external_id} 转换为TMDB ID 失败，响应返回空值 请检查！")
                    return None
                for type, items in response.items():
                    if not items:
                        continue
                    # 获取第一个结果
                    item = items[0]
                    # 如果是剧集季或剧集，返回 show_id
                    if type in ["tv_season_results", "tv_episode_results"]:
                        return item.get("show_id")
                    # 如果是电影或剧集，返回 id
                    elif type in ["movie_results", "tv_results"]:
                        return item.get("id")
                return None
            except Exception as e:
                logger.opt(colors=True).warning(
                    f"<y>TMDB</y>:外部ID {external_id} ——> TMDB ID 转换时发生未知异常 —— {e}")
                return None

    def _enable_anime_process(self):
        """
        启用Anime数据处理
        返回是否启用Anime数据处理功能。
        Returns:
            bool: 始终返回True，表示启用Anime数据处理
        """
        return True
