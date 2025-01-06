from bs4 import BeautifulSoup

from .db_image import db_image
from ..utils import *

# 爬取地址
weapon_url = "https://splatoonwiki.org/wiki/List_of_weapons_in_Splatoon_3"
base_url = "https://splatoonwiki.org/wiki"


async def reload_weapon_info():
    """爬取wiki数据 来重载武器数据，包括：武器图片，副武器图片，大招图片，武器配置信息"""
    global weapon_url
    response = await async_http_get(weapon_url)
    soup = BeautifulSoup(response.text, "html.parser")
    # 通过 selector 找到 Weapon list
    weapon_list = iter(soup.select_one("#mw-content-text > div > div > table > tbody").find_all("tr"))
    # 跳过表头
    next(weapon_list)
    for weapon_info in weapon_list:
        # (image_td, name_td, id_td, sub_td, special_td, special_points_td, level_pd, price_td, class_pd)
        # 筛选掉用作分隔符的偶数下标元素
        weapon_info = [weapon_info.contents[i] for i in range(len(weapon_info.contents)) if i % 2 == 1]
        weapon_data = WeaponData(
            name=weapon_info[1].contents[0].text,
            sub_name=weapon_info[3].contents[2].text,
            special_name=weapon_info[4].contents[2].text,
            special_points=int(weapon_info[5].contents[0]),
            level=int(weapon_info[6].contents[0].replace("\n", "")),
            weapon_class=weapon_info[8].contents[2].text,
            zh_name="None",
            zh_sub_name="None",
            zh_special_name="None",
        )
        # 排除秩序dlc武器
        introdeced: str = weapon_info[9].text
        if introdeced.startswith("Version 7.0.0 (Side Order)"):
            continue
        # 主武器，副武器，大招，武器类别，武器父类别 取翻译字典
        # 先从字典取武器名称翻译
        if weapon_data.name in dict_weapon_main_trans:
            weapon_data.zh_name = dict_weapon_main_trans[weapon_data.name]
        else:
            # 没有的话利用中英对照数据看能不能找到翻译数据(贴牌武器基本都不行，就只能等手动更新)
            weapon_data.zh_name = weapons_trans_eng_to_cht(weapon_data.name)
        if weapon_data.sub_name in dict_weapon_sub_trans:
            weapon_data.zh_sub_name = dict_weapon_sub_trans[weapon_data.sub_name]
        if weapon_data.special_name in dict_weapon_special_trans:
            weapon_data.zh_special_name = dict_weapon_special_trans[weapon_data.special_name]
        if weapon_data.weapon_class in dict_weapon_class_trans:
            weapon_data.zh_weapon_class = dict_weapon_class_trans[weapon_data.weapon_class]
            weapon_data.zh_father_class = dict_weapon_father_class_trans[weapon_data.zh_weapon_class]
        logger.info(
            "Reload Weapon data: {}, {}, {}, {}".format(
                weapon_data.name, weapon_data.sub_name, weapon_data.special_name, weapon_data.weapon_class
            )
        )
        # 数据库新增 装备信息
        db_image.add_or_modify_weapon_info(weapon_data)
        # 数据库新增 装备图片
        names = [
            weapon_data.name,
            weapon_data.sub_name,
            weapon_data.special_name,
            weapon_data.weapon_class,
        ]
        ids = [0, 3, 4, 8]
        for i in range(3):
            # 主武器图片、副武器图片、大招图片
            await get_image_info(
                ImageInfo(name=names[i], url=None, source_type=weapon_image_type[i], zh_name=None)
            )  # 多余项忽略
        # 类型图片，没有找到 File 页面
        await push_weapon_images(
            ImageInfo(
                name=names[3],
                url="https:" + weapon_info[ids[3]].contents[0].contents[0].contents[0].attrs["src"],
                source_type=weapon_image_type[3],
                zh_name=None,  # 多余项忽略
            )
        )
    return True


async def get_image_info(imageInfo: ImageInfo):
    """网页爬取图片信息"""
    global base_url
    url = base_url + "/File:S3_Weapon_{}_{}.png".format(imageInfo.source_type, imageInfo.name.replace(" ", "_"))
    response = await async_http_get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    imageInfo.url = "https:" + soup.select_one("#file > a > img").attrs["src"]
    await push_weapon_images(imageInfo)


async def push_weapon_images(img: ImageInfo):
    """向数据库新增 武器图片 二进制文件"""
    res = db_image.get_weapon_image(img.name, img.source_type)
    if not res:
        image_data = await get_file_url(img.url)
        if len(image_data) != 0:
            logger.info("[ImageDB] new weapon image {}".format(img.name))
            db_image.add_or_modify_weapon_images(
                img.name,
                img.source_type,
                image_data,
            )


async def get_file_url(url):
    """从网页读获取图片"""
    resp = await async_http_get(url)
    data = resp.content
    return data


if __name__ == "__main__":
    reload_weapon_info()
