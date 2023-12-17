import datetime
import re
from datetime import timedelta


# 类 图片信息 ImageInfo
class ImageInfo:
    def __init__(self, name, url, zh_name, source_type):
        self.name = name
        self.url = url
        self.zh_name = zh_name
        self.source_type = source_type


# 类 数据表 Weapon_Info + Weapon_Images
class WeaponData:
    # zh 字段暂且预留，方便后续翻译的进行
    # 为了便于先进行 INFO 信息的查询，image 字段默认留空
    def __init__(
        self,
        name,
        sub_name,
        special_name,
        special_points,
        level,
        weapon_class,
        image=None,
        sub_image=None,
        special_image=None,
        weapon_class_image=None,
        zh_name="None",
        zh_sub_name="None",
        zh_special_name="None",
        zh_weapon_class="None",
        zh_father_class="None",
    ):
        self.name = name
        self.image = image
        self.sub_name = sub_name
        self.sub_image = sub_image
        self.special_name = special_name
        self.special_image = special_image
        self.special_points = special_points
        self.level = level
        self.weapon_class = weapon_class
        self.weapon_class_image = weapon_class_image
        self.zh_name = zh_name
        self.zh_sub_name = zh_sub_name
        self.zh_special_name = zh_special_name
        self.zh_weapon_class = zh_weapon_class
        self.zh_father_class = zh_father_class


# 类 时区工具
class TimeUtil(object):
    @classmethod
    def parse_timezone(cls, timezone):
        """
        解析时区表示
        :param timezone: str eg: +8
        :return: dict{symbol, offset}
        """
        result = re.match(r"(?P<symbol>[+-])(?P<offset>\d+)", timezone)
        symbol = result.groupdict()["symbol"]
        offset = int(result.groupdict()["offset"])

        return {"symbol": symbol, "offset": offset}

    @classmethod
    def convert_timezone(cls, dt, timezone="+0") -> datetime.datetime:
        """默认是utc时间，需要提供时区"""
        result = cls.parse_timezone(timezone)
        symbol = result["symbol"]

        offset = result["offset"]

        if symbol == "+":
            return dt + timedelta(hours=offset)
        elif symbol == "-":
            return dt - timedelta(hours=offset)
        else:
            raise Exception("dont parse timezone format")


# 类 帮助菜单节点
class HelpElement:
    """帮助节点
    指令分类 指令list 描述list"""

    def __init__(
        self,
        pre: str,
        order_list: list[str],
        desc_list: list[str],
    ):
        self.pre = pre
        self.order_list = order_list  # 指令列表不宜过多，可能导致宽度超出图片范围
        self.desc_list = desc_list  # 单条备注文字都带有自动换行，文字长度无所谓


# 类 帮助模块
class HelpModel:
    """帮助模块
    功能标题 功能标题颜色 帮助节点
    """

    def __init__(
        self,
        sub_title: str,
        sub_title_rgb: tuple[int, int, int],
        elements: list[HelpElement] = None,
    ):
        self.sub_title = sub_title
        self.sub_title_rgb = sub_title_rgb
        self.elements = elements

    def add_element(self, element: HelpElement):
        self.elements = self.elements.append(element)


# 类 帮助卡片
class HelpCard:
    """帮助卡片
    标题 标题颜色 帮助模块
    """

    def __init__(
        self,
        title: str,
        title_rgb: tuple[int, int, int],
        models: list[HelpModel] = None,
    ):
        self.title = title
        self.title_rgb = title_rgb
        self.models = models

    def add_model(self, model: HelpModel):
        self.models = self.models.append(model)


