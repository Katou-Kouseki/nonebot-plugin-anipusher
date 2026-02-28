#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
推送缓冲器模块 - 负责延迟合并推送功能
主要功能包括：
- 合并相同作品的多集推送
- 智能集数范围显示（E01-E12 或 E01,E03,E05-E07）
- 防止重复推送
- 保留第一集图片用于合并推送
"""

import asyncio
import re
from typing import Dict, List, Any, Callable
from nonebot import logger


class PushBuffer:
    """
    推送缓冲器类 - 合并相同作品的多集推送
    
    当同一作品的多个剧集在短时间内更新时，会将这些推送合并为一条消息，
    减少消息刷屏，提升用户体验。
    
    Attributes:
        buffer: 存储待推送数据的缓冲区，key为"标题_S季数"
        tasks: 存储延迟推送任务的字典
        locks: 每个缓冲key对应的异步锁
    """
    
    def __init__(self):
        """初始化推送缓冲器"""
        self.buffer: Dict[str, List[Dict[str, Any]]] = {}
        self.tasks: Dict[str, asyncio.Task] = {}
        self.locks: Dict[str, asyncio.Lock] = {}
    
    async def add_episode(
        self, 
        title: str, 
        episode_data: Dict[str, Any], 
        push_callback: Callable
    ):
        """
        添加一集到缓冲区
        
        Args:
            title: 作品标题（用作分组key）
            episode_data: 集数据字典
            push_callback: 推送回调函数
        """
        season = self._extract_season_number(episode_data.get('season', '1'))
        buffer_key = f"{title}_S{season}"
        
        if buffer_key not in self.locks:
            self.locks[buffer_key] = asyncio.Lock()
        
        async with self.locks[buffer_key]:
            if buffer_key not in self.buffer:
                self.buffer[buffer_key] = []
                logger.opt(colors=True).info(
                    f"<g>PushBuffer</g>: 开始缓冲 [{title}] 第 {season} 季，60秒后推送"
                )
            
            self.buffer[buffer_key].append(episode_data)
            
            if buffer_key in self.tasks and not self.tasks[buffer_key].done():
                self.tasks[buffer_key].cancel()
            
            self.tasks[buffer_key] = asyncio.create_task(
                self._delayed_push(buffer_key, push_callback)
            )
    
    async def _delayed_push(self, buffer_key: str, push_callback: Callable):
        """延迟推送"""
        try:
            await asyncio.sleep(60)
            
            async with self.locks[buffer_key]:
                if buffer_key not in self.buffer or not self.buffer[buffer_key]:
                    return
                
                episodes = self.buffer[buffer_key]
                episode_count = len(episodes)
                title = episodes[0].get('title', '未知标题')
                merged_data = self._merge_episodes(episodes, title)
                
                await push_callback(merged_data, is_merged=True)
                
                del self.buffer[buffer_key]
                logger.opt(colors=True).info(
                    f"<g>PushBuffer</g>: 推送完成并清空缓冲区 [{buffer_key}]"
                )

        except Exception as e:
            logger.opt(colors=True).error(
                f"<r>PushBuffer</r>: 延迟推送失败 [{buffer_key}]: {e}"
            )
            if buffer_key in self.buffer:
                del self.buffer[buffer_key]

    def _merge_episodes(self, episodes: List[Dict[str, Any]], title: str) -> Dict[str, Any]:
        """
        合并多集数据
        
        Args:
            episodes: 集数据列表
            title: 作品标题
            
        Returns:
            Dict[str, Any]: 合并后的数据字典，包含：
                - title: 作品名
                - season: 季数
                - episode_count: 集数
                - episode_range: 集数范围显示（如 E01-E12）
                - episode_list: 集数列表
                - is_merged: 合并标记
                - image: 第一集的图片路径
        """
        episode_numbers = []
        season = None
        
        for ep in episodes:
            episode_num = self._extract_episode_number(ep.get('episode', ''))
            if episode_num:
                episode_numbers.append(episode_num)
            
            if season is None:
                season = self._extract_season_number(ep.get('season', ''))
        
        episode_numbers = sorted(set(episode_numbers))
        episode_range = self._format_episode_range(episode_numbers)
        
        merged = episodes[0].copy()
        first_image = merged.get('image')
        
        logger.opt(colors=True).debug(
            f"<g>PushBuffer</g>: 合并 [{title}] 使用第一集图片: {first_image}"
        )

        action = episodes[-1].get('action')
        source = episodes[-1].get('source', '')
        if 'EMBY' in source.upper():
            action = '媒体库批量更新'
        elif not action:
            action = '下载合并推送'

        merged.update({
            'title': title,
            'season': season or '1',
            'episode_count': len(episode_numbers),
            'episode_range': episode_range,
            'episode_list': episode_numbers,
            'is_merged': True,
            'action': action,
            'timestamp': episodes[-1].get('timestamp'),
        })
        
        if first_image:
            merged['image'] = first_image
        
        logger.opt(colors=True).info(
            f"<g>PushBuffer</g>: 合并完成 [{title}] 第{season}季 {len(episode_numbers)}集 ({episode_range}), 图片: {first_image}"
        )
        
        return merged
    
    def _extract_episode_number(self, episode_str: str) -> int:
        """从字符串中提取集数"""
        if not episode_str:
            return 0
        
        match = re.search(r'\d+', str(episode_str))
        if match:
            return int(match.group())
        return 0
    
    def _extract_season_number(self, season_str: str) -> str:
        """从字符串中提取季数"""
        if not season_str:
            return '1'
        
        if isinstance(season_str, str) and season_str.strip().lower() == 'none':
            return '1'
        
        match = re.search(r'\d+', str(season_str))
        if match:
            return match.group()
        return '1'
    
    def _format_episode_range(self, episode_numbers: List[int]) -> str:
        """
        格式化集数范围
        
        Examples:
            [1,2,3,4,5] -> "E01-E05"
            [1,3,5,6,7,10] -> "E01,E03,E05-E07,E10"
        """
        if not episode_numbers:
            return "未知"
        
        if len(episode_numbers) == 1:
            return f"E{episode_numbers[0]:02d}"
        
        ranges = []
        start = episode_numbers[0]
        end = start
        
        for i in range(1, len(episode_numbers)):
            if episode_numbers[i] == end + 1:
                end = episode_numbers[i]
            else:
                if start == end:
                    ranges.append(f"E{start:02d}")
                else:
                    ranges.append(f"E{start:02d}-E{end:02d}")
                start = episode_numbers[i]
                end = start
        
        if start == end:
            ranges.append(f"E{start:02d}")
        else:
            ranges.append(f"E{start:02d}-E{end:02d}")
        
        return ",".join(ranges)


_push_buffer = None


def get_push_buffer() -> PushBuffer:
    """获取全局推送缓冲器实例"""
    global _push_buffer
    if _push_buffer is None:
        _push_buffer = PushBuffer()
    return _push_buffer
