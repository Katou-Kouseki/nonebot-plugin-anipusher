#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据选择器模块 - 负责从不同数据源提取并格式化推送所需数据
主要功能包括：
- 从不同数据源（如ANIRSS、EMBY）提取信息
- 处理订阅者数据（群组订阅者和私人订阅者）
- 提取媒体信息（标题、集数、评分、类型等）
- 生成图片队列用于消息推送
"""
# 标准库
import json
from datetime import datetime
# 第三方库
from nonebot import logger
# 项目内部模块
from ...mapping import TableName


class DataPicker:
    """
    数据选择器类 - 从多个数据源提取并整合信息
    支持从不同类型的数据源（如ANIRSS、EMBY）中提取信息，并进行标准化处理，
    为消息推送提供统一格式的数据。
    """

    def __init__(self,
                 source: TableName,
                 source_data: dict,
                 anime_data: dict) -> None:
        """
        初始化数据选择器
        Args:
            source: 数据源类型，来自TableName枚举
            source_data: 源数据字典
            anime_data: 动漫数据字典
        """
        self.source = source
        self.source_data = source_data
        self.anime_data = anime_data

    def pick(self) -> dict:
        """
        提取并整合所有需要的数据
        Returns:
            dict: 包含所有提取数据的字典，包括ID、标题、集数、时间戳等信息
        """
        group_subscriber, private_subscriber = self._pick_subscriber()
        return {
            "id": self._pick_id(),
            "title": self._pick_title(),
            "episode": self._pick_episode(),
            "episode_title": self._pick_episode_title(),
            "timestamp": self._pick_timestamp(),
            "source": self._pick_source(),
            "action": self._pick_action(),
            "score": self._pick_score(),
            "genres": self._pick_genres(),
            "tmdb_id": self._pick_tmdb_id(),
            "group_subscribers": group_subscriber,
            "private_subscribers": private_subscriber,
            "image_queue": self._pick_image_queue()
        }

    def _pick_id(self) -> int | None:
        """
        提取媒体ID
        Returns:
            int | None: 媒体ID，如果无法提取则返回None
        """
        if self.source in (TableName.ANIRSS, TableName.EMBY):
            if id := self.source_data.get("id"):
                return int(id)
        logger.opt(colors=True).info("<y>PICKER</y>:未提取到未发送数据的ID <y>将导致发送状态切换失败</y>")
        return None

    def _pick_title(self) -> str | None:
        """
        提取媒体标题
        优先级：源数据标题 -> anime_data中的emby_title -> anime_data中的tmdb_title
        Returns:
            str | None: 媒体标题，如果无法提取则返回None
        """
        if self.source in (TableName.ANIRSS, TableName.EMBY):
            if title := self.source_data.get("title"):
                return str(title)
        if self.anime_data:
            return self.anime_data.get("emby_title") or self.anime_data.get("tmdb_title")
        else:
            logger.opt(colors=True).info("<y>PICKER</y>:未提取到数据 <c>Title</c>")
            return None

    def _pick_episode(self) -> str | None:
        """
        提取集数信息
        支持不同格式的集数表示，根据数据源类型进行相应处理。
        对于ANIRSS返回SxxExx格式，对于EMBY根据媒体类型返回不同格式。
        Returns:
            str | None: 集数信息，如果无法提取或为电影则返回None
        """
        if self.source == TableName.ANIRSS:
            season = self.source_data.get("season")
            episode = self.source_data.get("episode")
        elif self.source == TableName.EMBY:
            type = self.source_data.get('type')
            if not type:
                logger.opt(colors=True).info(f"<y>PICKER</y>:未提取到 <c>episode</c> 信息 —— {self.source_data}源数据中缺少 type 字段")
                return None
            elif type == "Movie":
                return None
            elif type == "Series":
                merged_episode = self.source_data.get("merged_episode")
                if merged_episode:
                    return f"合计 {merged_episode} 集更新"
                else:
                    logger.opt(colors=True).info(f"<y>PICKER</y>:未提取到 <c>episode</c> 信息 —— {self.source_data}源数据中类型为 Series 但缺少 merged_episode 字段")
                    return None
            elif type == "Episode":
                season = self.source_data.get("season")
                episode = self.source_data.get("episode")
                if not all([
                        season is not None,
                        episode is not None,
                        str(season).isdigit(),
                        str(episode).isdigit()]):
                    logger.opt(colors=True).info(f"<y>PICKER</y>:无效的 <c>episode</c> 信息 —— Season:{season} 或 Episode:{episode} 字段无效")
                    return None
            else:
                logger.opt(colors=True).info(f"<y>PICKER</y>:未知的类型 —— {type}")
                return None
        # 该断言仅为避免IDE静态类型检查失败
        assert season is not None and episode is not None
        return f"S{int(season):02d}E{int(episode):02d}"

    def _pick_episode_title(self) -> str | None:
        """
        提取剧集标题
        对于ANIRSS，优先级：tmdb_episode_title -> bangumi_episode_title -> bangumi_jpepisode_title
        对于EMBY，直接从源数据获取episode_title

        Returns:
            str | None: 剧集标题，如果无法提取则返回None
        """
        if self.source == TableName.ANIRSS:
            episode_title = (
                self.source_data.get('tmdb_episode_title')
                or self.source_data.get('bangumi_episode_title')
                or self.source_data.get('bangumi_jpepisode_title')
            )
            return episode_title
        elif self.source == TableName.EMBY:
            return self.source_data.get("episode_title")
        else:
            logger.opt(colors=True).info("<y>PICKER</y>:未提取到数据 <c>Episode Title</c>")
            return None

    def _pick_timestamp(self) -> str | None:
        """
        提取并格式化时间戳
        将ISO格式的时间戳转换为友好的显示格式
        Returns:
            str | None: 格式化的时间戳字符串，如果无法提取则返回None
        """
        if self.source in (TableName.ANIRSS, TableName.EMBY):
            if timestamp := self.source_data.get("timestamp"):
                return datetime.fromisoformat(timestamp).strftime('%m-%d %H:%M:%S')
            logger.opt(colors=True).info("<y>PICKER</y>:未提取到数据 <c>Timestamp</c>")
            return None
        else:
            return None

    def _pick_source(self) -> str:
        """
        提取数据源名称
        Returns:
            str: 数据源的字符串表示
        """
        return self.source.value

    def _pick_action(self) -> str | None:
        """
        提取操作类型
        Returns:
            str | None: 操作类型描述，如果无法提取则返回None
        """
        if self.source == TableName.ANIRSS:
            return self.source_data.get("action")
        elif self.source == TableName.EMBY:
            return "媒体更新已完成"
        else:
            return None

    def _pick_score(self) -> str | None:
        """
        提取评分信息
        优先级：源数据score -> anime_data中的score
        Returns:
            str | None: 评分信息，如果无法提取则返回None
        """
        if self.source in (TableName.ANIRSS, TableName.EMBY):
            if score := self.source_data.get("score", None):
                return score
        # 如果没有score则尝试降级从Anime数据库获取score
        if score := self.anime_data.get("score", None):
            return score
        logger.opt(colors=True).info("<y>PICKER</y>:未提取到数据 <c>Score</c>")
        return None

    def _pick_genres(self) -> str | None:
        """
        提取类型信息
        优先级：EMBY源数据genres -> anime_data中的genres
        Returns:
            str | None: 类型信息，如果无法提取则返回None
        """
        if self.source == TableName.EMBY:
            if genres := self.source_data.get("genres", None):
                return genres
        elif self.source == TableName.ANIRSS:
            pass
        # 如果没有genres则尝试降级从Anime数据库获取genres
        if genres := self.anime_data.get("genres", None):
            return genres
        logger.opt(colors=True).info("<y>PICKER</y>:未提取到数据 <c>Genres</c>")
        return None

    def _pick_tmdb_id(self) -> str | None:
        """
        提取TMDB ID
        优先级：源数据tmdb_id -> anime_data中的tmdb_id
        Returns:
            str | None: TMDB ID，如果无法提取则返回None
        """
        if self.source in (TableName.ANIRSS, TableName.EMBY):
            if tmdb_id := self.source_data.get("tmdb_id", None):
                return tmdb_id
        # 如果没有tmdb_id则尝试降级从Anime数据库获取tmdb_id
        if tmdb_id := self.anime_data.get("tmdb_id", None):
            return tmdb_id
        logger.opt(colors=True).info("<y>PICKER</y>:未提取到数据 <c>TMDB ID</c>")
        return None

    def _pick_subscriber(self) -> tuple[dict[str, list[str]], list[str]]:
        """
        获取订阅者数据
        从Anime数据库中提取订阅者信息，包括群组订阅者和私人订阅者。
        Returns:
            tuple[dict[str, list[str]], list[str]]:
                - 第一个元素：群组订阅者字典，格式为{'group_id': [user_id, user_id, ...]}
                - 第二个元素：私人订阅者列表，格式为[user_id, user_id, ...]
        """
        if not self.anime_data:
            logger.opt(colors=True).warning("<y>PICKER</y>:无Anime数据库数据 无法获取订阅者")
            return {}, []
        try:
            def _parse_config_field(field_name, expected_type, default_value):
                raw_data = self.anime_data.get(field_name, default_value)
                if raw_data is None:
                    return default_value
                # 如果是字符串，尝试JSON解析
                    # 如果已经是期望的类型，直接返回
                if isinstance(raw_data, expected_type):
                    return raw_data
                if isinstance(raw_data, str):
                    try:
                        parsed = json.loads(raw_data)
                        if isinstance(parsed, expected_type):
                            return parsed
                        logger.opt(colors=True).error(f"<r>PICKER</r>:解析 {field_name} <r>失败</r> 应为 {expected_type.__name__} 实际为 {type(parsed).__name__} 回退至默认值")
                        return default_value
                    except json.JSONDecodeError as e:
                        logger.opt(colors=True).error(f"<r>PICKER</r>:解析 {field_name} 失败 回退至默认值 —— {e}")
                        return default_value
                logger.opt(colors=True).error(f"<r>PICKER</r>:字段 {field_name} 类型 <r>错误</r> 应为 {expected_type.__name__} 实际为 {type(raw_data).__name__} 回退至默认值")
                return default_value
            # 获取订阅者数据
            group_subscriber = _parse_config_field('group_subscriber', dict, {})
            private_subscriber = _parse_config_field('private_subscriber', list, [])
            return group_subscriber, private_subscriber
        except Exception as e:
            logger.opt(colors=True).error(f"<r>PICKER</r>:获取订阅者数据 <r>失败</r> —— {e}")
            return {}, []

    def _pick_image_queue(self) -> list:
        """
        生成图片URL队列
        从不同来源收集图片URL，包括EMBY、ANIRSS和anime_data，并去重。
        Returns:
            list: 去重后的图片URL列表
        """
        from ...utils import generate_emby_image_url
        from ...config import APPCONFIG
        image_list = []
        try:
            if self.source == TableName.EMBY:
                tag = self.source_data.get("series_tag", None)
                series_id = self.source_data.get("series_id", None)
                try:
                    image_list.append(generate_emby_image_url(APPCONFIG.emby_host, series_id, tag))
                except Exception as e:
                    logger.opt(colors=True).error(f"<r>PICKER</r>:生成EMBY图片链接 <r>失败</r> —— {str(e)}")
            elif self.source == TableName.ANIRSS:
                if image := self.source_data.get("image_url", None):
                    image_list.append(image)
            if self.anime_data:
                image_list.append(self.anime_data.get("emby_image_url", None))
                image_list.append(self.anime_data.get("ainrss_image_url", None))
            return list(dict.fromkeys(filter(None, image_list)))
        except Exception as e:
            logger.opt(colors=True).error(f"<r>PICKER</r>:获取图片队列 <r>失败</r> —— {str(e)}")
            return []
