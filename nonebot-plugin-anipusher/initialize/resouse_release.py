import shutil
from nonebot import logger
from pathlib import Path
from ..config import WORKDIR
from ..exceptions import AppError
"""
资源复制模块
此模块负责应用程序资源文件的管理、复制和更新，确保应用程序运行时能够正确访问所需的资源文件。
主要功能包括：
- 将源代码中的资源文件复制到应用程序的工作目录
- 处理资源文件的覆盖和更新逻辑
- 提供统一的错误处理和日志记录

# 基本调用方式
from new_anipusher.init.res import ResourceCopier
# 在应用程序初始化阶段调用
try:
    ResourceCopier.copy_resources()
    print("资源文件释放成功")
except Exception as e:
    print(f"资源文件释放失败: {e}")
    # 根据实际情况决定是否继续运行程序或退出
"""


class ResourceCopier:
    """
    资源复制器类，负责将源代码中的资源文件复制到应用程序的工作目录
    该类专注于单一职责：将源代码中的资源文件复制到应用程序的工作目录中，
    并处理目标目录已存在时的覆盖逻辑。
    """
    @classmethod
    def copy_resources(cls) -> None:
        """释放资源文件至工作目录
        将源代码中的资源文件复制到应用程序的缓存目录中，
        如果目标目录已存在，则先删除再复制，确保资源文件是最新的。
        Raises:
            AppError.ResourceNotFound: 当源代码中的资源目录不存在时
            AppError.MissingParameter: 当缓存目录参数缺失时
            AppError.UnknownError: 当资源复制过程中发生其他错误时
        """
        # 获取源资源目录路径
        source_dir = Path(__file__).resolve().parents[1] / "res"
        # 检查源资源目录是否存在
        if not source_dir.is_dir():
            AppError.ResourceNotFound.raise_(f"资源目录res缺失 —— 路径:{source_dir}不存在")
        # 检查缓存目录参数是否设置
        if not WORKDIR.cache_dir:
            AppError.MissingParameter.raise_("缓存目录路径缺失 —— 参数WORKDIR.cache_dir未成功设置")
        if not WORKDIR.message_template_dir:
            AppError.MissingParameter.raise_("默认消息模板目录路径缺失 —— 参数WORKDIR.message_template_dir未成功设置")
        # 确保工作目录存在并设置目标资源目录
        WORKDIR.cache_dir.mkdir(parents=True, exist_ok=True)
        WORKDIR.message_template_dir.mkdir(parents=True, exist_ok=True)
        default_image_path = source_dir / "default_img.png"
        message_template_path = source_dir / "default_template.yaml"
        if not default_image_path.exists():
            AppError.ResourceNotFound.raise_("默认图片缺失 —— 请检查项目资源目录下是否有default_img.png文件")
        if not message_template_path.exists():
            AppError.ResourceNotFound.raise_("默认消息模板缺失 —— 请检查项目资源目录下是否有message_template.yaml文件")
        # 执行资源文件复制操作
        try:
            # 复制资源文件到目标目录
            shutil.copy(default_image_path, WORKDIR.cache_dir / "default_img.png")
            shutil.copy(message_template_path, WORKDIR.message_template_dir / "default_template.yaml")
        except Exception as e:
            AppError.ResourceCopyError.raise_(f"{e}")
