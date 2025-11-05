from click import group
from nonebot.exception import FinishedException
from nonebot import on_command, logger
from nonebot.matcher import Matcher
from nonebot.adapters.onebot.v11 import Message, GroupMessageEvent, PrivateMessageEvent
from nonebot.params import CommandArg
from nonebot_plugin_waiter import prompt, prompt_until
from ...utils import convert_db_list_first_row_to_dict
from ...config import FUNCTION
from ...mapping import TableName
from ...exceptions import AppError
from ...database import DatabaseOperator, schema_manager
from typing import Literal


subscribe = on_command(
    "订阅", aliases={"订阅动画", "订阅剧集", "订阅动漫", "订阅剧集", "订阅动漫剧集"})

remove_subscribe = on_command(
    "取消订阅", aliases={"取消订阅动画", "取消订阅剧集", "取消订阅动漫", "取消订阅剧集", "取消订阅动漫剧集"})


@subscribe.handle()
async def handle_subscribe(
        event: GroupMessageEvent | PrivateMessageEvent,
        matcher: Matcher,
        args: Message = CommandArg()):
    logger.opt(colors=True).info("<c>COMMAND</c>: 匹配命令 —— 订阅")
    if not FUNCTION.tmdb_enabled:
        logger.opt(colors=True).warning(
            "<y>COMMAND</y>: 未配置TMDB相关参数或TMDB功能未启用,无法订阅")
        await subscribe.finish("未配置TMDB相关参数或TMDB功能未启用,无法订阅")
    user_input = args.extract_plain_text().strip()
    if not user_input:
        logger.opt(colors=True).info("<c>COMMAND</c>: 未输入订阅名称,等待用户输入")
        user_input = await prompt(message="请输入要订阅的电影/动漫/剧集名称", timeout=60)
        if not user_input:
            logger.opt(colors=True).warning("<c>COMMAND</c>: 等待输入超时,对话已结束")
            await subscribe.finish("等待输入超时,对话已结束")
    try:
        subscribe_process = SubscribeProcess(user_input, event, matcher, "add")
        await subscribe_process.add_process()
    except FinishedException:
        pass
    except Exception as e:
        logger.opt(colors=True).error(
            f"<r>COMMAND</r>: 创建订阅处理器失败 —— {e} ")
        await subscribe.finish(f"订阅任务创建失败 —— {type(e).__name__}")


@remove_subscribe.handle()
async def handle_remove_subscribe(
        event: GroupMessageEvent | PrivateMessageEvent,
        matcher: Matcher,
        args: Message = CommandArg()):
    logger.opt(colors=True).info("<c>COMMAND</c>: 匹配命令 —— 取消订阅")
    if not FUNCTION.tmdb_enabled:
        logger.opt(colors=True).warning(
            "<y>COMMAND</y>: 未配置TMDB相关参数或TMDB功能未启用,无法取消订阅")
        await remove_subscribe.finish("未配置TMDB相关参数或TMDB功能未启用,无法取消订阅")
    user_input = args.extract_plain_text().strip()
    if not user_input:
        logger.opt(colors=True).info("<c>COMMAND</c>: 未输入取消订阅的对象,等待用户输入")
        user_input = await prompt(message="请输入要取消订阅的电影/动漫/剧集名称", timeout=60)
        if not user_input:
            logger.opt(colors=True).warning("<c>COMMAND</c>: 等待输入超时,对话已结束")
            await remove_subscribe.finish("等待输入超时,对话已结束")
    try:
        remove_subscribe_process = SubscribeProcess(
            user_input, event, matcher, "remove")
        await remove_subscribe_process.remove_process()
    except FinishedException:
        pass
    except Exception as e:
        logger.opt(colors=True).error(
            f"<r>COMMAND</r>: 创建取消订阅处理器失败 —— {e} ")
        await remove_subscribe.finish(f"取消订阅任务创建失败 —— {type(e).__name__}")


