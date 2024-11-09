import asyncio
import json
import xml.etree.ElementTree as ET
from datetime import datetime

import httpx
import tenacity
from httpx import ConnectError, HTTPStatusError, Response, TimeoutException
from nonebot.log import logger
from nonebot.utils import run_sync
from nonebot_plugin_htmlrender import template_to_pic
from tenacity import retry, stop_after_attempt, wait_fixed
from zhdate import ZhDate

from .config import (
    DATA_PATH,
    REPORT_PATH,
    TEMPLATE_PATH,
    Anime,
    Hitokoto,
    SixData,
    config,
    favs_arr,
    favs_list,
)


class GroupManage:

    def __init__(self):
        self._file = DATA_PATH / "data.json"
        self._data = []
        if self._file.exists():
            data = json.load(self._file.open(encoding="utf8"))
            self._data = data["close"]

    def add(self, group_id: str):
        if group_id not in self._data:
            self._data.append(group_id)

    def remove(self, group_id: str):
        if group_id in self._data:
            self._data.remove(group_id)

    def check(self, group_id: str) -> bool:
        logger.debug(f"检测日报发送群组: {group_id}:{group_id in self._data}")
        return group_id in self._data

    def save(self):
        with self._file.open("w", encoding="utf8") as file:
            json.dump({"close": self._data}, file, ensure_ascii=False, indent=4)


group_manager = GroupManage()


class AsyncHttpx:
    @classmethod
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(1),
        retry=(
            tenacity.retry_if_exception_type(
                (TimeoutException, ConnectError, HTTPStatusError)
            )
        ),
    )
    async def get(cls, url: str) -> Response:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url)
                response.raise_for_status()
                return response
            except (TimeoutException, ConnectError, HTTPStatusError) as e:
                logger.error(f"Request to {url} failed due to: {e}")
                raise

    @classmethod
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(1),
        retry=(
            tenacity.retry_if_exception_type(
                (TimeoutException, ConnectError, HTTPStatusError)
            )
        ),
    )
    async def post(
        cls, url: str, data: dict[str, str], headers: dict[str, str]
    ) -> Response:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, data=data, headers=headers)
                response.raise_for_status()
                return response
            except (TimeoutException, ConnectError, HTTPStatusError) as e:
                logger.error(f"Request to {url} failed due to: {e}")
                raise


@run_sync
def save(data: bytes):
    file_path = REPORT_PATH / f"{datetime.now().date()}.png"
    with open(file_path, "wb") as file:
        file.write(data)


class Report:
    hitokoto_url = "https://v1.hitokoto.cn/?c=a"
    alapi_url = "https://v2.alapi.cn/api/zaobao"
    six_url = "https://60s.viki.moe/?v2=1"
    game_url = "https://www.4gamers.com.tw/rss/latest-news"
    bili_url = "https://s.search.bilibili.com/main/hotword"
    it_url = "https://www.ithome.com/rss/"
    anime_url = "https://api.bgm.tv/calendar"

    week = {  # noqa: RUF012
        0: "一",
        1: "二",
        2: "三",
        3: "四",
        4: "五",
        5: "六",
        6: "日",
    }

    @classmethod
    async def get_report_image(cls) -> bytes:
        """获取数据"""
        now = datetime.now()
        file = REPORT_PATH / f"{now.date()}.png"
        if file.exists():
            with file.open("rb") as image_file:
                return image_file.read()
        zhdata = ZhDate.from_datetime(now)
        result = await asyncio.gather(
            *[
                cls.get_hitokoto(),
                cls.get_bili(),
                cls.get_six(),
                cls.get_anime(),
                cls.get_it(),
            ]
        )
        data = {
            "data_festival": cls.festival_calculation(),
            "data_hitokoto": result[0],
            "data_bili": result[1],
            "data_six": result[2],
            "data_anime": result[3],
            "data_it": result[4],
            "week": cls.week[now.weekday()],
            "date": now.date(),
            "zh_date": zhdata.chinese().split()[0][5:],
        }
        image_bytes = await template_to_pic(
            template_path=str((TEMPLATE_PATH / "mahiro_report").absolute()),
            template_name="main.html",
            templates={"data": data},
            pages={
                "viewport": {"width": 578, "height": 1885},
                "base_url": f"file://{TEMPLATE_PATH}",
            },
            wait=2,
        )
        await save(image_bytes)
        return image_bytes

    @classmethod
    def festival_calculation(cls) -> list[tuple[str, str]]:
        """计算节日"""
        base_date = datetime(2016, 1, 1)
        n = (datetime.now() - base_date).days
        result = []

        for i in range(0, len(favs_arr), 2):
            if favs_arr[i] >= n:
                result.extend(
                    (favs_arr[i + j] - n, favs_list[favs_arr[i + j + 1]])
                    for j in range(0, 14, 2)
                )
                break
        return result

    @classmethod
    async def get_hitokoto(cls) -> str:
        """获取一言"""
        res = await AsyncHttpx.get(cls.hitokoto_url)
        data = Hitokoto(**res.json())
        return data.hitokoto

    @classmethod
    async def get_bili(cls) -> list[str]:
        """获取哔哩哔哩热搜"""
        res = await AsyncHttpx.get(cls.bili_url)
        data = res.json()
        return [item["keyword"] for item in data["list"]]

    @classmethod
    async def get_alapi_data(cls) -> list[str]:
        """获取alapi数据"""
        payload = {"token": config.alapi_token, "format": "json"}
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        res = await AsyncHttpx.post(cls.alapi_url, data=payload, headers=headers)
        if res.status_code != 200:
            return ["Error: Unable to fetch data"]
        data = res.json()
        news_items = data.get("data", {}).get("news", [])
        return news_items[:11] if len(news_items) > 11 else news_items

    @classmethod
    async def get_six(cls) -> list[str]:
        """获取60s数据"""
        if config.alapi_token:
            return await cls.get_alapi_data()
        res = await AsyncHttpx.get(cls.six_url)
        data = SixData(**res.json())
        return data.data.news[:11] if len(data.data.news) > 11 else data.data.news

    @classmethod
    async def get_it(cls) -> list[str]:
        """获取it数据"""
        res = await AsyncHttpx.get(cls.it_url)
        root = ET.fromstring(res.text)
        titles = []
        for item in root.findall("./channel/item"):
            title_element = item.find("title")
            if title_element is not None:
                titles.append(title_element.text)
        return titles[:11] if len(titles) > 11 else titles

    @classmethod
    async def get_anime(cls) -> list[tuple[str, str]]:
        """获取动漫数据"""
        res = await AsyncHttpx.get(cls.anime_url)
        data_list = []
        week = datetime.now().weekday()
        try:
            anime = Anime(**res.json()[week])
        except IndexError:
            anime = Anime(**res.json()[-1])
        data_list.extend(
            (data.name_cn or data.name, data.image) for data in anime.items
        )
        return data_list[:8] if len(data_list) > 8 else data_list
