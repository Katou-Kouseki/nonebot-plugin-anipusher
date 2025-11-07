<div align="center">
  <a href="https://v2.nonebot.dev/store"><img src="https://v2.nonebot.dev/logo.png" width="180" height="180" alt="NoneBotPluginLogo"></a>
  <br>
</div>

<div align="center">

# nonebot-plugin-AniPusher

_✨ NoneBot AniPusher插件 ✨_<br>
NoneBot AniPusher插件 是将特定Webhooks消息推送至QQ的插件<br>
目前支持配置来自ani-rss和emby的webhooks消息



[![license](https://img.shields.io/github/license/AriadusTT/nonebot-plugin-anipusher.svg?cachebust=1)](./LICENSE)
[![pypi](https://img.shields.io/pypi/v/nonebot-plugin-AniPusher.svg)](https://pypi.python.org/pypi/nonebot-plugin-AniPusher)
[![python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
</div>

> [!IMPORTANT]
> 重大更新，请务必查看新的配置方式与功能列表

## 📖 介绍

AniPusher插件 是将特定Webhook消息推送至QQ的插件<br>

目前支持AniRSS和Emby推送<br>

![show](./docs/show.png)

## 💿 安装

<details open>
<summary>使用 nb-cli 安装</summary>
在 nonebot2 项目的根目录下打开命令行, 输入以下指令即可安装

    nb plugin install nonebot-plugin-anipusher

</details>

<details>
<summary>使用包管理器安装</summary>
在 nonebot2 项目的插件目录下, 打开命令行, 根据你使用的包管理器, 输入相应的安装命令

<details>
<summary>pip</summary>

    pip install nonebot-plugin-anipusher
</details>
<details>
<summary>pdm</summary>

    pdm add nonebot-plugin-anipusher
</details>
<details>
<summary>poetry</summary>

    poetry add nonebot-plugin-anipusher
</details>
<details>
<summary>conda</summary>

    conda install nonebot-plugin-anipusher
</details>

打开 nonebot2 项目根目录下的 `pyproject.toml` 文件, 在 `[tool.nonebot]` 部分追加写入

    plugins = ["nonebot-plugin-anipusher"]

</details>

## ⚙️ ani-rss配置[[ani-rss项目地址](https://github.com/wushuo894/ani-rss)]
该配置方法基于ani-rss `v2.0.13` 更新后新的通知配置功能<br>

`ani-rss → 设置 → 通知 → 添加通知`<br>
↓按如下配置↓<br>
![ani-rss-config](./docs/ani-rss-config.png)

通知类型为`Webhook`<br>
Method为`POST`<br>
URL为Nonebot2的IP地址和端口下的路径`/webhook`<br>
例如`http://Nonebot_IP:8080/webhook`<br>

↓Body请复制下方Json填入↓<br>

```json
{
  "ani": "${action}",
  "action": "${action}",
  "title": "${title}",
  "jpTitle": "${jpTitle}",
  "score": "${score}",
  "themoviedbName": "${themoviedbName}",
  "tmdbid": "${tmdbid}",
  "tmdbUrl": "${tmdburl}",
  "bgmUrl": "${bgmUrl}",
  "season": "${season}",
  "episode": "${episode}",
  "subgroup": "${subgroup}",
  "progress": "${currentEpisodeNumber}/${totalEpisodeNumber}",
  "premiere": "${year}-${month}-${date}",
  "text": "${text}",
  "downloadPath": "${downloadPath}",
  "episodeTitle": "${episodeTitle}",
  "bgmEpisodeTitle": "${bgmEpisodeTitle}",
  "bgmJpEpisodeTitle": "${bgmJpEpisodeTitle}",
  "image": "${image}"
}
```
> [!TIP]
> 如果未来AniRSS更新通知配置发生变化，需更改Body结构时，请保留键```"ani": "${action}"```，程序判断数据来源依赖此键！<br>
> 其余键值对可根据ani-rss的使用文档中通知下的通知模板对应的键结构进行更改<br>

## ⚙️ Emby配置
首先请确保你已在Emby服务器上安装了Webhooks插件（该插件目前已自动集成，应该不用再手动装了）<br>

`Emby → 设置 → 通知 → 添加通知 -> Webhooks`<br>
按如下配置<br>
![embv-config](./docs/emby-config.png)

网址为Nonebot2的IP地址和端口下的路径`/webhook`<br>
例如`http://Nonebot_IP:8080/webhook`<br>
请求内容类型为`application/json`<br>
Event目前只支持`媒体库-新媒体已添加`<br>
其他选项根据自身需求更改<br>


## ⚙️ 插件配置

配置项位于 nonebot2 项目根目录下的 `.env` 文件内<br>
如果没有配置插件项插件会自动跳过载入。<br>
请至少配置空插件项（如下图所示）<br>
![env](./docs/env-config.png)

> [!IMPORTANT]
> 缺少anipusher__emby_host或anipusher__emby_key会导致无法下载Emby服务器上的图片，其他渠道图片依旧可用<br>
> 缺少anipusher__tmdb_authorization时，插件将无法验证TMDB ID,导致数据无法存入综合数据库并且无法使用订阅命令。<br>
> 缺少anipusher__proxy时，插件会在初始化时尝试直连TMDB，如果连接测试失败，TMDB相关功能也会关闭。<br>

| 配置项 | 必填 | 默认值 | 说明 |
|:----|:----:|:----:|:----:|
| anipusher__emby_host | 否 | 无 | Emby的服务器地址（请勿填写中转地址）|
| anipusher__emby_key | 否 | 无 | Emby服务器-高级-API密钥中生成的密钥 |
| anipusher__tmdb_authorization | 否 | 无 | TMDB用户的ApiKey|
| anipusher__proxy | 否 | 无 | TMDB代理，如不填写则不使用代理 |

## 🎉 使用

### 指令表

| 指令 | 权限 | 需要@ | 范围 | 说明 |
|:-----|:----:|:----:|:----:|:----|
| 启用EMBY推送 | ALL | 否 | 私聊/群聊 | 群聊：发送指令后即将群组添加到Emby更新消息推送列表中，有新消息时将消息推送到群内<br>私聊：发送指令后即将用户添加到Emby更新消息推送列表中 |
| 启用AniRSS推送 | ALL | 否 | 私聊/群聊 | 群聊：发送指令后即将群组添加到AniRSS更新消息推送列表中，有新消息时将消息推送到群内<br>私聊：发送指令后即将用户添加到AniRSS更新消息推送列表中 |
| 取消EMBY推送 | ALL | 否 | 私聊/群聊 | 群聊：发送指令后关闭群组更新消息推送，不再接收推送<br>私聊：发送指令后关闭用户更新消息推送，不再接收推送 |
| 取消AniRSS推送 | ALL | 否 | 私聊/群聊 | 群聊：发送指令后关闭群组更新消息推送，不再接收推送<br>私聊：发送指令后关闭用户更新消息推送，不再接收推送 |
| 屏蔽推送 | ALL | 否 | 私聊/群聊 | 任何范围用户发送命令后,推送服务将被暂停,但记录服务仍在运行，使用重启推送命令后重启 |
| 重启推送 | ALL | 否 | 私聊/群聊 | 任何范围用户发送命令后,插件会重载推送对象，重启推送服务 |
| 订阅/取消订阅 | ALL | 否 | 私聊/群聊 | 群聊：使用订阅/取消订阅命令后在群组推送时会@您，私聊：程序只会在EMBY/ANISS推送功能开启时推送您订阅的番剧更新信息，没有订阅的则不会推送 |

### 订阅功能演示

支持带参数的订阅与对话式订阅，对话超时时间为60秒，如查询到多个结果会自动发送给用户选择，用户输入序号即可订阅，输入错误可重试次数为：5次<br>
演示效果如下图所示<br>
![对话式订阅](./docs/对话式订阅.png)
![带参数订阅](./docs/带参数订阅.png)




