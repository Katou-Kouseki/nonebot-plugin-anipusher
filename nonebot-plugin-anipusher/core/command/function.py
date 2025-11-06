from nonebot.exception import FinishedException
from nonebot import on_command, logger
from ...exceptions import AppError
from nonebot.adapters.onebot.v11 import PrivateMessageEvent, GroupMessageEvent
from ...config import PUSHTARGET, WORKDIR
from ...mapping import TableName
import json


register_emby_push = on_command(
    "启用EMBY推送", aliases={"启用Emby推送",
                         "启用emby推送",
                         "启用EMBY推送服务",
                         "启用Emby推送服务",
                         "启用emby推送服务",
                         "启用EMBY推送功能",
                         "启用Emby推送功能",
                         "启用emby推送功能"})

register_anirss_push = on_command(
    "启用AniRSS推送", aliases={"启用anirss推送",
                           "启用ANIRSS推送",
                           "启用AniRSS推送服务",
                           "启用anirss推送服务",
                           "启用ANIRSS推送服务",
                           "启用AniRSS推送功能",
                           "启用anirss推送功能",
                           "启用ANIRSS推送功能"})

unregister_emby_push = on_command(
    "取消EMBY推送", aliases={"取消Emby推送",
                         "取消emby推送",
                         "取消EMBY推送服务",
                         "取消Emby推送服务",
                         "取消emby推送服务",
                         "取消EMBY推送功能",
                         "取消Emby推送功能",
                         "取消emby推送功能",
                         "禁用EMBY推送",
                         "禁用Emby推送",
                         "禁用emby推送"})

unregister_anirss_push = on_command(
    "取消AniRSS推送", aliases={"取消anirss推送",
                           "取消ANIRSS推送",
                           "取消AniRSS推送服务",
                           "取消anirss推送服务",
                           "取消ANIRSS推送服务",
                           "取消AniRSS推送功能",
                           "取消anirss推送功能",
                           "取消ANIRSS推送功能",
                           "禁用AniRSS推送",
                           "禁用anirss推送",
                           "禁用ANIRSS推送"})

temp_block_push = on_command(
    "屏蔽推送", aliases={"屏蔽推送服务"})

restart_push = on_command(
    "重启推送", aliases={"重启推送服务"})

get_push_user = on_command(
    "获取推送用户", aliases={"获取推送服务用户"})


@register_emby_push.handle()
async def register_emby(event: PrivateMessageEvent | GroupMessageEvent):
    logger.opt(colors=True).info("<c>COMMAND</c>: 匹配命令 —— 启用EMBY推送功能")
    try:
        if isinstance(event, PrivateMessageEvent):
            user_id = int(event.user_id)
            if not user_id:
                AppError.MissingRequiredField.raise_("未获取到COMMAND用户ID")
            if not WORKDIR.config_file:
                AppError.EmptyParameter.raise_("推送对象json文件路径缺失")
            if not WORKDIR.config_file.exists():
                AppError.FileIOError.raise_("推送对象json文件不存在")
            private_target = PUSHTARGET.PrivatePushTarget.setdefault(
                TableName.EMBY.value, [])
            if user_id in private_target:
                logger.opt(colors=True).info(
                    f"<c>COMMAND</c>: 用户ID <c>{user_id}</c> 已注册EMBY推送功能, 无需重复注册")
                await register_emby_push.finish(f"{event.user_id} 已启用EMBY推送功能, 无需重复启用")
            private_target.append(str(user_id))
            with open(WORKDIR.config_file, 'r', encoding='utf-8') as file:
                data = json.load(file)
            data.setdefault('PrivatePushTarget', {})[TableName.EMBY.value] = private_target
            with open(WORKDIR.config_file, 'w', encoding='utf-8') as file:
                json.dump(data, file, ensure_ascii=False, indent=4)
            logger.opt(colors=True).info(
                f"<c>COMMAND</c>: 用户ID <c>{user_id}</c> 启用EMBY推送功能 —— <g>SUCCESS</g>")
            await register_emby_push.finish(f"{event.user_id} 启用EMBY推送功能 —— SUCCESS")
        elif isinstance(event, GroupMessageEvent):
            group_id = int(event.group_id)
            if not group_id:
                AppError.MissingRequiredField.raise_("未获取到COMMAND群ID")
            if not WORKDIR.config_file:
                AppError.EmptyParameter.raise_("推送对象json文件路径缺失")
            if not WORKDIR.config_file.exists():
                AppError.FileIOError.raise_("推送对象json文件不存在")
            group_target = PUSHTARGET.GroupPushTarget.setdefault(
                TableName.EMBY.value, [])
            if group_id in group_target:
                logger.opt(colors=True).info(
                    f"<c>COMMAND</c>:群组 <c>{group_id}</c> 已启用EMBY推送功能, 无需重复启用")
                await register_emby_push.finish(f"群组 {group_id} 已启用EMBY推送功能, 无需重复启用")
            group_target.append(str(group_id))
            with open(WORKDIR.config_file, 'r', encoding='utf-8') as file:
                data = json.load(file)
            data.setdefault('GroupPushTarget', {})[TableName.EMBY.value] = group_target
            with open(WORKDIR.config_file, 'w', encoding='utf-8') as file:
                json.dump(data, file, ensure_ascii=False, indent=4)
            logger.opt(colors=True).info(
                f"<c>COMMAND</c>:群组 <c>{group_id}</c> 已成功启用EMBY推送功能")
            await register_emby_push.finish(f"群组 {event.group_id} 已成功启用EMBY推送功能")
    except FinishedException:
        raise
    except Exception as e:
        logger.opt(colors=True).error(f"<c>COMMAND</c>: 注册EMBY推送功能 <r>失败</r> —— {e}")
        await register_emby_push.finish(f"启用EMBY推送功能失败 - {e}")


