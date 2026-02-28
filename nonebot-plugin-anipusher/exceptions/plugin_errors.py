
from enum import Enum
from typing import NoReturn
from pathlib import Path
import inspect

"""
应用程序统一错误处理模块

本模块定义了应用程序中所有可能发生的错误类型，采用枚举方式统一管理错误代码和描述信息，
提供一致的异常抛出和捕获机制。

错误分类体系：
├── 系统错误 (1000-1999): 系统级错误和通用错误
├── 数据库错误 (2000-2999): 数据存储和访问相关错误
├── 网络请求错误 (3000-3999): 外部服务调用相关错误
├── 推送错误 (4000-4999): 消息推送相关错误
└── 未来扩展: 可根据需要添加新的错误类别

错误代码结构：
- 格式：XXXX (四位数字)
- 第一位：错误类别标识
- 后三位：具体错误编码

使用示例：
    # 抛出异常
    AppError.FileIOError.raise_("文件不存在")

    # 捕获异常
    try:
        AppError.UnknownError.raise_("未知错误")
    except AppError.Exception as e:
        print(f"错误码: {e.error_code.code}")
        print(f"错误信息: {e.error_code.msg}")
        print(f"额外信息: {e.extra_msg}")
"""


class AppError(Enum):
    """应用程序错误代码枚举类

    错误代码分类说明:
    - 系统错误 (1000-1999): 系统级错误和通用错误
    - 数据库错误 (2000-2999): 数据库相关错误
    - 网络请求错误 (3000-3999): 外部服务调用相关错误
    错误代码格式: XXXX (四位数字)
    - 第一位数字表示错误类型分类
    - 后三位数字表示具体错误标识
    """

    # 系统错误 (1000-1999) - 仅保留实际使用的错误码
    UnknownError = (1000, "未知错误")
    InvalidConfiguration = (1002, "配置无效")
    MissingConfiguration = (1003, "缺少必要配置")
    ValidationError = (1005, "数据验证失败")
    InvalidParameter = (1006, "参数无效")
    MissingParameter = (1007, "缺少必要参数")
    EmptyParameter = (1008, "参数为空")
    MissingRequiredField = (1014, "缺少必要字段")  # 新增：用于参数中缺少必要的字段或属性
    ResourceNotFound = (1009, "资源未找到")
    PermissionDenied = (1010, "权限不足")
    FileIOError = (1012, "文件读写错误")
    DataConversionError = (1015, "数据转换失败")  # 新增：用于数据格式转换失败的场景
    ResourceCopyError = (1016, "资源复制失败")  # 新增：用于资源文件复制操作失败
    ImageConversionError = (1017, "图片转换失败")  # 新增：用于图片格式转换或编码失败
    ConfigFileReadError = (1018, "配置文件读取失败")  # 新增：用于配置文件读取错误
    ConfigFileResetError = (1019, "配置文件重置失败")  # 新增：用于配置文件重置错误
    MessageRenderError = (1020, "消息渲染失败")  # 新增：用于消息模板渲染错误
    ApiRequestError = (1021, "API请求失败")  # 新增：用于外部API请求错误
    FeatureNotEnabled = (1022, "功能未启用")  # 新增：用于功能未启用的场景

    # 数据库错误 (2000-2999) - 仅保留实际使用的错误码
    DatabaseConnectionFailed = (2000, "数据库连接失败")
    DatabaseTransactionError = (2002, "数据库事务错误")
    DatabaseQueryError = (2001, "数据库查询失败")  # 新增：用于数据库查询操作失败
    DatabaseUpsertError = (2003, "数据库插入更新失败")  # 新增：用于数据库插入或更新操作失败
    SqlGenerationError = (2004, "SQL语句生成失败")  # 新增：用于SQL语句生成错误
    DatabaseTimeout = (2005, "数据库操作超时")
    TableStructureError = (2006, "表结构获取失败")  # 新增：用于表结构获取错误
    SchemaGenerationError = (2007, "数据结构生成失败")  # 新增：用于数据结构生成错误

    # 网络请求错误 (3000-3999) - 仅保留实际使用的错误码
    NetworkConnectionFailed = (3000, "网络连接失败")
    InvalidHttpResponse = (3003, "无效的HTTP响应")

    # 推送错误 (4000-4999) - 新增推送相关错误码
    MessageParameterGenerateError = (4001, "消息参数生成失败")  # 新增：用于消息参数生成失败
    ImageSelectorCreateError = (4002, "图片选择器创建失败")  # 新增：用于图片选择器创建失败
    TmdbIdFetchError = (4003, "TMDB ID获取失败")  # 新增：用于TMDB ID获取失败
    PushTargetMergeError = (4004, "推送目标合并失败")  # 新增：用于合并推送目标失败
    SendStatusUpdateError = (4005, "发送状态更新失败")  # 新增：用于更新发送状态失败
    ImageDownloadTaskError = (4006, "图片下载任务创建失败")  # 新增：用于图片下载任务创建失败

    @property
    def code(self):
        """获取状态码"""
        return self.value[0]

    @property
    def msg(self):
        """获取状态描述"""
        return self.value[1]

    def __str__(self):
        """字符串表示"""
        return f"[{self.code}] {self.msg}"

    @classmethod
    def get_by_code(cls, code):
        """根据状态码获取枚举项"""
        for member in cls:
            if member.code == code:
                return member
        return None

    def raise_(self, extra_msg: str = "") -> NoReturn:
        """抛出此错误对应的异常
            并记录错误日志
        """
        error = self.Exception(self, extra_msg)
        self._log_error(error)
        raise error

    @staticmethod
    def _log_error(error: 'AppError.Exception') -> None:
        """记录错误日志"""
        from ..utils.dates import get_iso8601_timestamp
        log_dir = Path("anipusher_errors.log")
        log_dir.parent.mkdir(exist_ok=True)
        # 获取调用栈信息（排除日志记录部分）
        stack = "\n".join(
            f"  File \"{frame.filename}\", line {frame.lineno}, in {frame.function}"
            for frame in inspect.stack()[2:])  # 跳过日志记录调用栈)
        log_msg = (
            f"\n时间: {get_iso8601_timestamp()}\n"
            f"错误码: {error.error_code.code}\n"
            f"类型: {error.error_code.name}\n"
            f"描述: {error.error_code.msg}\n"
            f"详情: {error.extra_msg}\n"
            f"调用栈:\n{stack}\n\n"
            "────────────────────\n")
        try:
            with open(log_dir, "a", encoding="utf-8") as f:
                f.write(log_msg)
        except Exception as e:
            print(f"日志记录失败: {e}")

class _AppException(Exception):
    def __init__(self, error_code: 'AppError', extra_msg: str = ""):
        self.error_code = error_code
        self.extra_msg = extra_msg
        super().__init__(f"{error_code.msg} {extra_msg}".strip())

    def __str__(self):
        return f"[{self.error_code.code}] {super().__str__()}"

AppError.Exception = _AppException
