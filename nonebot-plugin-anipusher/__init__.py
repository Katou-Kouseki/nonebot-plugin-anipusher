

from .launcher import launch
from nonebot.plugin import PluginMetadata
from nonebot import require
from .model import AniPusherConfig

__plugin_meta__ = PluginMetadata(name="Anipusher推送机",
                                 description="nonebot-plugin-anipusher：一个消息推送插件，支持Emby及AniRss的Webhook信息推送",
                                 usage="nonebot-plugin-anipusher：一个消息推送插，支持Emby及AniRss的Webhook信息推送",
                                 type="application",
                                 config=AniPusherConfig,
                                 homepage="https://github.com/AriadusTT/nonebot-plugin-anipusher",
                                 supported_adapters={"~onebot.v11"}
                                 )

require("nonebot_plugin_localstore")
require("nonebot_plugin_apscheduler")