@register_anirss_push.handle()
async def register_anirss(event: PrivateMessageEvent | GroupMessageEvent):
    logger.opt(colors=True).info("<c>COMMAND</c>: 匹配命令 —— 启用AniRSS推送功能")
    try:
        if isinstance(event, PrivateMessageEvent):
            user_id = int(event.user_id)
            if not user_id:
                AppError.MissingRequiredField.raise_("未获取到COMMAND用户ID")
            if not WORKDIR.config_file:
                AppError.EmptyParameter.raise_("推送对象json文件路径缺失")
            if not WORKDIR.config_file.exists():
                AppError.FileIOError.raise_("推送对象json文件不存在")
            private_target = PUSHTARGET.PrivatePushTarget.setdefault(
                TableName.ANIRSS.value, [])
            if user_id in private_target:
                logger.opt(colors=True).info(
                    f"<c>COMMAND</c>: 用户ID <c>{user_id}</c> 已注册AniRSS推送功能, 无需重复注册")
                await register_anirss_push.finish(f"{event.user_id} 已启用AniRSS推送功能, 无需重复启用")
            private_target.append(str(user_id))
            with open(WORKDIR.config_file, 'r', encoding='utf-8') as file:
                data = json.load(file)
            data.setdefault('PrivatePushTarget', {})[TableName.ANIRSS.value] = private_target
            with open(WORKDIR.config_file, 'w', encoding='utf-8') as file:
                json.dump(data, file, ensure_ascii=False, indent=4)
            logger.opt(colors=True).info(
                f"<c>COMMAND</c>: 用户ID <c>{user_id}</c> 启用AniRSS推送功能 —— <g>SUCCESS</g>")
            await register_anirss_push.finish(f"{event.user_id} 启用AniRSS推送功能 —— SUCCESS")
        elif isinstance(event, GroupMessageEvent):
            group_id = int(event.group_id)
            if not group_id:
                AppError.MissingRequiredField.raise_("未获取到COMMAND群ID")
            if not WORKDIR.config_file:
                AppError.EmptyParameter.raise_("推送对象json文件路径缺失")
            if not WORKDIR.config_file.exists():
                AppError.FileIOError.raise_("推送对象json文件不存在")
            group_target = PUSHTARGET.GroupPushTarget.setdefault(
                TableName.ANIRSS.value, [])
            if group_id in group_target:
                logger.opt(colors=True).info(
                    f"<c>COMMAND</c>:群组 <c>{group_id}</c> 已启用AniRSS推送功能, 无需重复启用")
                await register_anirss_push.finish(f"群组 {group_id} 已启用AniRSS推送功能, 无需重复启用")
            group_target.append(str(group_id))
            with open(WORKDIR.config_file, 'r', encoding='utf-8') as file:
                data = json.load(file)
            data.setdefault('GroupPushTarget', {})[TableName.ANIRSS.value] = group_target
            with open(WORKDIR.config_file, 'w', encoding='utf-8') as file:
                json.dump(data, file, ensure_ascii=False, indent=4)
            logger.opt(colors=True).info(
                f"<c>COMMAND</c>:群组 <c>{group_id}</c> 启用AniRSS推送功能 —— SUCCESS")
            await register_anirss_push.finish(f"群组 {event.group_id} 启用AniRSS推送功能 —— SUCCESS")
    except FinishedException:
        raise
    except Exception as e:
        logger.opt(colors=True).error(f"<c>COMMAND</c>: 注册AniRSS推送功能 <r>失败</r> —— {e}")
        await register_anirss_push.finish(f"启用AniRSS推送功能失败 - {e}")


