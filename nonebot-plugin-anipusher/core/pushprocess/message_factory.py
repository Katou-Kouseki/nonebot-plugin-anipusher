
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
"""

# 第三方库
import yaml
from pathlib import Path
from typing import Optional
from nonebot import logger
from nonebot.adapters.onebot.v11 import Message, MessageSegment
# 项目内部模块
from ...config import WORKDIR
from ...exceptions import AppError


class MessageRenderer:
    """
    消息渲染工厂类，用于将YAML模板渲染成可发送的消息
    支持多种消息类型的渲染，包括静态文本、图片、动态内容和@用户等，
    并提供灵活的模板配置和数据替换功能。
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
            # 获取模板列表
            template_items = self.template_config.get("template", [])
            if not template_items:
                AppError.MissingConfiguration.raise_("消息模板文件中未定义任何模板项")
            # 对模板项按权重排序
            sorted_items = sorted(
                template_items, key=lambda x: x.get("weight", 0))
            # 渲染消息行
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
            # 获取模板列表
            template_items = self.template_config.get("template", [])
            if not template_items:
                AppError.MissingConfiguration.raise_("消息模板文件中未定义任何模板项")
            # 对模板项按权重排序
            sorted_items = sorted(
                template_items, key=lambda x: x.get("weight", 0))
            # 渲染消息行，但跳过at类型的消息行
            rendered_message = Message()
            for item in sorted_items:
                # 跳过at类型的消息行
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
            # 获取模板列表
            template_items = self.template_config.get("template", [])
            if not template_items:
                AppError.MissingConfiguration.raise_("消息模板文件中未定义任何模板项")
            # 对模板项按权重排序
            sorted_items = sorted(
                template_items, key=lambda x: x.get("weight", 0))
            # 只渲染at类型的消息行
            rendered_message = Message()
            for item in sorted_items:
                # 只处理at类型的消息行
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
        content = template.get("content")  # 静态消息内容或动态消息字段
        field = template.get("field")  # 动态消息字段
        type = template.get("type")  # 消息类型
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
            placeholder = f"{{{field}}}"  # 占位符配置
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
