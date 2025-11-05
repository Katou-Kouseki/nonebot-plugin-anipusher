from ..exceptions import AppError
from nonebot import logger


def generate_emby_series_url(host: str | None, series_id: str | None, server_id: str | None):
    """
    生成Emby系列的URL链接
    Args:
        host: Emby服务器主机地址
        series_id: 系列ID
        server_id: 服务器ID
    Returns:
        生成的URL字符串
    Raises:
        AppError.UnknownError: 未知错误
    """
    # 参数验证
    if not host:
        logger.opt(colors=True).warning("<r>LinkGeneration</r>: 生成EMBY链接失败 —— 主机地址(host)为空或无效")
        return None
    if not series_id:
        logger.opt(colors=True).warning("<r>LinkGeneration</r>: 生成EMBY链接失败 —— 系列ID(series_id)为空或无效")
        return None
    if not server_id:
        logger.opt(colors=True).warning("<r>LinkGeneration</r>: 生成EMBY链接失败 —— 服务器ID(server_id)为空或无效")
        return None
    # 参数类型验证和转换（确保是字符串类型）
    host = str(host).strip()
    series_id = str(series_id).strip()
    server_id = str(server_id).strip()
    try:
        return f"{host.rstrip('/')}/web/index.html#!/item?id={series_id}&serverId={server_id}"
    except Exception as e:
        AppError.UnknownError.raise_(f"生成EMBY链接失败: {str(e)}")


def generate_emby_image_url(host: str | None, series_id: str | None, tag: str | None):
    """
    生成Emby系列的图片URL链接
    Args:
        host: Emby服务器主机地址
        series_id: 系列ID
        tag: 图片标签
    Returns:
        生成的URL字符串
    Raises:
        AppError.UnknownError: 未知错误
    """
    # 参数验证
    if not host:
        logger.opt(colors=True).warning("<r>LinkGeneration</r>: 生成EMBY图片链接失败 —— 主机地址(host)为空")
        return None
    if not series_id:
        logger.opt(colors=True).warning("<r>LinkGeneration</r>: 生成EMBY图片链接失败 —— 系列ID(series_id)为空")
        return None
    if not tag:
        logger.opt(colors=True).warning("<r>LinkGeneration</r>: 生成EMBY图片链接失败 —— 图片标签(tag)为空")
        return None
    try:
        host = str(host).strip()
        series_id = str(series_id).strip()
        tag = str(tag).strip()
        return f"{host.rstrip('/')}/emby/Items/{series_id}/Images/Primary?tag={tag}&quality=90"
    except Exception as e:
        AppError.UnknownError.raise_(f"生成EMBY图片链接失败: {str(e)}")