@unregister_emby_push.handle()
async def unregister_emby(event: PrivateMessageEvent | GroupMessageEvent):
    logger.opt(colors=True).info("<c>COMMAND</c>: 匹配命令 —— 禁用EMBY推送功能")
    try:
        if isinstance(event, PrivateMessageEvent):
            user_id = int(event.user_id)
            if not user_id:
                AppError.MissingRequiredField.raise_("未获取到COMMAND用户ID")
            if not WORKDIR.config_file:
                AppError.EmptyParameter.raise_("推送对象json文件路径缺失")
            if not WORKDIR.config_file.exists():
                AppError.FileIOError.raise_("推送对象json文件不存在")
            private_target = PUSHTARGET.PrivatePushTarget.setdefault(
                TableName.EMBY.value, [])
            if user_id not in private_target:
                logger.opt(colors=True).info(
                    f"<c>COMMAND</c>: 用户ID <c>{user_id}</c> 未启用EMBY推送功能, 无需禁用")
                await unregister_emby_push.finish(f"{event.user_id} 未启用EMBY推送功能, 无需禁用")
            private_target.remove(str(user_id))
            with open(WORKDIR.config_file, 'r', encoding='utf-8') as file:
                data = json.load(file)
            data.setdefault('PrivatePushTarget', {})[TableName.EMBY.value] = private_target
            with open(WORKDIR.config_file, 'w', encoding='utf-8') as file:
                json.dump(data, file, ensure_ascii=False, indent=4)
            logger.opt(colors=True).info(
                f"<c>COMMAND</c>: 用户ID <c>{user_id}</c> 禁用EMBY推送功能 —— <g>SUCCESS</g>")
            await unregister_emby_push.finish(f"{event.user_id} 禁用EMBY推送功能 —— SUCCESS")
        elif isinstance(event, GroupMessageEvent):
            group_id = int(event.group_id)
            if not group_id:
                AppError.MissingRequiredField.raise_("未获取到COMMAND群ID")
            if not WORKDIR.config_file:
                AppError.EmptyParameter.raise_("推送对象json文件路径缺失")
            if not WORKDIR.config_file.exists():
                AppError.FileIOError.raise_("推送对象json文件不存在")
            group_target = PUSHTARGET.GroupPushTarget.setdefault(
                TableName.EMBY.value, [])
            if group_id not in group_target:
                logger.opt(colors=True).info(
                    f"<c>COMMAND</c>:群组 <c>{group_id}</c> 未启用EMBY推送功能, 无需禁用")
                await unregister_emby_push.finish(f"群组 {group_id} 未启用EMBY推送功能, 无需禁用")
            group_target.remove(str(group_id))
            with open(WORKDIR.config_file, 'r', encoding='utf-8') as file:
                data = json.load(file)
            data.setdefault('GroupPushTarget', {})[TableName.EMBY.value] = group_target
            with open(WORKDIR.config_file, 'w', encoding='utf-8') as file:
                json.dump(data, file, ensure_ascii=False, indent=4)
            logger.opt(colors=True).info(
                f"<c>COMMAND</c>:群组 <c>{group_id}</c> 已成功禁用EMBY推送功能")
            await unregister_emby_push.finish(f"群组 {event.group_id} 已成功禁用EMBY推送功能")
    except FinishedException:
        raise
    except Exception as e:
        logger.opt(colors=True).error(f"<c>COMMAND</c>: 禁用EMBY推送功能 <r>失败</r> —— {e}")
        await unregister_emby_push.finish(f"禁用EMBY推送功能失败 - {e}")


