import aiohttp

"""
HTTP请求模块

此模块提供了异步HTTP请求相关的工具函数,主要封装了aiohttp库的常用功能
提供更简洁的API接口用于发送HTTP请求并处理响应
支持设置请求头、URL参数、代理、超时等选项
"""


async def get_request(url: str,
                      headers: dict | None = None,
                      params: dict | None = None,
                      proxy: str | None = None,
                      is_binary: bool = False,
                      timeout: aiohttp.ClientTimeout | None = None
                      ) -> bytes | str:
    """发送异步HTTP GET请求
    封装aiohttp的GET请求方法,提供更便捷的API,并处理常见的请求配置和响应处理。
    Args:
        url (str): 请求的URL地址
        headers (dict | None): 请求头字典,如果为None则不设置额外请求头
        params (dict | None): URL查询参数,如果为None则不设置额外参数
        proxy (str | None): 代理服务器地址,如果为None则不使用代理
        is_binary (bool): 是否以二进制方式返回响应内容
                          True: 返回bytes(适用于图片、文件等二进制数据)
                          False: 返回str(适用于文本、JSON等字符串数据)
        timeout (aiohttp.ClientTimeout | None): 请求超时配置,如果为None则使用默认超时

    Returns:
        bytes | str: 根据is_binary参数决定返回bytes或str类型的响应内容

    Raises:
        aiohttp.ClientResponseError: 当HTTP响应状态码不是2XX时抛出
        asyncio.TimeoutError: 当请求超时时抛出
        aiohttp.ClientError: 当发生其他客户端错误时抛出
    """
    # 默认超时配置
    _DEFAULT_TIMEOUT = aiohttp.ClientTimeout(
        total=8,      # 总超时时间（秒）
        connect=5,    # 连接超时时间（秒）
        sock_read=2   # 读取数据超时时间（秒）
    )
    # 创建客户端会话并发送GET请求
    async with aiohttp.ClientSession(timeout=timeout or _DEFAULT_TIMEOUT) as session:
        async with session.get(url, headers=headers, params=params, proxy=proxy) as resp:
            # 检查响应状态码，如果不是2XX则抛出异常
            resp.raise_for_status()
            # 根据is_binary参数决定返回数据类型
            if is_binary:
                # 以二进制方式读取响应内容（适用于图片、文件等）
                return await resp.read()
            else:
                # 以文本方式读取响应内容（默认，适用于文本、JSON等）
                return await resp.text()