class SubscribeProcess:
    def __init__(self, title, event: GroupMessageEvent | PrivateMessageEvent, matcher: Matcher, choice_type: Literal["add", "remove"]):
        self.title = title
        self.user_choice = None
        self.event = event
        self.matcher = matcher
        self.tmdb_id = None
        self.db_operator = DatabaseOperator()
        self.choice_type: Literal["add", "remove"] = choice_type

    async def add_process(self):
        """
        处理订阅流程
        1. 从TMDB API搜索标题
        2. 显示搜索结果并等待用户选择
        3. 创建数据库订阅记录
        """
        try:
            total_results, extracted_data = await self._get_data_from_api()
        except FinishedException:
            raise
        except Exception as e:
            logger.opt(colors=True).error(
                f"<r>COMMAND</r>: 从TMDB API获取搜索结果失败 —— {e} ")
            await self.matcher.finish("订阅失败 —— 从TMDB API获取搜索结果出现错误")
        try:
            await self._wait_for_user_choice(total_results, extracted_data)
        except FinishedException:
            raise
        except Exception as e:
            logger.opt(colors=True).error(
                f"<r>COMMAND</r>: 等待用户选择订阅项失败 —— {e} ")
            await self.matcher.finish("订阅失败 —— 等待用户选择订阅项出现错误")
        try:
            db_item = await self._search_in_db()
        except FinishedException:
            raise
        except Exception as e:
            logger.opt(colors=True).error(
                f"<r>COMMAND</r>: 查询数据库失败 —— {e} ")
            await self.matcher.finish("订阅失败 —— 查询数据库出现错误")
        try:
            db_structured_data = await self._add_user_to_structured_data(db_item)
        except FinishedException:
            raise
        except Exception as e:
            logger.opt(colors=True).error(
                f"<r>COMMAND</r>: 创建数据库订阅记录失败 —— {e} ")
            await self.matcher.finish("订阅失败 —— 创建数据库订阅记录出现错误")
        try:
            await self._upsert_to_db(db_structured_data)
        except FinishedException:
            raise
        except Exception as e:
            logger.opt(colors=True).error(
                f"<r>COMMAND</r>: 更新数据库记录失败 —— {e} ")
            await self.matcher.finish("订阅失败 —— 更新数据库记录出现错误")
        if self.user_choice is None:
            await self.matcher.finish(f"订阅TMDB ID: {self.tmdb_id} 成功,更新时会通过您的订阅来源@通知你")
        await self.matcher.finish(f"订阅{extracted_data[self.user_choice - 1]['title']}(TMDB ID: {self.tmdb_id})成功,更新时会通过您的订阅来源@通知你")

    async def remove_process(self):
        try:
            total_results, extracted_data = await self._get_data_from_api()
        except FinishedException:
            raise
        except Exception as e:
            logger.opt(colors=True).error(
                f"<r>COMMAND</r>: 从TMDB API获取搜索结果失败 —— {e} ")
            await self.matcher.finish("订阅失败 —— 从TMDB API获取搜索结果出现错误")
        try:
            await self._wait_for_user_choice(total_results, extracted_data)
        except FinishedException:
            raise
        except Exception as e:
            logger.opt(colors=True).error(
                f"<r>COMMAND</r>: 等待用户选择取消订阅项失败 —— {e} ")
            await self.matcher.finish("取消订阅失败 —— 等待用户选择取消订阅项出现错误")
        try:
            db_item = await self._search_in_db()
        except FinishedException:
            raise
        except Exception as e:
            logger.opt(colors=True).error(
                f"<r>COMMAND</r>: 查询数据库失败 —— {e} ")
            await self.matcher.finish("取消订阅失败 —— 查询数据库出现错误")
        try:
            db_structured_data = await self._remove_user_from_structured_data(db_item)
        except FinishedException:
            raise
        except Exception as e:
            logger.opt(colors=True).error(
                f"<r>COMMAND</r>: 取消数据库订阅记录失败 —— {e} ")
            await self.matcher.finish("取消订阅失败 —— 取消数据库订阅记录出现错误")
        try:
            await self._upsert_to_db(db_structured_data)
        except FinishedException:
            raise
        except Exception as e:
            logger.opt(colors=True).error(
                f"<r>COMMAND</r>: 更新数据库记录失败 —— {e} ")
            await self.matcher.finish("取消订阅失败 —— 更新数据库记录出现错误")
        if self.user_choice is None:
            await self.matcher.finish(f"取消订阅TMDB ID: {self.tmdb_id}成功,更新时不会再通过您的订阅来源@通知您")
        await self.matcher.finish(f"取消订阅{extracted_data[self.user_choice - 1]['title']}(TMDB ID: {self.tmdb_id})成功,更新时不会再通过您的订阅来源@通知您")

    async def _get_data_from_api(self) -> tuple[int, list[dict]]:
        """
        从TMDB API获取搜索结果
        Returns:
            格式化后的搜索结果字典,包含total_results和extracted_data
        """
        api_result = await self._search_by_multi_api()
        return self._api_result_reformated(api_result)

    async def _search_by_multi_api(self) -> dict | None:
        from ...external import TmdbApiRequest
        return await TmdbApiRequest.search_by_multi(query=self.title)

    def _api_result_reformated(self, api_result: dict | None) -> tuple[int, list[dict]]:
        """
        格式化TMDB API返回结果
        Args:
            api_result: 原始API返回字典
        Returns:
            格式化后的字典,包含必要字段(title, type, tmdb_id)
        """
        if not api_result:
            AppError.MissingRequiredField.raise_("TMDB API返回数据为空")
        total_results = api_result.get("total_results", 0)
        if total_results == 0:
            return total_results, []
        extracted_data = [
            {
                "tmdb_id": item.get("id"),
                "type": item.get("media_type"),
                "title": item.get("title") or item.get("name"),
            }
            for item in api_result.get("results", [])[:5]
        ]
        return total_results, extracted_data

    async def _wait_for_user_choice(self, total_results: int, extracted_data: list[dict]) -> None:
        """
        等待用户选择订阅项
        Args:
            extracted_data: 格式化后的搜索结果列表

        """
        if total_results == 0:
            await self.matcher.finish("未找到匹配的动画/剧集,请检查名称是否正确")
        elif total_results == 1:
            self.tmdb_id = extracted_data[0]["tmdb_id"]
            if self.tmdb_id:
                id_input = 1
                if self.choice_type == "add":
                    await self.matcher.send(f"已确认{extracted_data[0]['title']}(TMDB ID: {self.tmdb_id}), 尝试添加到订阅列表...")
                elif self.choice_type == "remove":
                    await self.matcher.send(f"已确认{extracted_data[0]['title']}(TMDB ID: {self.tmdb_id}), 尝试从订阅列表移除...")
            else:
                AppError.UnknownError.raise_(
                    "TMDB API返回数据中缺少TMDB ID或TMDB ID处理异常")
        else:
            message_header = "| 序号 | 类型 | 标题 "
            separator = "|———|———|——————"
            message_body = "\n".join([
                f"| {i + 1} | {item['type']:-^6} | {item['title']}"
                for i, item in enumerate(extracted_data)
            ])
            message = f"{message_header}\n{separator}\n{message_body}"
            await self.matcher.send(message)
            if total_results > 5:
                id_input = await prompt_until(f"找到 {total_results} 个匹配项,仅显示前5项,请输入要选择的项序号：\n如没有对应项，请输入0结束对话\n然后重新输入更详细的名称进行查询",
                                              checker=lambda msg: (
                                                  text := msg.extract_plain_text()).isdigit() and 0 <= int(text) <= 5,
                                              matcher=self.matcher,
                                              timeout=60)
            else:
                id_input = await prompt_until(f"找到 {total_results} 个匹配项,请输入要选择的项序号：\n如没有对应项，请输入0结束对话\n然后重新输入更详细的名称进行查询",
                                              checker=lambda msg: (text := msg.extract_plain_text(
                                              )).isdigit() and 0 <= int(text) <= total_results,
                                              matcher=self.matcher,
                                              timeout=60)
            if not id_input:
                await self.matcher.finish("输入超时,对话已终止")
            id = int(id_input.extract_plain_text())
            if id == 0:
                await self.matcher.finish("已取消操作")
            if self.choice_type == "add":
                await self.matcher.send(f"已确认{extracted_data[id - 1]['title']}(TMDB ID: {extracted_data[id - 1]['tmdb_id']}), 尝试添加到订阅列表...")
            elif self.choice_type == "remove":
                await self.matcher.send(f"已确认{extracted_data[id - 1]['title']}(TMDB ID: {extracted_data[id - 1]['tmdb_id']}), 尝试从订阅列表移除...")
            self.tmdb_id = extracted_data[id - 1]["tmdb_id"]
            self.user_choice = id

    async def _search_in_db(self) -> dict:
        """
        从数据库中搜索指定TMDB ID的订阅项
        Args:
            tmdb_id: 要搜索的TMDB ID
        Returns:
            格式化后的数据库订阅项字典,如果未找到则返回None
        """
        try:
            db_result = await self.db_operator.select_data(table_name=TableName.ANIME,
                                                           where={
                                                               "tmdb_id": self.tmdb_id},
                                                           limit=1)
            if not db_result:
                if self.choice_type == "add":
                    await self.matcher.send("本地数据库中没有该动画/剧集的记录，新建记录中...")
                    db_structured_data = schema_manager.get_default_schema(
                        TableName.ANIME)
                    db_structured_data["tmdb_id"] = self.tmdb_id
                elif self.choice_type == "remove":
                    await self.matcher.finish("本地数据库中没有该动画/剧集的记录，没有需要移除的订阅，操作已取消")
            else:
                db_structured_data = convert_db_list_first_row_to_dict(
                    TableName.ANIME, db_result)
            return db_structured_data
        except FinishedException:
            raise
        except AppError.Exception:
            raise
        except Exception as e:
            AppError.UnknownError.raise_(f"查询数据库失败 —— {str(e)}")

    async def _add_user_to_structured_data(self, db_structured_data: dict):
        """
        添加订阅用户到格式化后的数据库订阅项字典中
        Args:
            db_structured_data: 格式化后的数据库订阅项字典
        Returns:
            更新后的格式化后的数据库订阅项字典
        """
        try:
            private_subscriber = db_structured_data.get(
                "private_subscriber", [])
            group_subscriber = db_structured_data.get("group_subscriber", {})
            if isinstance(self.event, GroupMessageEvent):
                if str(self.event.group_id) not in group_subscriber:
                    group_subscriber[str(self.event.group_id)] = [
                        str(self.event.user_id)]
                    db_structured_data["group_subscriber"] = group_subscriber
                else:
                    if str(self.event.user_id) not in group_subscriber[str(self.event.group_id)]:
                        group_subscriber[str(self.event.group_id)].append(
                            str(self.event.user_id))
                        db_structured_data["group_subscriber"] = group_subscriber
                    else:
                        await self.matcher.finish("你已订阅该动画/剧集, 无需重复订阅")
            elif isinstance(self.event, PrivateMessageEvent):
                if str(self.event.user_id) not in private_subscriber:
                    private_subscriber.append(str(self.event.user_id))
                    db_structured_data["private_subscriber"] = private_subscriber
                else:
                    await self.matcher.finish("你已订阅该动画/剧集, 无需重复订阅")
            else:
                await self.matcher.finish("异常的事件类型，无法添加订阅用户")
            return db_structured_data
        except FinishedException:
            raise
        except AppError.Exception:
            raise
        except Exception as e:
            AppError.UnknownError.raise_(f"添加订阅用户到数据库失败 —— {str(e)}")

    async def _upsert_to_db(self, db_structured_data: dict):
        """
        用更新后的格式化后的数据库订阅项字典替换数据库中的记录
        Args:
            db_structured_data: 更新后的格式化后的数据库订阅项字典
        """
        try:
            await self.db_operator.upsert_data(table_name=TableName.ANIME,
                                               data=db_structured_data,
                                               conflict_column="tmdb_id")
        except AppError.Exception:
            raise
        except Exception as e:
            AppError.UnknownError.raise_(f"更新数据库记录失败 —— {str(e)}")

    async def _remove_user_from_structured_data(self, db_structured_data: dict):
        """
        从格式化后的数据库订阅项字典中移除订阅用户
        Args:
            db_structured_data: 格式化后的数据库订阅项字典
        Returns:
            更新后的格式化后的数据库订阅项字典
        """
        try:
            private_subscriber = db_structured_data.get(
                "private_subscriber", [])
            group_subscriber = db_structured_data.get("group_subscriber", {})
            if isinstance(self.event, GroupMessageEvent):
                if str(self.event.group_id) in group_subscriber:
                    if str(self.event.user_id) in group_subscriber[str(self.event.group_id)]:
                        group_subscriber[str(self.event.group_id)].remove(
                            str(self.event.user_id))
                        db_structured_data["group_subscriber"] = group_subscriber
                    else:
                        await self.matcher.finish("你未订阅该动画/剧集, 无需取消订阅")
                else:
                    await self.matcher.finish("你未订阅该动画/剧集, 无需取消订阅")
            elif isinstance(self.event, PrivateMessageEvent):
                if str(self.event.user_id) in private_subscriber:
                    private_subscriber.remove(str(self.event.user_id))
                    db_structured_data["private_subscriber"] = private_subscriber
                else:
                    await self.matcher.finish("你未订阅该动画/剧集, 无需取消订阅")
            else:
                await self.matcher.finish("异常的事件类型，无法取消订阅用户")
            return db_structured_data
        except FinishedException:
            raise
        except AppError.Exception:
            raise
        except Exception as e:
            AppError.UnknownError.raise_(f"从数据库记录中移除订阅用户失败 —— {str(e)}")
