# -*- coding: utf-8 -*-
"""
推送管理器模块
该模块负责管理和执行消息推送的完整流程，包括：
1. 从数据库获取未发送数据
2. 获取相关动漫信息
3. 生成消息参数
4. 选择推送图片
5. 确定推送目标（私聊和群组）
6. 渲染和发送消息
7. 更新发送状态
8. 支持延迟合并推送功能

核心类: PushManager - 管理整个推送生命周期

调用方式示例：
    # 方式1：直接创建并执行
    await PushManager.create_and_execute(TableName.BANGUMI)

    # 方式2：分步创建与执行
    manager = PushManager(TableName.BANGUMI)
    await manager.execute()
"""
from nonebot import logger
from ...mapping import TableName
from ...exceptions import AppError
from ...database import DatabaseOperator, schema_manager
from ...utils import convert_db_list_first_row_to_dict
from ...config import PUSHTARGET
from .data_picker import DataPicker
from .image_selector import ImageSelector
from .message_factory import MessageRenderer
from .push_machine import private_msg_pusher, group_msg_pusher
from .push_buffer import get_push_buffer


class PushManager:
    """
    推送管理器类
    负责协调整个消息推送流程，从数据获取到最终推送和状态更新。
    支持私聊和群组两种推送方式，并实现了消息的分段渲染优化。
    支持延迟合并推送功能，将同一作品的多个剧集合并为一条消息推送。
    Attributes:
        source: 数据来源表名枚举
        tmdb_id: 媒体的TMDB ID，用于获取额外信息
        unsend_data_id: 当前处理的未发送数据ID
    """

    def __init__(self, source: TableName):
        """
        初始化推送管理器
        Args:
            source: 数据来源表名枚举
        """
        self.source: TableName = source
        self.tmdb_id: int | None = None
        self.unsend_data_id = None
        self.media_type: str | None = None
        self.group_push_target: dict = {}
        self.private_push_target: list = []

    @classmethod
    async def create_and_execute(cls, source: TableName):
        """
        创建并执行推送管理器的便捷方法
        Args:
            source: 数据来源表名枚举
        Returns:
            PushManager: 推送管理器实例
        """
        instance = cls(source)
        await instance.execute()
        return instance

    async def execute(self):
        """
        执行推送管理器
        步骤：
        1. 校验数据来源有效性
        2. 从数据库获取一条未发送的数据
        3. 提取并记录当前数据ID
        4. 根据TMDB ID查询对应的ANIME信息（若无则使用默认空数据）
        5. 使用DataPicker生成完整的消息参数
        6. 通过ImageSelector为消息选择推送图片
        7. 在推送前先标记为已发送，防止重复推送
        8. 合并私聊与群组推送目标
        9. 根据媒体类型决定是否使用缓冲合并推送
        """
        try:
            if not self.source or not isinstance(self.source, TableName):
                AppError.InvalidParameter.raise_(
                    "推送管理器处理失败 —— 未提供有效的数据来源")
            selected_data = await self._select_unsend_data_from_db()
            if not selected_data:
                logger.opt(colors=True).info(
                    f"<y>{self.source.value}</y>:未查询到未发送数据")
                return
            unsend_data = convert_db_list_first_row_to_dict(
                self.source, selected_data)
        except Exception as e:
            logger.opt(exception=True).error(
                f"<r>PUSHER:</r>{e}")
            logger.opt(colors=True).error(
                "<r>PUSHER</r>:获取未发送数据 <r>失败</r> —— 推送流程 <r>中断</r>")
            return
        try:
            self.unsend_data_id = unsend_data.get("id")
            if not self.unsend_data_id:
                AppError.InvalidParameter.raise_(
                    "推送管理器处理失败 —— 未提供有效的数据ID")
        except Exception as e:
            logger.opt(exception=True).error(
                f"<r>PUSHER:</r>{e}")
            logger.opt(colors=True).error(
                "<r>PUSHER</r>:获取未发送数据 <r>失败</r> —— 推送流程 <r>中断</r>")
            return
        try:
            self.tmdb_id = self._get_tmdb_id(unsend_data)
            if self.tmdb_id is None:
                logger.opt(colors=True).warning(
                    "<y>PUSHER</y>:未获取到有效的TMDB ID 跳过ANIME数据库查询")
                anime_db_data = schema_manager.get_default_schema(
                    TableName.ANIME).copy()
            else:
                anime_selected_data = await self._select_anime_data_from_db()
                if not anime_selected_data:
                    logger.opt(colors=True).warning(
                        f"<y>PUSHER</y>:数据库中未查询到 TMDB ID: <c>{self.tmdb_id}</c> 对应条目")
                    anime_db_data = schema_manager.get_default_schema(
                        TableName.ANIME).copy()
                else:
                    anime_db_data = convert_db_list_first_row_to_dict(TableName.ANIME,
                                                                      anime_selected_data)
        except Exception as e:
            logger.opt(exception=True).error(
                f"<r>PUSHER:</r>{e}")
            logger.opt(colors=True).error(
                "<r>PUSHER:</r>获取对应ANIME数据库数据 <r>失败</r> —— 跳过此部分数据")
            anime_db_data = schema_manager.get_default_schema(
                TableName.ANIME).copy()
        try:
            try:
                picker = DataPicker(self.source, unsend_data, anime_db_data)
                message_params = picker.pick()
            except Exception as e:
                AppError.MessageParameterGenerateError.raise_(f"{str(e)}")
            logger.opt(colors=True).info(
                "<g>PUSHER</g>:消息参数生成    |<g>SUCCESS</g>")
        except Exception as e:
            logger.opt(exception=True).error(
                f"<r>PUSHER:</r>{e}")
            logger.opt(colors=True).error(
                "<r>PUSHER:</r>消息参数生成 <r>失败</r> —— 推送流程 <r>中断</r>")
            return
        try:
            image_queue = message_params.get("image_queue", [])
            try:
                image_selector = ImageSelector(
                    image_queue, 
                    str(self.tmdb_id),
                    source_data=unsend_data,
                    emby_series_id=unsend_data.get("series_id")
                )
                image_path = await image_selector.select()
            except Exception as e:
                AppError.ImageSelectorCreateError.raise_(f"{str(e)}")
        except Exception as e:
            logger.opt(exception=True).error(
                f"<r>PUSHER</r>:{e}")
            logger.opt(colors=True).error(
                "<r>PUSHER</r>:获取图片地址 <r>失败</r> —— 跳过图片发送")
            image_path = None
        message_params["image"] = image_path
        try:
            self.private_push_target, self.group_push_target = self._pushtarget_conflate(
                message_params)
        except Exception as e:
            logger.opt(exception=True).error(
                f"<r>PUSHER:</r>{e}")
            logger.opt(colors=True).error(
                "<r>PUSHER</r>:推送目标检索 <r>失败</r> —— 推送流程 <r>中断</r>")
            return
        try:
            await self._change_send_status()
            logger.opt(colors=True).info(
                "<g>PUSHER</g>:更新数据发送状态    |<g>SUCCESS</g>")
        except Exception as e:
            logger.opt(exception=True).error(
                f"<r>PUSHER:</r>{e}")
            logger.opt(colors=True).error(
                "<r>PUSHER</r>:更新数据发送状态 <r>失败</r> —— 推送流程 <r>中断</r>")
            return
        self.media_type = message_params.get("media_type")
        title = message_params.get("title")
        if not title:
            logger.opt(colors=True).warning(
                "<y>PUSHER</y>: 标题为空，无法推送")
            return
        if self.media_type and self.media_type.lower() == 'movie':
            await self._do_push(message_params, is_merged=False)
        elif self.media_type and self.media_type.lower() in ('episode', 'series'):
            push_buffer = get_push_buffer()
            await push_buffer.add_episode(
                title=title,
                episode_data=message_params,
                push_callback=self._do_push
            )
            logger.opt(colors=True).info(
                f"<g>PUSHER</g>: [{title}] 已加入推送缓冲区")
        else:
            logger.opt(colors=True).warning(
                f"<y>PUSHER</y>: [{title}] 未知媒体类型 {self.media_type}，直接推送")
            await self._do_push(message_params, is_merged=False)

    async def _do_push(self, message_params: dict, is_merged: bool = False):
        """
        实际执行推送
        Args:
            message_params: 消息参数字典
            is_merged: 是否为合并推送
        """
        try:
            message_renderer = MessageRenderer()
            if is_merged:
                message = message_renderer.render_merged(message_params)
            else:
                message = message_renderer.render_all(message_params)
            logger.opt(colors=True).info(
                "<g>PUSHER</g>:消息渲染  |<g>COMPLETE</g>")
        except Exception as e:
            logger.opt(exception=True).error(
                f"<r>RENDER</r>:{e}")
            logger.opt(colors=True).error(
                "<r>RENDER</r>:消息渲染 <r>失败</r> —— 推送流程 <r>中断</r>")
            return
        await self._push_to_private(message)
        await self._push_to_group(message, message_params)
        push_type = "合并推送" if is_merged else "单集推送"
        logger.opt(colors=True).info(
            f"<g>PUSHER</g>: {push_type} [{message_params.get('title')}] 完成")

    async def _push_to_private(self, message):
        """推送消息到私聊用户"""
        if not self.private_push_target:
            logger.opt(colors=True).info(
                "<g>PUSHER</g>:没有私聊推送目标 —— 消息渲染与发送已跳过 |<g>PASS</g>")
            return
        await private_msg_pusher(message, self.private_push_target)
        logger.opt(colors=True).info(
            "<g>PUSHER</g>:私聊推送        |<g>COMPLETE</g>")

    async def _push_to_group(self, message, message_params: dict):
        """推送消息到群组"""
        if not self.group_push_target:
            logger.opt(colors=True).info(
                "<g>PUSHER</g>:没有群组推送目标 —— 消息渲染与发送已跳过 |<g>PASS</g>")
            return
        try:
            message_renderer = MessageRenderer()
            base_message = message_renderer.render_base(message_params)
            logger.opt(colors=True).info(
                "<g>PUSHER</g>:基础消息渲染  |<g>COMPLETE</g>")
            for group_id, subscriber in self.group_push_target.items():
                message_params["at"] = subscriber
                at_message = message_renderer.render_at(message_params)
                full_message = base_message + at_message
                await group_msg_pusher(full_message, [group_id])
            logger.opt(colors=True).info(
                "<g>PUSHER</g>:群组推送        |<g>COMPLETE</g>")
        except Exception as e:
            logger.opt(exception=True).error(
                f"<r>RENDER</r>:{e}")
            logger.opt(colors=True).error(
                "<r>RENDER</r>:消息渲染 <r>失败</r> —— 推送流程 <r>中断</r>")
            return

    async def _select_unsend_data_from_db(self) -> list:
        """
        从数据库中选择未发送的数据
        Returns:
            tuple: 查询到的未发送数据元组
        Raises:
            AppError.MissingParameter: 当未提供有效数据来源时
            AppError.DatabaseQueryError: 当数据库查询失败时
        """
        try:
            db_operator = DatabaseOperator()
            if not self.source:
                AppError.MissingParameter.raise_(
                    "查询数据库失败 —— 未提供有效的数据来源")
            return await db_operator.select_data(table_name=self.source,
                                                 where={"send_status": 0},
                                                 order_by="id",
                                                 order_type="DESC",
                                                 limit=1)
        except AppError.Exception:
            raise
        except Exception as e:
            AppError.DatabaseQueryError.raise_(
                f"{self.source.value}数据库查询失败: {str(e)}")

    async def _select_anime_data_from_db(self) -> list:
        """
        从ANIME数据库中选择相关动漫数据
        Returns:

        Raises:
            AppError.MissingParameter: 当未提供有效TMDB ID时
            AppError.DatabaseQueryError: 当数据库查询失败时
        """
        try:
            if self.tmdb_id == 0:
                AppError.MissingParameter.raise_(
                    "获取ANIME数据库数据失败 —— 未提供有效的TMDB ID")
            db_operator = DatabaseOperator()
            return await db_operator.select_data(table_name=TableName.ANIME,
                                                 where={
                                                     "tmdb_id": self.tmdb_id},
                                                 limit=1)
        except AppError.Exception:
            raise
        except Exception as e:
            AppError.DatabaseQueryError.raise_(f"ANIME数据库查询失败: {str(e)}")

    def _get_tmdb_id(self, data: dict) -> int | None:
        """
        从数据中提取TMDB ID
        Args:
            data: 包含TMDB ID的数据字典
        Returns:
            int: TMDB ID，如果未找到则返回0
        Raises:
            AppError.MissingParameter: 当未提供有效数据时
            AppError.TmdbIdFetchError: 当获取TMDB ID失败时
        """
        try:
            if not data:
                AppError.MissingParameter.raise_(
                    "获取TMDB ID失败 —— 未提供有效的未发送数据")
            tmdb_id_value = data.get("tmdb_id", None)
            if tmdb_id_value == "None" or tmdb_id_value is None:
                return None
            try:
                return int(tmdb_id_value)
            except (ValueError, TypeError):
                logger.opt(colors=True).warning(
                    f"<y>PUSHER</y>:TMDB ID 格式错误，请检查数据 —— TMDB ID: <c>{tmdb_id_value}</c> TYPE: <c>{type(tmdb_id_value).__name__}</c>")
                return None
        except Exception as e:
            AppError.TmdbIdFetchError.raise_(f"{str(e)}")

    def _pushtarget_conflate(self, picked_params: dict) -> tuple:
        """
        合并和计算推送目标
        根据订阅者信息和配置的推送目标，计算最终的推送对象列表
        Args:
            picked_params: 包含订阅者信息的参数字典
        Returns:
            tuple: (私聊推送目标列表, 群组推送目标字典)
        Raises:
            AppError.PushTargetMergeError: 当合并推送目标失败时
        """
        try:
            private_subscribers = picked_params.get(
                "private_subscribers", []) or []
            group_subscribers = picked_params.get(
                "group_subscribers", {}) or {}
            private_pusher_user = PUSHTARGET.PrivatePushTarget.get(
                self.source.value, []) or []
            group_pusher_user = PUSHTARGET.GroupPushTarget.get(
                self.source.value, []) or []
            private_pusher_user_set = set(map(str, private_pusher_user))
            private_subscribers_str = set(map(str, private_subscribers))
            private_push_target = list(
                private_subscribers_str & private_pusher_user_set)
            group_pusher_user_set = set(map(str, group_pusher_user))
            group_push_target = {}
            for group_id in group_pusher_user_set:
                group_push_target[group_id] = group_subscribers.get(
                    group_id, []) or group_subscribers.get(int(group_id), []) or []
            return private_push_target, group_push_target
        except AppError.Exception:
            raise
        except Exception as e:
            AppError.PushTargetMergeError.raise_(f"{str(e)}")

    async def _change_send_status(self):
        """
        更新数据的发送状态
        将处理完成的数据标记为已发送（send_status=1）
        Raises:
            AppError.SendStatusUpdateError: 当更新失败时抛出
        """
        try:
            db_operator = DatabaseOperator()
            await db_operator.upsert_data(table_name=self.source,
                                          data={"id": self.unsend_data_id,
                                                "send_status": 1},
                                          conflict_column="id")
        except AppError.Exception:
            raise
        except Exception as e:
            AppError.SendStatusUpdateError.raise_(f"{str(e)}")
