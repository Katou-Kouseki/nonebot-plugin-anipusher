import asyncio
import shutil
import aiohttp
from pathlib import Path
from typing import Literal
from nonebot import logger

from ...config import WORKDIR, APPCONFIG, FUNCTION
from ...utils import CommonUtils, EmbyUtils
from ...exceptions import AppError
from ...external import get_request


class ImageProcessor:
    def __init__(self, image_queue: list, emby_series_id: str | None = None, tmdb_id: str | None = None) -> None:
        self.image_queue = image_queue
        self.emby_series_id = emby_series_id
        self.tmdb_id = tmdb_id
        self.is_image_expired = False  # 图片是否过期
        self.output_img = None  # 最终图片输出路径

    async def process(self) -> Path | None:
        # 先搜索本地存储
        self.output_img = self._search_in_localstore()  # 如果有且未过期，则设置output_img并返回，否则继续
        # 如果有未过期的本地图片，直接返回
        if self.output_img and not self.is_image_expired:
            logger.opt(colors=True).info('<g>Pusher</g>：发现可用的本地图片，使用本地图片')
            return self.output_img
        # 本地图片已过期时的日志
        if self.output_img and self.is_image_expired:
            logger.opt(colors=True).info('<y>Pusher</y>：发现本地图片已过期，尝试获取新图片')
        # 处理图片队列
        result = await self._process_image_queue()
        if result:
            return result
        # 所有尝试失败后的回退逻辑
        return self._fallback_to_available_image()

    async def _process_image_queue(self) -> Path | None:
        # 如果图片队列不为空，则处理图片队列
        if not self.image_queue:
            return None
        # 清理图片队列，获取有效图片列表
        cleaned_urls = self._clean_image_queue()
        if not cleaned_urls:
            return None
        # 下载并保存图片
        image_data = await self._download_first_valid_image(cleaned_urls)
        if not image_data:
            return None
        img_path = await self._save_bytes_to_cache(image_data)
        if img_path:
            self.output_img = img_path
            logger.opt(colors=True).info('<g>Pusher</g>：刷新图片缓存 <g>完成</g>')
            return img_path
        return None

    # 在本地存储中查找图片，如果找不到，则返回None，等待后续处理
    def _search_in_localstore(self) -> None | Path:
        try:
            if not self.tmdb_id:
                raise AppError.Exception(
                    AppError.MissingData, "项目TMDB ID缺失！")
            if not WORKDIR.cache_dir:
                raise AppError.Exception(AppError.MissingData, "项目缓存目录缺失！")
            local_img_path = WORKDIR.cache_dir / f"{self.tmdb_id}.png"
            # 如果本地存在图片，且未过期，则直接返回base64编码
            if not local_img_path.exists():
                logger.opt(colors=True).info(
                    "<y>Pusher</y>：本地图片不存在，尝试获取新图片")
                return None
            # 如果图片未过期，则直接返回base64编码
            if CommonUtils.is_cache_img_expired(local_img_path):
                self.is_image_expired = True
            return local_img_path
        except Exception as e:
            logger.opt(colors=True).warning(
                f"<y>Pusher</y>：获取本地图片失败，错误信息：{e}")
            return None

    # 获取默认图片
    def _default_image(self) -> Path | None:
        try:
            if not WORKDIR.cache_dir:
                raise AppError.Exception(AppError.MissingData, "项目缓存目录缺失！")
            img_path = WORKDIR.cache_dir / "res" / "default_img.png"
            if not img_path.exists():
                logger.opt(colors=True).warning(
                    f"<y>Pusher</y>：默认图片不存在，请检查路径{img_path}")
                return None
            return img_path
        except Exception as e:
            logger.opt(colors=True).warning(
                f"<y>Pusher</y>：获取默认图片失败，错误信息：{e}")
            return None

    def _clean_image_queue(self):
        url_dict = {}  # 存储图片url,key是url，value是数据源
        for item in self.image_queue:  # 遍历图片队列
            if CommonUtils.is_url(str(item)):
                if item not in url_dict:
                    url_dict[item] = "ANI_RSS"
                else:
                    continue
            else:
                # 如果不是url，则为emby的tag，需要转换为url
                if not FUNCTION.emby_enabled:
                    continue
                try:
                    url = EmbyUtils.splice_emby_image_url(
                        APPCONFIG.emby_host, self.emby_series_id, item)
                    if url not in url_dict:
                        url_dict[url] = "EMBY"
                    else:
                        continue
                except Exception as e:
                    logger.opt(colors=True).warning(
                        f"<y>Pusher</y>：获取emby图片失败，错误信息：{e}")
        return url_dict

    async def _download_first_valid_image(self, url_dict: dict):
        tasks = []  # 初始化任务列表
        errors = []  # 初始化错误列表
        binary = None  # 初始化结果
        for url, source in url_dict.items():
            try:
                if source == "ANI_RSS":
                    headers = {
                        "User-Agent": "AriadusTTT/nonebot_plugin_AniPush/1.0.0 (Python)"}
                    proxy = None
                elif source == "EMBY":
                    headers = {
                        "X-Emby-Token": APPCONFIG.emby_key,
                        "User-Agent": "AriadusTTT/nonebot_plugin_AniPush/1.0.0 (Python)"
                    }
                    proxy = APPCONFIG.proxy
                task = asyncio.create_task(
                    get_request(url,
                                headers=headers,
                                proxy=proxy,
                                is_binary=True,
                                timeout=aiohttp.ClientTimeout(
                                    total=15,      # 总超时
                                    connect=5,    # 连接超时
                                    sock_read=5  # 读取超时
                                )))
                tasks.append(task)
            except Exception as e:
                logger.opt(colors=True).warning(
                    f"<y>Pusher</y>：{url}下载任务创建失败，错误信息：{e}")
                continue
        if not tasks:  # 如果没有创建任何任务
            return None
        # 使用as_completed迭代处理
        for task in asyncio.as_completed(tasks):
            try:
                binary = await task
                for t in tasks:
                    if not t.done():
                        t.cancel()
                        try:
                            await t  # 等待取消完成
                        except (asyncio.CancelledError, Exception):
                            pass  # 预期中的异常，无需处理
                return binary  # 返回第一个成功的结果的二进制数据
            except Exception as e:
                errors.append(e)
        logger.opt(colors=True).warning(
            f"<y>Pusher</y>：图片下载全部失败，错误信息：{errors}")
        return None

    async def _save_bytes_to_cache(self, binary: bytes) -> Path | Literal[False]:
        if not WORKDIR.cache_dir:
            logger.opt(colors=True).warning(
                "<y>Pusher</y>：缓存目录缺失！")
            return False
        WORKDIR.cache_dir.mkdir(parents=True, exist_ok=True)
        img_path = WORKDIR.cache_dir / f"{self.tmdb_id}.png"
        try:
            temp_path = img_path.with_suffix('.tmp')
            temp_path.write_bytes(binary)
        except Exception as e:
            logger.opt(colors=True).warning(
                f"<y>Pusher</y>：图片写入失败，错误信息：{e}")
            return False
        try:
            shutil.move(temp_path, img_path)
        except Exception as e:
            logger.opt(colors=True).warning(
                f"<y>Pusher</y>：图片替换失败，错误信息：{e}")
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception as e:
                    logger.opt(colors=True).warning(
                        f"<y>Pusher</y>：临时图片删除失败，错误信息：{e}")
            return False
        return img_path

    def _fallback_to_available_image(self) -> Path | None:
        """回退到可用图片（过期图片或默认图片）"""
        if self.output_img:
            logger.opt(colors=True).info('<y>Pusher</y>：获取新图片失败，回退使用超期图片')
            return self.output_img

        logger.opt(colors=True).info('<y>Pusher</y>：没有获取到可用图片，使用默认图片')
        return self._default_image()
