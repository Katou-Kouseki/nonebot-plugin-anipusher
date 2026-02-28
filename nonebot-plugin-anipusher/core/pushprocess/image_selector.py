#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
图片选择器模块 - 负责图片缓存管理与选择
主要功能包括：
- 从本地缓存中搜索图片
- 刷新图片缓存
- 图片有效性验证
- 提供降级策略（过期图片或默认图片）
- 支持Emby图片标签处理
- 原子化文件写入操作
"""
import asyncio
import shutil
import aiohttp
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any
from nonebot import logger
from ...config import WORKDIR, APPCONFIG, FUNCTION
from ...external import get_request
from ...exceptions import AppError


class ImageSelector:
    """
    图片选择器类 - 负责从本地缓存或网络获取图片并提供降级策略
    支持多种图片来源，包括本地缓存和网络下载，并提供完整的降级机制，
    确保在各种情况下都能提供可用的图片资源。
    支持Emby图片标签处理和更健壮的缓存管理。
    """

    def __init__(self,
                 image_queue: list,
                 tmdb_id: str | None,
                 source_data: Dict[str, Any] | None = None,
                 emby_series_id: str | None = None) -> None:
        """
        初始化图片选择器
        Args:
            image_queue: 图片URL队列或标签队列
            tmdb_id: 媒体内容的TMDB ID，用于标识和缓存图片
            source_data: 源数据字典，用于处理Emby图片标签
            emby_series_id: Emby系列ID
        """
        self.image_queue = image_queue
        self.tmdb_id = tmdb_id
        self.source_data = source_data
        self.emby_series_id = emby_series_id
        self.is_image_expired = False
        self.output_img: Path | None = None

    async def select(self) -> Path | None:
        """
        选择并返回合适的图片路径
        优先级：有效本地缓存 -> 新下载图片 -> 过期缓存 -> 默认图片
        Returns:
            Path | None: 图片文件路径，当所有降级策略都失败时返回None
        """
        self.output_img = self._search_in_localstore()
        if self.output_img and not self.is_image_expired:
            logger.opt(colors=True).info(
                '<g>PUSHER</g>:发现可用的本地图片')
            return self.output_img
        if self.output_img and self.is_image_expired:
            logger.opt(colors=True).info(
                '<y>PUSHER</y>:本地图片已过期，尝试获取新图片')
        result = await self._process_image_queue()
        if result:
            return result
        return self._fallback_to_available_image()

    def _get_cache_path(self) -> Path | None:
        """生成缓存路径"""
        cache_key = None
        current_tmdb_id = self.tmdb_id
        current_series_id = self.emby_series_id
        if current_tmdb_id and current_tmdb_id != 'None':
            cache_key = f"{current_tmdb_id}"
        elif current_series_id:
            cache_key = f"emby_{current_series_id}"
        if cache_key and WORKDIR.cache_dir:
            return WORKDIR.cache_dir / f"{cache_key}.png"
        logger.opt(colors=True).error("<r>Image</r>:无法生成缓存路径，关键ID缺失！")
        return None

    async def _process_image_queue(self) -> Path | None:
        """处理图片队列"""
        if not self.image_queue:
            return None
        cleaned_urls = self._clean_image_queue()
        if not cleaned_urls:
            return None
        image_data = await self._download_first_valid_image(cleaned_urls)
        if not image_data:
            return None
        img_path = await self._save_bytes_to_cache(image_data)
        if img_path:
            self.output_img = img_path
            logger.opt(colors=True).info('<g>PUSHER</g>:刷新图片缓存 <g>完成</g>')
            return img_path
        return None

    def _search_in_localstore(self) -> Path | None:
        """在本地缓存中搜索图片"""
        local_img_path = self._get_cache_path()
        if not local_img_path:
            return None
        try:
            if not local_img_path.exists():
                logger.opt(colors=True).info("<y>PUSHER</y>:本地图片不存在")
                return None
            try:
                if self._is_cache_img_expired(local_img_path):
                    self.is_image_expired = True
            except Exception as check_e:
                logger.opt(colors=True).warning(
                    f"<y>PUSHER</y>:检查图片是否过期时出错：{check_e}，视为已过期")
                self.is_image_expired = True
            return local_img_path
        except Exception as e:
            logger.opt(colors=True).warning(
                f"<y>PUSHER</y>:获取本地图片失败：{e}")
            return None

    def _clean_image_queue(self) -> Dict[str, str]:
        """清理图片队列，处理Emby图片标签"""
        url_dict = {}
        if not self.source_data:
            for tag_or_url in self.image_queue:
                if self._is_url(str(tag_or_url)):
                    if tag_or_url not in url_dict:
                        url_dict[tag_or_url] = "EXTERNAL"
            return url_dict
        series_id = self.source_data.get('series_id')
        for tag_or_url in self.image_queue:
            if self._is_url(str(tag_or_url)):
                if tag_or_url not in url_dict:
                    url_dict[tag_or_url] = "EXTERNAL"
            elif FUNCTION.emby_enabled:
                if series_id:
                    try:
                        from ...utils import generate_emby_image_url
                        url = generate_emby_image_url(
                            APPCONFIG.emby_host, str(series_id), str(tag_or_url))
                        if url not in url_dict:
                            url_dict[url] = "EMBY"
                            logger.opt(colors=True).debug(
                                f"<g>Image</g>:使用 Series ID ({series_id}) 拼接 Emby 图片 URL 成功")
                    except Exception as e:
                        logger.opt(colors=True).warning(
                            f"<y>PUSHER</y>:使用 Series ID 拼接 Emby 图片 URL 失败：{e}")
                else:
                    logger.opt(colors=True).warning(
                        "<y>Image</y>:缺少 Series ID，无法为 Emby 标签生成 URL")
        return url_dict

    def _is_url(self, item: str) -> bool:
        """检查是否为有效URL"""
        if not isinstance(item, str):
            return False
        try:
            from urllib.parse import urlparse
            result = urlparse(item)
            return result.scheme in ['http', 'https'] and bool(result.netloc)
        except Exception:
            return False

    async def _download_first_valid_image(self, url_dict: dict) -> bytes | None:
        """下载第一个有效图片"""
        tasks, errors = [], []
        for url, source in url_dict.items():
            try:
                headers = {"User-Agent": "AriadusTTT/nonebot_plugin_AniPush/1.0.0 (Python)"}
                proxy = None
                if source == "EMBY":
                    headers["X-Emby-Token"] = APPCONFIG.emby_key
                    proxy = APPCONFIG.proxy
                task = asyncio.create_task(
                    get_request(
                        url,
                        headers=headers,
                        proxy=proxy,
                        is_binary=True,
                        timeout=aiohttp.ClientTimeout(total=15, connect=5, sock_read=5)
                    )
                )
                tasks.append(task)
            except Exception as e:
                logger.opt(colors=True).warning(
                    f"<y>PUSHER</y>:{url} 下载任务创建失败，{e}")
        if not tasks:
            return None
        for task in asyncio.as_completed(tasks):
            try:
                binary = await task
                for t in tasks:
                    if not t.done():
                        t.cancel()
                return binary
            except Exception as e:
                errors.append(e)
        if errors:
            logger.opt(colors=True).warning(
                f"<y>PUSHER</y>:图片下载全部失败，共 {len(errors)} 个错误。")
        return None

    async def _save_bytes_to_cache(self, binary: bytes) -> Path | None:
        """保存图片到缓存"""
        img_path = self._get_cache_path()
        if not img_path:
            return None
        try:
            img_path.parent.mkdir(parents=True, exist_ok=True)
            temp_path = img_path.with_suffix('.tmp')
            with open(temp_path, 'wb') as f:
                f.write(binary)
            shutil.move(temp_path, img_path)
            logger.opt(colors=True).debug(
                f"<g>PUSHER</g>:图片保存成功 -> {img_path}")
            return img_path
        except Exception as e:
            logger.opt(colors=True).warning(
                f"<y>PUSHER</y>:图片写入或移动失败，{e}")
            if 'temp_path' in locals() and temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError:
                    pass
            return None

    def _fallback_to_available_image(self) -> Path | None:
        """回退到可用图片"""
        if self.output_img and self.output_img.exists():
            logger.opt(colors=True).warning(
                '<y>PUSHER</y>:获取新图片失败，回退使用超期图片')
            return self.output_img
        logger.opt(colors=True).warning(
            '<y>PUSHER</y>:获取新/过期图片失败，使用默认图片')
        return self._get_default_image()
    def _get_default_image(self) -> Path | None:
        """获取默认图片"""
        try:
            res_path = Path(__file__).parent.parent.parent / "res" / "default_img.png"
            if not res_path.exists():
                logger.opt(colors=True).warning(
                    f"<y>PUSHER</y>:默认图片不存在 {res_path}")
                return None
            return res_path
        except Exception as e:
            logger.opt(colors=True).warning(
                f"<y>PUSHER</y>:获取默认图片失败：{e}")
            return None

    @staticmethod
    def _is_cache_img_expired(img_path: str | Path, expire_hours: float = 14 * 24) -> bool:
        """检查缓存图片是否过期"""
        path = Path(img_path) if isinstance(img_path, str) else img_path
        try:
            if not path.is_file():
                logger.opt(colors=True).debug(
                    f"<y>Utils</y>:缓存图片不存在，视为过期: {path}")
                return True
            modified_timestamp = path.stat().st_mtime
            modified_time = datetime.fromtimestamp(modified_timestamp)
            is_expired = datetime.now() - modified_time > timedelta(hours=expire_hours)
            logger.opt(colors=True).trace(
                f"<y>Utils</y>:检查图片 {path} 是否过期: {is_expired}")
            return is_expired
        except OSError as e:
            logger.opt(colors=True).warning(
                f"<y>Utils</y>:检查图片 {path} 修改时间时发生 OS 错误：{e}，视为已过期")
            return True
        except Exception as e:
            logger.opt(colors=True).error(
                f"<r>Utils</r>:检查图片 {path} 是否过期时发生未知严重错误：{e}，视为已过期")
            return True
