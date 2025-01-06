import datetime
import os

import cfscrape
import httpx
from httpx import Response

from .dataClass import TimeUtil
from ..config import plugin_config

DIR_RESOURCE = f"{os.path.abspath(os.path.join(__file__, os.pardir, os.pardir))}/resource"
time_format_ymdh = "%Y-%m-%dT%H"
HTTP_TIME_OUT = 5.0  # 请求超时，秒
proxy_address = plugin_config.splatoon3_proxy_address
if proxy_address:
    proxies = "http://{}".format(proxy_address)
else:
    proxies = None

# 背景 rgb颜色
dict_bg_rgb = {
    "Turf War": (24, 200, 26),
    "Ranked Challenge": (227, 68, 17),
    "Ranked Open": (24, 200, 26),
    "X Schedule": (14, 205, 147),
    "打工": (14, 203, 146),
    "活动": (223, 42, 119),
    "祭典": (103, 103, 114),
    "祭典时间-金黄": (234, 255, 61),
    "上-武器卡片-黄": (234, 255, 61),
    "下-武器卡片-蓝": (96, 58, 255),
    "上-武器卡片": (255, 148, 157),
    "下-武器卡片": (124, 217, 127),
    "祭典结算项目卡片": (63, 63, 70, 70),
}


def cf_http_get(url: str):
    """cf get"""
    # 实例化一个create_scraper对象
    scraper = cfscrape.create_scraper()
    # 请求报错，可以加上时延
    # scraper = cfscrape.create_scraper(delay = 6)
    if proxy_address:
        cf_proxies = {
            "http": "http://{}".format(proxy_address),
            "https": "http://{}".format(proxy_address),
        }
        # 获取网页内容 代理访问
        res = scraper.get(url, proxies=cf_proxies)
    else:
        # 获取网页内容
        res = scraper.get(url)
    return res


async def async_http_get(url: str) -> Response:
    """async http_get"""
    async with httpx.AsyncClient(proxies=proxies) as client:
        response = await client.get(url, timeout=HTTP_TIME_OUT)
        return response


def http_get(url: str) -> Response:
    """http_get"""
    response = httpx.get(url, proxies=proxies, timeout=HTTP_TIME_OUT)
    return response


def multiple_replace(text, _dict):
    """批量替换文本"""
    for key in _dict:
        text = text.replace(key, _dict[key])
    return text


def get_expire_time() -> str:
    """计算过期时间 字符串 精确度为 ymdh"""
    # 计算过期时间
    time_now = get_time_now_china()
    time_now_h = time_now.hour
    # 计算过期时间字符串
    # 判断当前小时是奇数还是偶数
    expire_time: datetime
    if (time_now_h % 2) == 0:
        # 偶数
        expire_time = time_now + datetime.timedelta(hours=2)
    else:
        expire_time = time_now + datetime.timedelta(hours=1)
    expire_time_str = expire_time.strftime(time_format_ymdh).strip()
    return expire_time_str


def time_converter(time_str) -> datetime:
    """时间转换 年-月-日 时:分:秒"""
    # convert time to UTC+8
    dt = datetime.datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%SZ")
    dt += datetime.timedelta(hours=8)
    return dt


def time_converter_yd(time_str):
    """时间转换 月-日"""
    dt = time_converter(time_str)
    return datetime.datetime.strftime(dt, "%m.%d")


def time_converter_hm(time_str):
    """时间转换 时:分"""
    dt = time_converter(time_str)
    return datetime.datetime.strftime(dt, "%H:%M")


def time_converter_mdhm(time_str):
    """时间转换 月-日 时:分"""
    dt = time_converter(time_str)
    return datetime.datetime.strftime(dt, "%m-%d %H:%M")


def time_converter_weekday(time_str):
    """时间转换 周几，如周一"""
    dt = time_converter(time_str)
    weekday = dt.weekday()
    return weekday


def get_time_ymd():
    """获取年月日"""
    dt = get_time_now_china().strftime("%Y-%m-%d")
    return dt


def get_time_y() -> int:
    """获取年"""
    year = get_time_now_china().year
    return year


def get_time_now_china() -> datetime.datetime:
    """获取中国所在东八区时间"""
    # 获取utc时间，然后转东8区时间
    utc_now = datetime.datetime.utcnow()
    convert_now = TimeUtil.convert_timezone(utc_now, "+8")
    return convert_now
