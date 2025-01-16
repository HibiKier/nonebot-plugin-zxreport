from pathlib import Path

import nonebot
import nonebot_plugin_localstore as store
from pydantic import BaseModel

REPORT_PATH = store.get_plugin_cache_file("mahiro_report")
REPORT_PATH.mkdir(parents=True, exist_ok=True)
DATA_PATH = store.get_plugin_data_dir()
DATA_PATH.mkdir(parents=True, exist_ok=True)

TEMPLATE_PATH = Path(__file__).parent


class Conifg(BaseModel):
    alapi_token: str = ""
    """alapi token，在 https://admin.alapi.cn/user/login 登录后获取token"""
    auto_send: bool = True
    """每日9点自动发送"""
    zxrepot_full_show: bool = False
    """是否显示完全信息"""


config = nonebot.get_plugin_config(Conifg)


class Hitokoto(BaseModel):
    id: int
    """id"""
    uuid: str
    """uuid"""
    hitokoto: str
    """一言"""
    type: str
    """类型"""
    from_who: str | None
    """作者"""
    creator: str
    """创建者"""
    creator_uid: int
    """创建者id"""
    reviewer: int
    """审核者"""
    commit_from: str
    """提交来源"""
    created_at: str
    """创建日期"""
    length: int
    """长度"""


class SixDataTo(BaseModel):
    news: list[str]
    """新闻"""
    tip: str
    """tip"""
    updated: int
    """更新日期"""
    url: str
    """链接"""
    cover: str
    """图片"""


class SixData(BaseModel):
    status: int
    """状态码"""
    message: str
    """返回内容"""
    data: SixDataTo
    """数据"""


class WeekDay(BaseModel):
    en: str
    """英文"""
    cn: str
    """中文"""
    ja: str
    """日本称呼"""
    id: int
    """ID"""


class AnimeItem(BaseModel):
    name: str
    name_cn: str
    images: dict | None

    @property
    def image(self) -> str:
        return self.images["large"] if self.images else ""


class Anime(BaseModel):
    weekday: WeekDay
    items: list[AnimeItem]
