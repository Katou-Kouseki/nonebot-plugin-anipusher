from pathlib import Path
from nonebot import logger
import importlib
import sys


class ProcessorImport:
    def __init__(self):
        pass

    @classmethod
    async def import_processors(cls):
        """
        扫描项目文件夹，动态导入所有模块并查找 AbstractDataProcessor 的子类
        Returns:
            list[type[AbstractDataProcessor]]: 找到的所有子类列表
        Raises:
            AppError: 如果基类无效或导入过程中发生严重错误
        """
        # 获取项目根目录
        plugin_root = Path(__file__).resolve().parent.parent
        project_root = plugin_root.parent
        # 将项目根目录添加到Python路径（如果还没有）
        if str(project_root) not in sys.path:
            sys.path.append(str(project_root))

        # 设置处理器目录为core/dataprocess/processor
        processor_dir = plugin_root / "core" / "dataprocess" / "processor"
        if not processor_dir.is_dir():
            logger.opt(colors=True).error(
                f"<r>HealthCheck</r>:处理器目录 {processor_dir} 不存在")
            return False

        successed_module: list[str] = []
        error_module: list[str] = []

        # 遍历处理器目录中的所有Python文件
        for file in processor_dir.glob("*.py"):
            # 跳过__init__.py和以下划线开头的文件
            if file.name == "__init__.py" or file.name.startswith("_"):
                continue
            try:
                # 动态获取当前插件的顶层包名，以兼容任何文件夹名称或运行环境
                package_root = __name__.split('.')[0]
                module_name = f"{package_root}.core.dataprocess.processor.{file.stem}"
                # 动态导入模块，这会触发装饰器的执行
                importlib.import_module(module_name)
                successed_module.append(module_name)
            except ImportError as e:
                logger.opt(colors=True).warning(
                    f"<y>HealthCheck</y>:处理器模块导入失败: <r>{file.name}</r> —— {str(e)}")
                error_module.append(module_name)
            except Exception as e:
                logger.opt(colors=True).warning(
                    f"<y>HealthCheck</y>:处理模块时发生错误: <r>{file.name}</r> —— {str(e)}")
                error_module.append(module_name)
        if successed_module:
            # 提取文件名部分（不包含包路径）用于日志显示
            file_names = [module_name.split('.')[-1] for module_name in successed_module]
            error_file_names = [module_name.split('.')[-1] for module_name in error_module]
            logger.opt(colors=True).info(
                f"<g>HealthCheck</g>:{len(successed_module)}个数据处理器被加载 <c>{', '.join(file_names)}</c>")
            if error_module:
                logger.opt(colors=True).warning(
                    f"<y>HealthCheck</y>:{len(error_module)}个处理器模块加载失败 {', '.join(error_file_names)}")
            return True
        else:
            logger.opt(colors=True).error(
                "<r>HealthCheck</r>:未成功导入任何处理器模块")
            return False
