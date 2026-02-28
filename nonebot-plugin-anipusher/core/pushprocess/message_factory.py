
# -*- coding: utf-8 -*-
"""
消息工厂模块 - 负责消息模板渲染与构建
此模块提供MessageRenderer类，用于将YAML模板渲染成可发送的消息。
主要功能包括：
1. 模板加载与解析
2. 动态数据替换
3. 条件渲染
4. 消息长度限制
5. 空行处理
6. 支持静态文本、图片、动态内容和@用户等多种消息类型
7. 支持合并推送消息渲染
"""

import yaml
from pathlib import Path
from typing import Optional
from nonebot import logger
from nonebot.adapters.onebot.v11 import Message, MessageSegment
from ...config import WORKDIR
from ...exceptions import AppError


class MessageRenderer:
    """
    消息渲染工厂类，用于将YAML模板渲染成可发送的消息
    支持多种消息类型的渲染，包括静态文本、图片、动态内容和@用户等，
    并提供灵活的模板配置和数据替换功能。
    支持合并推送消息的渲染。
    """

    def __init__(self, template_path: Optional[Path] = None):
        """
        初始化消息渲染工厂类
        Args:
            template_path: 消息模板文件路径，若为None则使用默认模板
        Raises:
            AppError.ResourceNotFound: 当默认模板目录或文件不存在时
        """
        if template_path is None:
            if not WORKDIR.message_template_dir:
                AppError.ResourceNotFound.raise_(
                    "消息模板目录未配置")
            if not WORKDIR.message_template_dir.exists():
                AppError.ResourceNotFound.raise_(
                    f"消息模板目录不存在 —— {WORKDIR.message_template_dir}")
            if not (WORKDIR.message_template_dir / "default_template.yaml").exists():
                AppError.ResourceNotFound.raise_(
                    f"默认消息模板文件不存在 —— {WORKDIR.message_template_dir / 'default_template.yaml'}")
            self.template_path = WORKDIR.message_template_dir / "default_template.yaml"
        else:
            self.template_path = template_path
        self.template_config = self._load_template()

    def _load_template(self) -> dict:
        """
        加载并解析YAML模板文件
        Returns:
            dict: 解析后的模板配置字典
        Raises:
            AppError.ResourceNotFound: 当模板文件不存在时
            AppError.ConfigParseError: 当模板文件解析失败时
        """
        try:
            with open(self.template_path, "r", encoding="utf-8") as f:
                template_config = yaml.safe_load(f)
        except FileNotFoundError as e:
            AppError.ResourceNotFound.raise_(
                f"消息模板文件不存在 —— {e}")
        except yaml.YAMLError as e:
            AppError.UnknownError.raise_(
                f"消息模板文件解析错误 —— {e}")
        return template_config

    def render_all(self, data: dict) -> Message:
        """
        渲染完整消息模板，包括所有类型的消息内容
        Args:
            data: 包含替换变量的字典，用于填充模板中的占位符
        Returns:
            Message: 渲染后的可发送消息对象
        Raises:
            AppError.MissingConfiguration: 当模板文件中未定义任何模板项时
            AppError.MessageRenderError: 当消息渲染失败时
        """
        try:
            template_items = self.template_config.get("template", [])
            if not template_items:
                AppError.MissingConfiguration.raise_("消息模板文件中未定义任何模板项")
            sorted_items = sorted(
                template_items, key=lambda x: x.get("weight", 0))
            rendered_message = Message()
            for _, item in enumerate(sorted_items):
                try:
                    line = self._line_render(item, data)
                    if line is not None:
                        rendered_message += line
                except Exception as e:
                    logger.opt(colors=True).warning(
                        f"RENDER:渲染消息行时出错 —— {e}")
                    continue
            if rendered_message and str(rendered_message).endswith("\n"):
                rendered_message = Message(str(rendered_message).rstrip("\n"))
            return rendered_message
        except AppError.Exception:
            raise
        except Exception as e:
            AppError.MessageRenderError.raise_(f"{e}")

    def render_merged(self, data: dict) -> Message:
        """
        渲染合并推送消息模板
        当同一作品的多个剧集合并推送时使用此方法
        Args:
            data: 包含替换变量的字典，必须包含以下合并推送专用字段：
                - episode_count: 集数
                - episode_range: 集数范围显示（如 E01-E12）
                - season: 季数
        Returns:
            Message: 渲染后的可发送消息对象
        Raises:
            AppError.MissingConfiguration: 当模板文件中未定义合并推送模板时
            AppError.MessageRenderError: 当消息渲染失败时
        """
        try:
            merged_template = self.template_config.get("merged_template", [])
            if not merged_template:
                logger.opt(colors=True).warning(
                    "<y>RENDER</y>:未定义合并推送模板，使用默认模板")
                return self._render_merged_default(data)
            sorted_items = sorted(
                merged_template, key=lambda x: x.get("weight", 0))
            rendered_message = Message()
            for item in sorted_items:
                try:
                    line = self._line_render_merged(item, data)
                    if line is not None:
                        rendered_message += line
                except Exception as e:
                    logger.opt(colors=True).warning(
                        f"<y>RENDER</y>:渲染合并消息行时出错 —— {e}")
                    continue
            if rendered_message and str(rendered_message).endswith("\n"):
                rendered_message = Message(str(rendered_message).rstrip("\n"))
            return rendered_message
        except AppError.Exception:
            raise
        except Exception as e:
            AppError.MessageRenderError.raise_(f"合并消息渲染失败: {e}")

    def _render_merged_default(self, data: dict) -> Message:
        """
        渲染默认合并推送消息
        当YAML模板中未定义合并推送模板时使用
        Args:
            data: 包含替换变量的字典
        Returns:
            Message: 渲染后的消息对象
        """
        message = Message()
        if data.get("image"):
            from ...utils import convert_image_path_to_base64
            base64_image = convert_image_path_to_base64(data["image"])
            message.append(MessageSegment.image(base64_image))
        if data.get("title"):
            message.append(MessageSegment.text(f"🎬 {data['title']}\n"))
        episode_count = data.get("episode_count", 0)
        episode_range = data.get("episode_range", "")
        season = data.get("season", "1")
        if episode_count and episode_range:
            message.append(MessageSegment.text(
                f"✨第 {season} 季 更新 {episode_count} 集 ({episode_range})\n"))
        if data.get("timestamp"):
            message.append(MessageSegment.text(f"⏱️ 更新时间：{data['timestamp']}\n"))
        if data.get("action"):
            message.append(MessageSegment.text(f"🔔 推送类型：{data['action']}\n"))
        if data.get("score"):
            message.append(MessageSegment.text(f"🔢 目前评分：{data['score']}\n"))
        if str(message).endswith("\n"):
            message = Message(str(message).rstrip("\n"))
        return message

    def render_base(self, data: dict) -> Message:
        """
        渲染除@用户部分外的基础消息内容
        Args:
            data: 包含替换变量的字典，用于填充模板中的占位符
        Returns:
            Message: 渲染后的基础消息对象（不包含@用户内容）
        Raises:
            AppError.MissingConfiguration: 当模板文件中未定义任何模板项时
            AppError.MessageRenderError: 当基础消息渲染失败时
        """
        try:
            template_items = self.template_config.get("template", [])
            if not template_items:
                AppError.MissingConfiguration.raise_("消息模板文件中未定义任何模板项")
            sorted_items = sorted(
                template_items, key=lambda x: x.get("weight", 0))
            rendered_message = Message()
            for item in sorted_items:
                if item.get("type") == "at":
                    continue
                try:
                    line = self._line_render(item, data)
                    if line is not None:
                        rendered_message += line
                except Exception as e:
                    logger.opt(colors=True).warning(
                        f"<y>RENDER</y>:渲染基础消息行时出错 —— {e}")
                    continue
            if rendered_message and str(rendered_message).endswith("\n"):
                rendered_message = Message(str(rendered_message).rstrip("\n"))
            return rendered_message
        except AppError.Exception:
            raise
        except Exception as e:
            AppError.MessageRenderError.raise_(f"基础消息渲染失败: {e}")

    def render_at(self, data: dict) -> Message:
        """
        专门渲染@用户部分的消息内容
        Args:
            data: 包含替换变量的字典，必须包含at字段，存储需要@的用户列表
        Returns:
            Message: 渲染后的@用户消息对象
        Raises:
            AppError.MissingConfiguration: 当模板文件中未定义任何模板项时
            AppError.MessageRenderError: 当@消息渲染失败时
        """
        try:
            template_items = self.template_config.get("template", [])
            if not template_items:
                AppError.MissingConfiguration.raise_("消息模板文件中未定义任何模板项")
            sorted_items = sorted(
                template_items, key=lambda x: x.get("weight", 0))
            rendered_message = Message()
            for item in sorted_items:
                if item.get("type") == "at":
                    try:
                        line = self._line_render(item, data)
                        if line is not None:
                            rendered_message += line
                    except Exception as e:
                        logger.opt(colors=True).warning(
                            f"<y>RENDER</y>:渲染at消息行时出错 —— {e}")
                        continue
            return rendered_message
        except AppError.Exception:
            raise
        except Exception as e:
            AppError.MessageRenderError.raise_(f"at消息渲染失败: {e}")

    def _line_render(self, template: dict, data: dict | None) -> MessageSegment | Message | None:
        """
        渲染单条消息行，支持多种消息类型的渲染
        Args:
            item: 消息行配置项，包含content、field、type等字段
            data: 包含替换变量的字典，用于填充动态内容
        Returns:
            MessageSegment | Message | None: 渲染后的消息段或消息对象，
                                           当动态字段数据不存在时返回None
        Raises:
            AppError.MissingParameter: 当缺少必要参数或占位符不匹配时
        """
        content = template.get("content")
        field = template.get("field")
        type = template.get("type")
        if not content:
            AppError.MissingParameter.raise_("没有可渲染的消息内容")
        if not type:
            AppError.MissingParameter.raise_("消息字段类型不能为空")
        if type != "static":
            if not field:
                AppError.MissingParameter.raise_("消息模板中未提供图片对应字段名")
            elif field not in data:
                AppError.MissingParameter.raise_(
                    f"未生成模板字段 <c>{field}</c> 对应数据")
            placeholder = f"{{{field}}}"
            if placeholder not in content:
                AppError.MissingParameter.raise_(
                    f"模板中未提供占位符 <c>{placeholder}</c> 请检查模板配置")
        if type == "static":
            return MessageSegment.text(content + "\n")
        elif type == "image":
            img_path = (data or {}).get(field)
            if not img_path:
                AppError.MissingParameter.raise_(f"未找到可用的图片字段 <c>{field}</c>")
            from ...utils import convert_image_path_to_base64
            base64_image = convert_image_path_to_base64(img_path)
            return MessageSegment.image(base64_image)
        elif type == "dynamic":
            filler = (data or {}).get(field)
            if not filler:
                logger.opt(colors=True).warning(
                    f"<y>RENDER</y>:没有找到字段 <c>{field}</c> 所需数据 —— 跳过该字段渲染")
                return None
            rendered_content = content.replace(
                f"{{{field}}}", str((data or {})[field]))
            return MessageSegment.text(rendered_content + "\n")
        elif type == "at":
            at_message = Message()
            placeholder = f"{{{field}}}"
            if placeholder not in content:
                AppError.MissingParameter.raise_(
                    f"模板中未提供占位符 <c>{placeholder}</c> 请检查模板配置")
            at_list = (data or {}).get(field) or []
            if at_list:
                at_message.append(MessageSegment.text(
                    "\n" + content.rstrip(placeholder)))
                for user in at_list:
                    at_message.append(MessageSegment.at(user))
            return at_message

    def _line_render_merged(self, template: dict, data: dict | None) -> MessageSegment | Message | None:
        """
        渲染合并推送的单条消息行
        支持合并推送专用字段：episode_count, episode_range, season
        Args:
            template: 消息行配置项
            data: 包含替换变量的字典
        Returns:
            MessageSegment | Message | None: 渲染后的消息段或消息对象
        """
        content = template.get("content")
        field = template.get("field")
        type = template.get("type")
        if not content:
            return None
        if not type:
            return None
        if type == "static":
            return MessageSegment.text(content + "\n")
        elif type == "image":
            img_path = (data or {}).get(field)
            if not img_path:
                return None
            from ...utils import convert_image_path_to_base64
            base64_image = convert_image_path_to_base64(img_path)
            return MessageSegment.image(base64_image)
        elif type == "dynamic":
            if not field:
                return None
            filler = (data or {}).get(field)
            if not filler:
                logger.opt(colors=True).debug(
                    f"<y>RENDER</y>:合并推送没有找到字段 <c>{field}</c> —— 跳过")
                return None
            rendered_content = content.replace(f"{{{field}}}", str(filler))
            return MessageSegment.text(rendered_content + "\n")
        elif type == "merged_episode":
            episode_count = (data or {}).get("episode_count", 0)
            episode_range = (data or {}).get("episode_range", "")
            season = (data or {}).get("season", "1")
            if episode_count and episode_range:
                formatted_text = content.replace(
                    "{season}", str(season)
                ).replace(
                    "{episode_count}", str(episode_count)
                ).replace(
                    "{episode_range}", episode_range
                )
                return MessageSegment.text(formatted_text + "\n")
            return None
        elif type == "at":
            at_message = Message()
            at_list = (data or {}).get(field) or []
            if at_list:
                at_message.append(MessageSegment.text("\n📣 通知："))
                for user in at_list:
                    at_message.append(MessageSegment.at(user))
            return at_message
        return None