# help_card = HelpCard(
#     title="地图查询帮助手册",
#     models=[
#         HelpModel(
#             sub_title="对战地图 查询",
#             sub_title_rgb=(234, 255, 61),
#             elements=[
#                 HelpElement(
#                     pre="直接查询:",
#                     order_list=["图", "图图", "下图", "下下图", "全部图"],
#                     desc_list=["查询当前或指定时段 所有模式 的地图", "前面如果是 全部 则显示至多未来5个时段的地图"],
#                 ),
#                 HelpElement(
#                     pre="指定时间段查询:",
#                     order_list=["0图", "123图", "1图", "2468图"],
#                     desc_list=["可以在前面加上多个0-9的数字，不同数字代表不同时段", "如0代表当前，1代表下时段，2代表下下时段，以此类推"],
#                 ),
#             ],
#         ),
#         HelpModel(
#             sub_title="对战地图 筛选查询",
#             sub_title_rgb=(234, 255, 61),
#             elements=[
#                 HelpElement(
#                     pre="直接查询:",
#                     order_list=["挑战", "涂地", "x赛", "塔楼", "开放挑战", "pp抢鱼"],
#                     desc_list=["支持指定规则或比赛，或同时指定规则比赛", "触发词进行了语义化处理，很多常用的称呼也能触发，如:pp和排排 都等同于 开放;抢鱼对应鱼虎;涂涂对应涂地 等"],
#                 ),
#                 HelpElement(
#                     pre="指定时间段查询:",
#                     order_list=["0挑战", "1234开放塔楼", "全部x赛区域"],
#                     desc_list=["与图图的指定时间段查询方法一致，如果指定时间段没有匹配的结果，会返回全部时间段满足该筛选的结果", "前面加上 全部 则显示未来24h满足条件的对战"],
#                 ),
#             ],
#         ),
#         HelpModel(
#             sub_title="打工 查询",
#             sub_title_rgb=(234, 255, 61),
#             elements=[
#                 HelpElement(
#                     pre="直接查询:",
#                     order_list=["工", "打工", "bigrun", "团队打工", "全部工"],
#                     desc_list=["查询当前和下一时段的打工地图，如果存在bigrun或团队打工时，也会显示在里面，并根据时间自动排序", "前面加上 全部 则显示接下来的五场打工地图"],
#                 ),
#             ],
#         ),
#         HelpModel(
#             sub_title="其他 查询",
#             sub_title_rgb=(234, 255, 61),
#             elements=[
#                 HelpElement(
#                     pre="直接查询:",
#                     order_list=["祭典", "活动", "衣服", "帮助", "help"],
#                     desc_list=["查询 祭典  活动  nso当前售卖衣服", "帮助/help:回复本帮助图片"],
#                 ),
#             ],
#         ),
#         HelpModel(
#             sub_title="私房用 随机武器",
#             sub_title_rgb=(234, 255, 61),
#             elements=[
#                 HelpElement(
#                     pre="直接查询:",
#                     order_list=["随机武器", "随机武器 nice弹", "随机武器 小枪 刷 狙 泡"],
#                     desc_list=[
#                         "可以在 随机武器 后面，接至多四个参数，每个参数间用空格分开",
#                         "参数包括全部的 武器类型，如 小枪 双枪 弓 狙 等;全部的 副武器名称，如 三角雷 水球 雨帘;全部的大招名称，如 nice弹 龙卷风 rpg等",
#                         "如果不带参数或参数小于4，剩下的会自动用 同一大类下的武器 进行筛选，如 狙 和 加特林 都属于 远程类，小枪 与 刷子，滚筒 等属于 近程类，保证尽可能公平",
#                         "如果不希望进行任何限制，也可以发送 随机武器完全随机，来触发不加限制的真随机武器(平衡性就没法保证了)",
#                     ],
#                 ),
#             ],
#         ),
#         HelpModel(
#             sub_title="bot管理员命令",
#             sub_title_rgb=(255, 167, 137),
#             elements=[
#                 HelpElement(
#                     pre="直接发送:",
#                     order_list=["清空图片缓存", "更新武器数据"],
#                     desc_list=["清空图片缓存：会主动清空2h内的全部缓存图", "更新武器数据：首次使用时，必须先运行一次这个命令，来更新武器数据库，不然随机武器功能无法使用"],
#                 ),
#             ],
#         ),
#         HelpModel(
#             sub_title="关于本插件",
#             sub_title_rgb=(234, 255, 61),
#             elements=[
#                 HelpElement(
#                     pre="",
#                     order_list=[],
#                     desc_list=[
#                         "本插件已开源，地址如下：",
#                         "https://github.com/Skyminers/Bot-Splatoon3",
#                         "有github账号的人可以去帮忙点个star，这是对我们最大的支持了",
#                         "插件作者:Cypas_Nya;Sky_miner",
#                     ],
#                 ),
#             ],
#         ),
#     ],
# )