@unregister_anirss_push.handle()
async def unregister_anirss(event: PrivateMessageEvent | GroupMessageEvent):
    logger.opt(colors=True).info("<c>COMMAND</c>: 匹配命令 —— 禁用AniRSS推送功能")
    try:
        if isinstance(event, PrivateMessageEvent):
            user_id = int(event.user_id)
            if not user_id:
                AppError.MissingRequiredField.raise_("未获取到COMMAND用户ID")
            if not WORKDIR.config_file:
                AppError.EmptyParameter.raise_("推送对象json文件路径缺失")
            if not WORKDIR.config_file.exists():
                AppError.FileIOError.raise_("推送对象json文件不存在")
            private_target = PUSHTARGET.PrivatePushTarget.setdefault(
                TableName.ANIRSS.value, [])
            if user_id not in private_target:
                logger.opt(colors=True).info(
                    f"<c>COMMAND</c>: 用户ID <c>{user_id}</c> 未启用AniRSS推送功能, 无需禁用")
                await unregister_anirss_push.finish(f"{event.user_id} 未启用AniRSS推送功能, 无需禁用")
            private_target.remove(str(user_id))
            with open(WORKDIR.config_file, 'r', encoding='utf-8') as file:
                data = json.load(file)
            data.setdefault('PrivatePushTarget', {})[TableName.ANIRSS.value] = private_target
            with open(WORKDIR.config_file, 'w', encoding='utf-8') as file:
                json.dump(data, file, ensure_ascii=False, indent=4)
            logger.opt(colors=True).info(
                f"<c>COMMAND</c>: 用户ID <c>{user_id}</c> 禁用AniRSS推送功能 —— <g>SUCCESS</g>")
            await unregister_anirss_push.finish(f"{event.user_id} 禁用AniRSS推送功能 —— SUCCESS")
        elif isinstance(event, GroupMessageEvent):
            group_id = int(event.group_id)
            if not group_id:
                AppError.MissingRequiredField.raise_("未获取到COMMAND群ID")
            if not WORKDIR.config_file:
                AppError.EmptyParameter.raise_("推送对象json文件路径缺失")
            if not WORKDIR.config_file.exists():
                AppError.FileIOError.raise_("推送对象json文件不存在")
            group_target = PUSHTARGET.GroupPushTarget.setdefault(
                TableName.ANIRSS.value, [])
            if group_id not in group_target:
                logger.opt(colors=True).info(
                    f"<c>COMMAND</c>:群组 <c>{group_id}</c> 未启用AniRSS推送功能, 无需禁用")
                await unregister_anirss_push.finish(f"群组 {group_id} 未启用AniRSS推送功能, 无需禁用")
            group_target.remove(str(group_id))
            with open(WORKDIR.config_file, 'r', encoding='utf-8') as file:
                data = json.load(file)
            data.setdefault('GroupPushTarget', {})[TableName.ANIRSS.value] = group_target
            with open(WORKDIR.config_file, 'w', encoding='utf-8') as file:
                json.dump(data, file, ensure_ascii=False, indent=4)
            logger.opt(colors=True).info(
                f"<c>COMMAND</c>:群组 <c>{group_id}</c> 已成功禁用AniRSS推送功能")
            await unregister_anirss_push.finish(f"群组 {event.group_id} 已成功禁用AniRSS推送功能")
    except FinishedException:
        raise
    except Exception as e:
        logger.opt(colors=True).error(f"<c>COMMAND</c>: 禁用AniRSS推送功能 <r>失败</r> —— {e}")
        await unregister_anirss_push.finish(f"禁用AniRSS推送功能失败 - {e}")


