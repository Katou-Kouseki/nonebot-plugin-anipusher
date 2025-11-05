# -*- coding: utf-8 -*-
"""数据处理管理器模块
负责协调整个数据处理流程，包括数据源分析和处理器选择执行。
作为数据处理系统的核心协调器，接收原始数据，分析其来源，并选择合适的处理器进行处理。
"""

# 第三方库
from nonebot import logger
# 项目内部模块
from ...exceptions import AppError
from ...mapping import TableName
from .abstract_processor import AbstractDataProcessor


class DataProcessor:
    """数据处理协调类
    负责接收原始数据，分析数据来源，并协调相应的处理器执行数据处理任务。
    作为数据处理流程的调度中心，管理整个从数据接收到处理完成的生命周期。
    """

    def __init__(self, data):
        """初始化数据处理器
        Args:
            data: 待处理的原始数据，通常来自webhook或其他数据源
        """
        self.received_data = data
        self.source = None

    @classmethod
    async def create_and_execute(cls, data) -> 'DataProcessor':
        """创建并运行数据处理器的工厂方法
        这是处理流程的主入口点，创建处理器实例并启动主处理流程。
        Args:
            data: 待处理的原始数据
        Returns:
            DataProcessor: 创建的处理器实例
        """
        instance = cls(data)
        await instance.main_process()
        return instance

    def source_analysis(self):
        """分析数据源
        根据数据的特征判断其来源类型，返回对应的TableName枚举值。
        当前实现通过检查数据中的关键字段来确定来源。
        Returns:
            TableName: 数据来源对应的枚举值
        Raises:
            AppError.InvalidParameter: 当数据格式无效或为空时
            AppError.UnknownError: 当无法识别数据来源时
        """
        # 简单示例：根据数据内容判断来源
        if not isinstance(self.received_data, dict):
            AppError.InvalidParameter.raise_(
                "数据来源解析失败 —— WEBHOOK数据格式与期望格式 DICT 不符 ")
        if not self.received_data:
            AppError.InvalidParameter.raise_(
                "数据来源解析失败 —— WEBHOOK数据为空")
        analyze_key = next(iter(self.received_data), None)  # 避免StopIteration
        if not analyze_key:
            AppError.InvalidParameter.raise_(
                "数据来源解析失败 —— 没有可分析的字段")
        # 基于分析出的字段，给出对应的解析器
        if analyze_key.lower() == 'title':
            return TableName.EMBY
        elif analyze_key.lower() == 'ani':
            return TableName.ANIRSS
        else:
            AppError.UnknownError.raise_(
                f"数据来源解析失败 —— 未知来源：{analyze_key}")

    async def main_process(self):
        """主处理流程
        执行完整的数据处理流程：先分析数据源，然后选择并执行对应的处理器。
        包含异常处理机制，确保单个处理任务失败不会影响整个系统。
        """
        try:
            # 步骤1：分析数据源
            self.source = self.source_analysis()
            logger.opt(colors=True).info(
                f"数据源分析 <g>SUCCESS</g> 来源: <g>{self.source.value}</g>")
        except AppError.Exception as e:
            # 数据源分析失败，记录错误并退出处理
            logger.opt(colors=True).error(
                f"数据源分析 <r>FAIL</r> —— {e}")
            return
        try:
            # 步骤2：验证数据源不为None
            if self.source is None:
                AppError.MissingParameter.raise_(
                    "指定数据处理器 FAIL —— source未被正确设置")
            # 步骤3：选择对应的处理器
            processor = await AbstractDataProcessor.select_processor(
                self.received_data, self.source)
            if not processor:
                AppError.MissingParameter.raise_(
                    f"指定数据处理器 FAIL —— 未找到{self.source.value} 对应的处理器")
            # 步骤4：执行数据处理
        except AppError.Exception as e:
            # 处理过程中发生任何异常，记录错误并退出
            logger.opt(colors=True).error(f"{e}")
            return
        except Exception as e:
            logger.opt(colors=True).error(
                f"指定数据处理器 <r>FAIL</r> —— 未知错误：{e}")
            return
        try:
            await processor.execute()
        except Exception:
            return
        finally:
            logger.opt(colors=True).info("————————————— 等待下一条数据 —————————————")
