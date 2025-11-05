# -*- coding: utf-8 -*-
"""
推送机模块
该模块负责具体的消息推送功能，提供了两个核心推送函数：
1. private_msg_pusher - 向指定用户发送私聊消息
2. group_msg_pusher - 向指定群组发送群聊消息
这两个函数封装了与NoneBot交互的底层细节，处理消息发送过程中的异常，并提供日志记录功能。
"""
# 第三方库导入
from nonebot import get_bot, logger
# 项目内部模块导入
from ...exceptions import AppError


async def private_msg_pusher(msg, private_target: list | None):
    """
    向指定用户发送私聊消息。
    Args:
        msg: 要发送的消息内容。
        private_target: 目标用户ID列表，如果为None则不发送。
    Raises:
        AppError.UnknownError: 如果无法获取nonebot对象，抛出异常。
    """
    bot = get_bot()
    if not bot:
        AppError.UnknownError.raise_('nonebot对象获取失败')
    if private_target:
        for user_id in private_target:
            try:
                try:
                    await bot.send_private_msg(user_id=user_id, message=msg)
                except Exception as e:
                    AppError.UnknownError.raise_(f"推送消息至用户 {user_id} 失败 —— {e}")
            except Exception as e:
                logger.opt(exception=True).error(
                    f"<r>PUSHER:</r>{e}")


async def group_msg_pusher(msg, group_target: list | None):
    """
    向指定群组发送群聊消息。
    Args:
        msg: 要发送的消息内容。
        group_target: 目标群组ID列表，如果为None则不发送。
    Raises:
        AppError.UnknownError: 如果无法获取nonebot对象，抛出异常。
    """
    bot = get_bot()
    if not bot:
        AppError.UnknownError.raise_('nonebot对象获取失败')
    if group_target:
        for group_id in group_target:
            try:
                try:
                    await bot.send_group_msg(group_id=group_id, message=msg)
                except Exception as e:
                    AppError.UnknownError.raise_(f"推送消息至群组 {group_id} 失败 —— {e}")
            except Exception as e:
                logger.opt(exception=True).error(
                    f"<r>PUSHER:</r>{e}")
