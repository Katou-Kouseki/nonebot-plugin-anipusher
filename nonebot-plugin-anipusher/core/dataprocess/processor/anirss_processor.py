#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AniRSS数据处理器模块
该模块负责处理来自AniRSS的webhook数据，提取动画信息并进行格式化，
支持提取标题、评分、集数等信息，以及TMDB和Bangumi相关数据。
"""

# 标准库
import json
import re
# 项目内部模块
from ..abstract_processor import AbstractDataProcessor
from ....database import schema_manager
from ....exceptions import AppError
from ....mapping import TableName
from ....utils import get_iso8601_timestamp


@AbstractDataProcessor.register(TableName.ANIRSS)
class AniRSSProcessor(AbstractDataProcessor):
    """
    AniRSS数据处理器类
    通过装饰器注册到ANIRSS数据源，负责处理AniRSS webhook数据的格式化和提取。
    支持提取动画标题、评分、集数等信息，以及TMDB和Bangumi相关数据。
    """

    async def _reformat(self) -> None:
        """
        重新格式化AniRSS webhook数据
        从原始数据中提取各种动画信息，并将其填充到标准数据结构中。
        Returns:
            bool: 方法实际上不返回值，但通过异常表示处理状态
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
            default_schema = schema_manager.get_default_schema(TableName.ANIRSS)
        except Exception as e:
            raise e
        try:
            extract = self.DataExtraction(self.raw_data)
            send_status = False
            timestamp = extract.extract_timestamp()
            action = extract.extract_action()
            title = extract.extract_title()
            jp_title = extract.extract_jp_title()
            tmdb_title = extract.extract_tmdb_title()
            score = extract.extract_score()
            tmdb_id = extract.extract_tmdb_id()
            tmdb_url = extract.extract_tmdb_url()
            bangumi_url = extract.extract_bgm_url()
            season = extract.extract_season()
            episode = extract.extract_episode()
            tmdb_episode_title = extract.extract_episodeTitle()
            bangumi_episode_title = extract.extract_bgmEpisodeTitle()
            bangumi_jpepisode_title = extract.extract_bgmJpEpisodeTitle()
            subgroup = extract.extract_subgroup()
            progress = extract.extract_progress()
            premiere = extract.extract_premiere()
            download_path = extract.extract_download_path()
            text = extract.extract_text()
            image = extract.extract_image_url()
            raw_data = extract.extract_raw_data()
        except Exception as e:
            AppError.UnknownError.raise_(
                f"提取WEBHOOK数据字段 FAIL —— {e}")
        try:
            default_schema.update({
                "send_status": send_status,
                "timestamp": timestamp,
                "action": action,
                "title": title,
                "jp_title": jp_title,
                "tmdb_title": tmdb_title,
                "score": score,
                "tmdb_id": tmdb_id,
                "tmdb_url": tmdb_url,
                "bangumi_url": bangumi_url,
                "season": season,
                "episode": episode,
                "tmdb_episode_title": tmdb_episode_title,
                "bangumi_episode_title": bangumi_episode_title,
                "bangumi_jpepisode_title": bangumi_jpepisode_title,
                "subgroup": subgroup,
                "progress": progress,
                "premiere": premiere,
                "download_path": download_path,
                "text": text,
                "image_url": image,
                "raw_data": raw_data
            })
            self.structured_data = default_schema
            self.tmdb_id = tmdb_id
        except Exception as e:
            AppError.UnknownError.raise_(f"生成格式化数据 FAIL —— {e}")

    class DataExtraction:
        """
        数据提取辅助类
        负责从AniRSS webhook原始数据中提取各种动画信息字段。
        """
        def __init__(self, data: dict):
            """
            初始化数据提取类
            Args:
                data: AniRSS webhook原始数据字典
            """
            self.data = data

        def extract_timestamp(self) -> str:
            """
            提取时间戳
            Returns:
                str: ISO 8601格式的当前时间戳
            """
            return get_iso8601_timestamp()

        def extract_action(self) -> str | None:
            """
            提取动作类型
            Returns:
                str | None: 动作类型，如果不存在则返回None
            """
            return self.data.get("action")

        def extract_title(self) -> str | None:
            """
            提取动画标题
            去除标题中的TMDB ID标记。
            Returns:
                str | None: 处理后的标题，如果不存在则返回None
            """
            title = self.data.get("title")
            if not title:
                return None
            return re.sub(r'\[tmdbid=\d+\]', '', str(title)).strip()

        def extract_jp_title(self) -> str | None:
            """
            提取日文标题
            Returns:
                str | None: 日文标题，如果不存在则返回None
            """
            return self.data.get("jpTitle")

        def extract_score(self) -> str | None:
            """
            提取评分
            Returns:
                str | None: 评分，如果不存在则返回None
            """
            return self.data.get("score")

        def extract_tmdb_title(self) -> str | None:
            """
            提取TMDB标题
            Returns:
                str | None: TMDB标题，如果不存在则返回None
            """
            return self.data.get("themoviedbName")

        def extract_tmdb_id(self) -> int | None:
            """
            提取TMDB ID
            Returns:
                int | None: TMDB ID，如果不存在则返回None
            """
            return self.data.get("tmdbid")

        def extract_tmdb_url(self) -> str | None:
            """
            提取TMDB链接
            Returns:
                str | None: TMDB链接，如果不存在则返回None
            """
            return self.data.get("tmdbUrl")

        def extract_bgm_url(self) -> str | None:
            """
            提取Bangumi链接
            Returns:
                str | None: Bangumi链接，如果不存在则返回None
            """
            return self.data.get("bgmUrl")

        def extract_season(self) -> str | None:
            """
            提取季度
            Returns:
                str | None: 季度信息，如果不存在则返回None
            """
            return self.data.get("season")

        def extract_episode(self) -> str | None:
            """
            提取集数
            Returns:
                str | None: 集数信息，如果不存在则返回None
            """
            return self.data.get("episode")

        def extract_subgroup(self) -> str | None:
            """
            提取字幕组
            Returns:
                str | None: 字幕组名称，如果不存在则返回None
            """
            return self.data.get("subgroup")

        def extract_progress(self) -> str | None:
            """
            提取进度
            Returns:
                str | None: 观看进度，如果不存在则返回None
            """
            return self.data.get("progress")

        def extract_premiere(self) -> str | None:
            """
            提取首播日期
            Returns:
                str | None: 首播日期，如果不存在则返回None
            """
            return self.data.get("premiere")

        def extract_text(self) -> str | None:
            """
            提取文本内容
            Returns:
                str | None: 文本内容，如果不存在则返回None
            """
            return self.data.get("text")

        def extract_download_path(self) -> str | None:
            """
            提取下载路径
            Returns:
                str | None: 下载路径，如果不存在则返回None
            """
            return self.data.get("downloadPath")

        def extract_episodeTitle(self) -> str | None:
            """
            提取TMDB集标题
            Returns:
                str | None: TMDB剧集标题，如果不存在则返回None
            """
            return self.data.get("episodeTitle")

        def extract_bgmEpisodeTitle(self) -> str | None:
            """
            提取Bangumi集标题
            Returns:
                str | None: Bangumi剧集标题，如果不存在则返回None
            """
            return self.data.get("bgmEpisodeTitle")

        def extract_bgmJpEpisodeTitle(self) -> str | None:
            """
            提取Bangumi日文集标题
            Returns:
                str | None: Bangumi日文剧集标题，如果不存在则返回None
            """
            return self.data.get("bgmJpEpisodeTitle")

        def extract_image_url(self) -> str | None:
            """
            提取图片链接
            Returns:
                str | None: 图片链接，如果不存在则返回None
            """
            return self.data.get("image")

        def extract_raw_data(self) -> str | None:
            """
            提取原始数据
            将原始数据序列化为JSON字符串。
            Returns:
                str | None: JSON格式的原始数据，序列化失败返回None
            """
            return json.dumps(self.data, ensure_ascii=False)

    def _enable_anime_process(self):
        """
        启用Anime数据处理
        返回是否启用Anime数据处理功能。
        Returns:
            bool: 始终返回True，表示启用Anime数据处理
        """
        return True
