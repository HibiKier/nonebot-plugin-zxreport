from datetime import datetime

from nonebot import require
from nonebot.log import logger
from nonebot.permission import SUPERUSER
from nonebot.plugin import PluginMetadata, inherit_supported_adapters
from playwright.async_api import TimeoutError

require("nonebot_plugin_alconna")
require("nonebot_plugin_htmlrender")
require("nonebot_plugin_localstore")

from nonebot_plugin_alconna import Alconna, Image, UniMessage, on_alconna

from .config import REPORT_PATH
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

_reset_matcher = on_alconna(
    Alconna("重置真寻日报"), priority=5, block=True, permission=SUPERUSER
)


@_reset_matcher.handle()
async def _():
    file = REPORT_PATH / f"{datetime.now().date()}.png"
    if file.exists():
        file.unlink()
        logger.info("重置真寻日报")
    await UniMessage("真寻日报已重置!").send()


@_matcher.handle()
async def _():
    try:
        path = await Report.get_report_image()
        await UniMessage(Image(path=path)).send()
        logger.info("查看真寻日报")
    except TimeoutError:
        await UniMessage("真寻日报生成超时...").send(at_sender=True)
        logger.error("真寻日报生成超时")