@temp_block_push.handle()
async def block():
    logger.opt(colors=True).info("<c>COMMAND</c>: 匹配命令 —— 屏蔽推送")
    try:
        if not WORKDIR.config_file:
            AppError.EmptyParameter.raise_("推送对象json文件路径缺失")
        if not WORKDIR.config_file.exists():
            AppError.FileIOError.raise_("推送对象json文件不存在")
        pushtarget = {
            "PrivatePushTarget": PUSHTARGET.PrivatePushTarget,
            "GroupPushTarget": PUSHTARGET.GroupPushTarget
        }
        with open(WORKDIR.config_file, 'w', encoding='utf-8') as file:
            json.dump(pushtarget, file, ensure_ascii=False, indent=4)
        PUSHTARGET.PrivatePushTarget.clear()
        PUSHTARGET.GroupPushTarget.clear()
        logger.opt(colors=True).info(
            "<c>COMMAND</c>: 已成功屏蔽所有推送目标")
        await temp_block_push.finish("已停止推送服务，如需恢复请使用“重启推送”命令")
    except FinishedException:
        raise
    except Exception as e:
        logger.opt(colors=True).error(f"<c>COMMAND</c>: 屏蔽推送 <r>失败</r> —— {e}")
        await temp_block_push.finish(f"屏蔽推送失败 —— {e}")


@restart_push.handle()
async def restart():
    logger.opt(colors=True).info("<c>COMMAND</c>: 匹配命令 —— 重启推送")
    try:
        if not WORKDIR.config_file:
            AppError.EmptyParameter.raise_("推送对象json文件路径缺失")
        if not WORKDIR.config_file.exists():
            AppError.FileIOError.raise_("推送对象json文件不存在")
        with open(WORKDIR.config_file, 'r', encoding='utf-8') as file:
            data = json.load(file)
        PUSHTARGET.PrivatePushTarget = data.setdefault('PrivatePushTarget', {})
        PUSHTARGET.GroupPushTarget = data.setdefault('GroupPushTarget', {})
        logger.opt(colors=True).info(
            "<c>COMMAND</c>: 已成功重启推送服务")
        await restart_push.finish("已成功重启推送服务")
    except FinishedException:
        raise
    except Exception as e:
        logger.opt(colors=True).error(f"<c>COMMAND</c>: 重启推送 <r>失败</r> —— {e}")
        await restart_push.finish(f"重启推送失败 —— {e}")


@get_push_user.handle()
async def get_user():
    logger.opt(colors=True).info("<c>COMMAND</c>: 匹配命令 —— 获取推送用户")
    try:
        def format_ids(ids):
            """格式化用户ID列表"""
            return "|".join(map(str, ids)) if ids else "暂无用户"
        emby_private_target_str = format_ids(PUSHTARGET.PrivatePushTarget.setdefault(TableName.EMBY.value, []))
        anirss_private_target_str = format_ids(PUSHTARGET.PrivatePushTarget.setdefault(TableName.ANIRSS.value, []))
        emby_group_target_str = format_ids(PUSHTARGET.GroupPushTarget.setdefault(TableName.EMBY.value, []))
        anirss_group_target_str = format_ids(PUSHTARGET.GroupPushTarget.setdefault(TableName.ANIRSS.value, []))
        logger.opt(colors=True).info(
            "<c>COMMAND</c>: 已成功获取推送用户")
        await get_push_user.finish(
            f"已成功获取推送用户\nEmby私聊推送目标:\n{emby_private_target_str}\n\nAniRSS私聊推送目标:\n{anirss_private_target_str}\n\nEmby群组推送目标:\n{emby_group_target_str}\n\nAniRSS群组推送目标:\n{anirss_group_target_str}")
    except FinishedException:
        raise
    except Exception as e:
        logger.opt(colors=True).error(f"<c>COMMAND</c>: 获取推送用户 <r>失败</r> —— {e}")
        await get_push_user.finish(f"获取推送用户失败 —— {e}")
