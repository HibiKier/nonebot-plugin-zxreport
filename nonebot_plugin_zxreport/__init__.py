import asyncio
from datetime import datetime

from nonebot import get_bots, require
from nonebot.log import logger
from nonebot.permission import SUPERUSER
from nonebot.plugin import PluginMetadata, inherit_supported_adapters
from playwright.async_api import TimeoutError

require("nonebot_plugin_alconna")
require("nonebot_plugin_htmlrender")
require("nonebot_plugin_localstore")
require("nonebot_plugin_apscheduler")
require("nonebot_plugin_uninfo")

from nonebot_plugin_alconna import Alconna, Image, Target, UniMessage, on_alconna
from nonebot_plugin_apscheduler import scheduler
from nonebot_plugin_uninfo import get_interface

from .config import REPORT_PATH, Conifg, config
from .data_source import Report

__plugin_meta__ = PluginMetadata(
    name="真寻日报",
    description="嗨嗨，这里是小记者真寻哦",
    usage="""
    指令：
        真寻日报
    """.strip(),
    type="application",
    config=Conifg,
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
        await UniMessage(Image(raw=path)).send()
        logger.info("查看真寻日报")
    except TimeoutError:
        await UniMessage("真寻日报生成超时...").send(at_sender=True)
        logger.error("真寻日报生成超时")


@scheduler.scheduled_job(
    "cron",
    hour=0,
    minute=1,
)
async def _():
    for _ in range(3):
        try:
            await Report.get_report_image()
            logger.info("自动生成日报成功...")
            break
        except TimeoutError:
            logger.warning("自动生成日报失败...")


@scheduler.scheduled_job(
    "cron",
    hour=9,
    minute=1,
)
async def _():
    if config.auto_send:
        file = await Report.get_report_image()
        for _, bot in get_bots().items():
            if interface := get_interface(bot):
                scenes = [s for s in await interface.get_scenes() if s.is_group]
                for scene in scenes:
                    await UniMessage(Image(raw=file)).send(
                        bot=bot, target=Target(scene.id)
                    )
                    await asyncio.sleep(1)
        logger.info("每日真寻日报发送完成...")
