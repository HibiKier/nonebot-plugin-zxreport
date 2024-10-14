from nonebot import require
from nonebot.log import logger
from nonebot.plugin import PluginMetadata, inherit_supported_adapters

require("nonebot_plugin_alconna")
require("nonebot_plugin_htmlrender")
require("nonebot_plugin_localstore")

from nonebot_plugin_alconna import Alconna, Image, UniMessage, on_alconna

from .data_source import Report

__plugin_meta__ = PluginMetadata(
    name="真寻日报",
    description="嗨嗨，这里是小记者真寻哦",
    usage="""
    指令：
        真寻日报
    """.strip(),
    type="application",
    homepage="https://github.com/HibiKier/nonebot-plugin-zxreport",
    supported_adapters=inherit_supported_adapters(
        "nonebot_plugin_alconna",
    ),
    extra={"author": "HibiKier", "version": "0.1"},
)


_matcher = on_alconna(Alconna("真寻日报"), priority=5, block=True)


@_matcher.handle()
async def _():
    path = await Report.get_report_image()
    await UniMessage(Image(path=path)).send()
    logger.info("查看真寻日报")
