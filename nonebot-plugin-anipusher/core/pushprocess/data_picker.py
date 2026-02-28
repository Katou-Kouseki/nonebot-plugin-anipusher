#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据选择器模块 - 负责从不同数据源提取并格式化推送所需数据
主要功能包括：
- 从不同数据源（如ANIRSS、EMBY）提取信息
- 处理订阅者数据（群组订阅者和私人订阅者）
- 提取媒体信息（标题、集数、评分、类型等）
- 生成图片队列用于消息推送
- 支持合并推送所需的媒体类型和季数字段
"""
import json
from datetime import datetime
from nonebot import logger
from ...mapping import TableName


class DataPicker:
    """
    数据选择器类 - 从多个数据源提取并整合信息
    支持从不同类型的数据源（如ANIRSS、EMBY）中提取信息，并进行标准化处理，
    为消息推送提供统一格式的数据。
    支持合并推送所需的额外字段提取。
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
            "image_queue": self._pick_image_queue(),
            "media_type": self._pick_media_type(),
            "season": self._pick_season(),
            "subgroup": self._pick_subgroup(),
            "progress": self._pick_progress(),
            "premiere": self._pick_premiere(),
            "bgm_url": self._pick_bgmurl(),
            "tmdb_url": self._pick_tmdb_url(),
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
        else:
            return None
        if season is not None and episode is not None:
            try:
                return f"第 {int(season)} 季 | 第 {int(episode)} 集"
            except (ValueError, TypeError):
                return None
        return None

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
        if tmdb_id := self.anime_data.get("tmdb_id", None):
            return tmdb_id
        logger.opt(colors=True).info("<y>PICKER</y>:未提取到数据 <c>TMDB ID</c>")
        return None

    def _pick_media_type(self) -> str | None:
        """
        提取媒体类型
        用于判断是否使用合并推送功能
        Returns:
            str | None: 媒体类型（Movie, Episode, Series），如果无法提取则返回None
        """
        if self.source == TableName.EMBY:
            return self.source_data.get("type")
        elif self.source == TableName.ANIRSS:
            season = self.source_data.get("season")
            episode = self.source_data.get("episode")
            if season and episode:
                return "Episode"
            elif season:
                return "Series"
        return None

    def _pick_season(self) -> str | None:
        """
        提取季数
        用于合并推送时显示季数信息
        Returns:
            str | None: 季数，如果无法提取则返回None
        """
        if self.source == TableName.EMBY:
            type = self.source_data.get('type')
            if type == "Movie":
                return None
            season = self.source_data.get("season")
            if season is not None:
                try:
                    return str(int(season))
                except (ValueError, TypeError):
                    return str(season) if season else None
        elif self.source == TableName.ANIRSS:
            season = self.source_data.get("season")
            if season is not None:
                try:
                    return str(int(season))
                except (ValueError, TypeError):
                    return str(season) if season else None
        return None

    def _pick_subgroup(self) -> str | None:
        if self.source == TableName.ANIRSS:
            return self.source_data.get('subgroup')
        logger.opt(colors=True).debug("<y>PICKER</y>:没有获取到数据subgroup")
        return None

    def _pick_progress(self) -> str | None:
        if self.source == TableName.ANIRSS:
            return self.source_data.get('progress')
        logger.opt(colors=True).debug("<y>PICKER</y>:没有获取到数据progress")
        return None

    def _pick_premiere(self) -> str | None:
        for key in ['premiere', 'PremiereDate']:
             premiere = self.source_data.get(key)
             if premiere and isinstance(premiere, str):
                 if 'T' in premiere: return premiere.split('T')[0]
                 return premiere

        if self.anime_data:
            if premiere := self.anime_data.get("premiere"): return str(premiere)

        logger.opt(colors=True).debug("<y>PICKER</y>:没有获取到数据premiere")
        return None

    def _pick_bgmurl(self) -> str | None:
        if bgm_url := self.source_data.get("bangumi_url"): return bgm_url
        if bgm_url := self.source_data.get("bgmUrl"): return bgm_url
        if self.source == TableName.EMBY:
            external_urls = self.source_data.get('external_urls', [])
            if isinstance(external_urls, list):
                for url_obj in external_urls:
                    if isinstance(url_obj, dict) and (url_obj.get('Name') or url_obj.get('name', '')).lower() == 'bangumi':
                        if url := url_obj.get('Url') or url_obj.get('url'): return url
            provider_ids = self.source_data.get('provider_ids')
            if isinstance(provider_ids, dict):
                 if bangumi_id := provider_ids.get('Bangumi'): return f"https://bgm.tv/subject/{bangumi_id}"

        if self.anime_data:
            if bgm_url := self.anime_data.get("bangumi_url"): return bgm_url

        logger.opt(colors=True).debug("<y>PICKER</y>:没有获取到数据bgmUrl")
        return None

    def _pick_tmdb_url(self) -> str | None:
        tmdb_url = self.source_data.get('tmdb_url') or self.source_data.get('tmdbUrl')
        if tmdb_url and isinstance(tmdb_url, str) and tmdb_url.strip():
            return tmdb_url.strip()
        if self.source == TableName.EMBY:
            external_urls = self.source_data.get('external_urls', [])
            if isinstance(external_urls, list):
                for url_obj in external_urls:
                    if isinstance(url_obj, dict) and (url_obj.get('Name') or url_obj.get('name', '')).lower() == 'themoviedb':
                        if url := url_obj.get('Url') or url_obj.get('url'): return url

        tmdb_id = self._pick_tmdb_id()
        if tmdb_id:
            media_type = self._pick_media_type()
            base = "https://www.themoviedb.org"
            type_path = "tv" if media_type and media_type.lower() != 'movie' else "movie"
            return f"{base}/{type_path}/{tmdb_id}"

        logger.opt(colors=True).debug("<y>PICKER</y>:没有获取到数据tmdbUrl")
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
