import datetime
import json
import random

from nonebot.log import logger
from .utils import get_time_ymd, cf_http_get, time_format_ymdh, get_time_now_china, get_expire_time

trans_res: dict = None
trans_eng_res: dict = None
trans_res_expire_ymd: str
trans_eng_res_expire_ymd: str
# 武器图片类型
weapon_image_type = ["Main", "Sub", "Special", "Class", "Father_Class"]


def check_expire_trans(_trans_res_expire_ymd):
    """校验过期翻译 过期时间为两小时"""
    expire_time = datetime.datetime.strptime(_trans_res_expire_ymd, time_format_ymdh)
    time_now = get_time_now_china()
    if time_now >= expire_time:
        return True
    return False


def get_trans_cht_data() -> dict:
    """取中文 翻译数据"""
    global trans_res
    global trans_res_expire_ymd
    if trans_res is None or check_expire_trans(trans_res_expire_ymd):
        logger.info("重新请求:中文翻译文本")
        result = cf_http_get("https://splatoon3.ink/data/locale/zh-CN.json").text
        trans_res = json.loads(result)
        # 刷新储存时 时间
        trans_res_expire_ymd = get_expire_time()
        return trans_res
    else:
        return trans_res


def get_trans_eng_data() -> dict:
    """取英文 文本数据"""
    global trans_eng_res
    global trans_eng_res_expire_ymd
    if trans_eng_res is None or check_expire_trans(trans_eng_res_expire_ymd):
        logger.info("重新请求:英文文本")
        result = cf_http_get("https://splatoon3.ink/data/locale/en-GB.json").text
        trans_eng_res = json.loads(result)
        # 刷新储存时 时间
        trans_eng_res_expire_ymd = get_expire_time()
        return trans_eng_res
    else:
        return trans_eng_res


def weapons_trans_eng_to_cht(eng_name):
    """装备由英文名翻译为中文"""
    # 获取两组语言数据
    cht_data = get_trans_cht_data()
    eng_data = get_trans_eng_data()
    cht_weapons = dict(cht_data["weapons"])
    eng_weapons = dict(eng_data["weapons"])
    key = ""
    zht_name = ""
    # 查找英文对应的key
    for k, v in eng_weapons.items():
        if v["name"] == eng_name:
            key = k
            break
    # 用key来查找中文
    if key != "":
        zht_name = cht_weapons[key]["name"]
    return zht_name


def get_trans_stage(_id: str):
    """获取地图翻译名"""
    global trans_res
    zh_res = trans_res["stages"].get(_id)
    if zh_res:
        zh_name = zh_res["name"]
    else:
        return "未取得翻译名称"
    return zh_name


def get_trans_weapon(_id: str):
    """获取武器翻译名"""
    global trans_res
    zh_res = trans_res["weapons"].get(_id)
    if zh_res:
        zh_name = zh_res["name"]
    else:
        return "未取得翻译名称"
    return zh_name


def get_trans_game_mode(text):
    """用现有翻译字典对游戏模式进行翻译"""
    if text in dict_rule_reverse_trans:
        return dict_rule_reverse_trans[text]
    return text


def weapon_semantic_word_conversion(word: str):
    """装备 语义词转换,并返回语义词类别"""
    word_type = weapon_image_type
    # 判断这个语义词是属于 类别，副武器，大招
    if word in dict_weapon_class:
        return word_type[3], dict_weapon_class.get(word)
    if word in dict_weapon_sub:
        return word_type[1], dict_weapon_sub.get(word)
    if word in dict_weapon_special:
        return word_type[2], dict_weapon_special.get(word)
    # 没有任何匹配时，取随机大类别
    # 遍历values
    father_class_list = []
    for v in dict_weapon_class.values():
        father_class_list.append(dict_weapon_father_class_trans.get(v))
    return word_type[4], random.choice(list(father_class_list))


# 翻译字典
dict_rule_reverse_trans = {
    "LOFT": "真格塔楼",
    "CLAM": "真格蛤蜊",
    "GOAL": "真格鱼虎",
    "AREA": "真格区域",
    "TURF_WAR": "占地对战",
}

# 星期翻译
dict_weekday_trans = {
    0: "一",
    1: "二",
    2: "三",
    3: "四",
    4: "五",
    5: "六",
    6: "日",
}
# dict
dict_contest_trans = {
    "涂地": "Turf War",
    "挑战": "Ranked Challenge",
    "开放": "Ranked Open",
    "X段": "X Schedule",
}
dict_rule_trans = {
    "区域": "AREA",
    "蛤蜊": "CLAM",
    "塔楼": "LOFT",
    "鱼虎": "GOAL",
}

# 触发前缀  同义文本替换
dict_prefix_replace = {
    "\\": "",
    "/": "",
    ".": "",
    "。": "",
    ",": "",
    "，": "",
}

# 触发关键词  同义文本替换
dict_keyword_replace = {
    "\\": "",
    "/": "",
    ".": "",
    "。": "",
    ",": "",
    "，": "",
    "涂涂": "涂地",
    "涂": "涂地",
    "组排": "开放",
    "排排": "开放",
    "排": "开放",
    "pp": "开放",
    "PP": "开放",
    "P": "开放",
    "help": "帮助",
    "p": "开放",
    "单排": "挑战",
    "真格": "挑战",
    "x": "X段",
    "X": "X段",
    "x段": "X段",
    "X赛": "X段",
    "x赛": "X段",
    "推塔": "塔楼",
    "塔": "塔楼",
    "抢塔": "塔楼",
    "抢鱼": "鱼虎",
    "鱼": "鱼虎",
    "蛤": "蛤蜊",
    "区": "区域",
    "鲑鱼跑": "工",
    "团队打工": "工",
    "打工": "工",
    "big run": "工",
    "bigrun": "工",
}

# 配装武器关键词前置处理
dict_builds_pre_replace = {
    "无印": "",
    "炮": "泡",
    "息": "熄",
    "篮": "蓝",
    " ": "",
    ".": "",
    "。": "",
    "·": "",
    "-": "",
    "/": "",
}

# 配装武器mode翻译
dict_builds_mode_trans = {
    "涂地": "TW",
    "塔楼": "TC",
    "鱼虎": "RM",
    "蛤蜊": "CB",
    "区域": "SZ",
}

# 规范翻译字典 装备 主武器名称
# noinspection SpellCheckingInspection
dict_weapon_main_trans = {
    ".52 Gal": ".52加仑",
    ".96 Gal": ".96加仑",
    ".96 Gal Deco": ".96加仑 装饰",
    "Aerospray MG": "专业模型枪MG",
    "Aerospray RG": "专业模型枪RG",
    "Annaki Splattershot Nova": "太空射击枪 联名",
    "Ballpoint Splatling": "圆珠笔",
    "Bamboozler 14 Mk I": "14式竹筒枪·甲",
    "Big Swig Roller": "宽滚筒",
    "Big Swig Roller Express": "宽滚筒 联名",
    "Blaster": "火热爆破枪",
    "Bloblobber": "满溢泡澡泼桶",
    "Carbon Roller": "碳纤维滚筒",
    "Carbon Roller Deco": "碳纤维滚筒 装饰",
    "Clash Blaster": "冲涂爆破枪",
    "Clash Blaster Neo": "冲涂爆破枪 新型",
    "Classic Squiffer": "鱿快洁α",
    "Custom Dualie Squelchers": "双重清洁枪 改装",
    "Custom Jet Squelcher": "喷射清洁枪 改装",
    "Custom Splattershot Jr.": "枫叶射击枪",
    "Dapple Dualies": "溅镀枪",
    "Dapple Dualies Nouveau": "溅镀枪·新艺术",
    "Dark Tetra Dualies": "四重弹跳手枪 黑",
    "Dualie Squelchers": "双重清洁枪",
    "Dynamo Roller": "电动马达滚筒",
    "E-liter 4K": "公升4K",
    "E-liter 4K Scope": "4K准星枪",
    "Explosher": "爆炸泼桶",
    "Flingza Roller": "可变式滚筒",
    "Forge Splattershot Pro": "顶尖射击枪 联名",
    "Glooga Dualies": "开尔文525",
    "Goo Tuber": "高压油管枪",
    "H-3 Nozzlenose": "H3卷管枪",
    "H-3 Nozzlenose D": "H3卷管枪D",
    "Heavy Splatling": "桶装旋转枪",
    "Heavy Splatling Deco": "桶装旋转枪 装饰",
    "Hero Shot Replica": "英雄射击枪 复制",
    "Hydra Splatling": "消防栓旋转枪",
    "Inkbrush": "巴勃罗",
    "Inkbrush Nouveau": "巴勃罗·新艺术",
    "Jet Squelcher": "喷射清洁枪",
    "Krak-On Splat Roller": "斯普拉滚筒 联名",
    "L-3 Nozzlenose": "L3卷管枪",
    "L-3 Nozzlenose D": "L3卷管枪D",
    "Light Tetra Dualies": "四重弹跳手枪 白",
    "Luna Blaster": "新星爆破枪",
    "Luna Blaster Neo": "新星爆破枪 新型",
    "Mini Splatling": "斯普拉旋转枪",
    "N-ZAP '85": "N-ZAP85",
    "N-ZAP '89": "N-ZAP89",
    "Nautilus 47": "鹦鹉螺号47",
    "Neo Splash-o-matic": "窄域标记枪 新型",
    "Neo Sploosh-o-matic": "广域标记枪 新型",
    "Octobrush": "北斋",
    "Painbrush": "文森",
    "Range Blaster": "远距爆破枪",
    "Rapid Blaster": "快速爆破枪",
    "Rapid Blaster Deco": "快速爆破枪 装饰",
    "Rapid Blaster Pro": "快速爆破枪 精英",
    "Rapid Blaster Pro Deco": "快速爆破枪 精英装饰",
    "REEF-LUX 450": "LACT-450",
    "S-BLAST '92": "S-BLAST92",
    "Slosher": "飞溅泼桶",
    "Slosher Deco": "飞溅泼桶 装饰",
    "Sloshing Machine": "回旋泼桶",
    "Snipewriter 5H": "R-PEN/5H",
    "Splash-o-matic": "窄域标记枪",
    "Splat Brella": "遮阳防空伞",
    "Splat Charger": "斯普拉蓄力狙击枪",
    "Splat Dualies": "斯普拉机动枪",
    "Splat Roller": "斯普拉滚筒",
    "Splatana Stamper": "工作刮水刀",
    "Splatana Wiper": "雨刷刮水刀",
    "Splatana Wiper Deco": "雨刷刮水刀 装饰",
    "Splatterscope": "斯普拉准星枪",
    "Splattershot": "斯普拉射击枪",
    "Splattershot Jr.": "新叶射击枪",
    "Splattershot Nova": "太空射击枪",
    "Splattershot Pro": "顶尖射击枪",
    "Sploosh-o-matic": "广域标记枪",
    "Squeezer": "开瓶喷泉枪",
    "Tenta Brella": "露营防空伞",
    "Tenta Sorella Brella": "露营防空伞 姐妹",
    "Tentatek Splattershot": "斯普拉射击枪 联名",
    "Tri-Slosher": "洗笔桶",
    "Tri-Slosher Nouveau": "洗笔桶·新艺术",
    "Tri-Stringer": "三发猎鱼弓",
    "Undercover Brella": "特工配件",
    "Z+F Splat Charger": "斯普拉蓄力狙击枪 联名",
    "Z+F Splatterscope": "斯普拉准星枪 联名",
    "Zink Mini Splatling": "斯普拉旋转枪 联名",
    "Ballpoint Splatling Nouveau": "圆珠笔·新艺术",
    "Bloblobber Deco": "满溢泡澡泼桶 装饰",
    "Custom Goo Tuber": "高压油管枪 改装",
    "Dread Wringer": "墨瀑淋",
    "Gold Dynamo Roller": "电动马达滚筒 高磁波",
    "Heavy Edit Splatling": "审查者",
    "Inkline Tri-Stringer": "三发猎鱼弓 联名",
    "Octobrush Nouveau": "北斋·新艺术",
    "Sloshing Machine Neo": "回旋泼桶 新型",
    "Sorella Brella": "遮阳防空伞 姐妹",
    "Custom Blaster": "火热爆破枪 改装",
    "Enperry Splat Dualies": "斯普拉机动枪 联名",
    "Foil Squeezer": "开瓶喷泉枪 金属箔",
    "Painbrush Nouveau": "文森·新艺术",
    "REEF-LUX 450 Deco": "LACT-450 装饰",
    "S-BLAST '91": "S-BLAST91",
    "Snipewriter 5B": "R-PEN/5B",
    "Undercover Sorella Brella": "特工配件 姐妹",
    "Splatana Stamper Nouveau": "工作刮水刀·新艺术",
    ".52 Gal Deco": ".52加仑 装饰",
    "Custom E-liter 4K": "公升4K 改装",
    "Custom E-liter 4K Scope": "4K准星枪 改装",
    "Custom Explosher": "爆炸泼桶 改装",
    "Douser Dualies FF": "灭熄FF",
    "Dread Wringer D": "墨瀑淋D",
    "Foil Flingza Roller": "可变式滚筒 金属箔",
    "Glooga Dualies Deco": "开尔文525 装饰",
    "Nautilus 79": "鹦鹉螺号79",
    "New Squiffer": "鱿快洁β",
    "Recycled Brella 24 Mk I": "24式可替换伞·甲",
    "Bamboozler 14 Mk II": "14式竹筒枪·乙",
    "Charcoal Decavitator": "巨齿刮水刀 墨黑",
    "Custom Douser Dualies FF": "灭熄FF 改装",
    "Custom Hydra Splatling": "消防栓旋转枪 改装",
    "Custom Range Blaster": "远距爆破枪 改装",
    "Custom Wellstring V": "邦普V 改装",
    "Heavy Edit Splatling Nouveau": "审查者·新艺术",
    "Mint Decavitator": "巨齿刮水刀 薄荷",
    "Recycled Brella 24 Mk II": "24式可替换伞·乙",
    "Wellstring V": "邦普V",
}

# 规范翻译字典 装备 副武器名称
# noinspection SpellCheckingInspection
dict_weapon_sub_trans = {
    "Splat Bomb": "斯普拉炸弹",
    "Suction Bomb": "吸盘炸弹",
    "Burst Bomb": "快速炸弹",
    "Sprinkler": "洒墨器",
    "Splash Wall": "斯普拉防护墙",
    "Fizzy Bomb": "碳酸炸弹",
    "Curling Bomb": "冰壶炸弹",
    "Autobomb": "机器人炸弹",
    "Squid Beakon": "跳跃信标",
    "Point Sensor": "定点侦测器",
    "Ink Mine": "墨汁陷阱",
    "Toxic Mist": "毒雾",
    "Angle Shooter": "标线器",
    "Torpedo": "鱼雷",
}

# 规范翻译字典 装备 大招名称
# noinspection SpellCheckingInspection
dict_weapon_special_trans = {
    "Trizooka": "终极发射",
    "Big Bubbler": "巨大防护罩",
    "Zipcaster": "触手喷射",
    "Tenta Missiles": "多重导弹",
    "Ink Storm": "墨雨云",
    "Booyah Bomb": "赞气弹",
    "Wave Breaker": "弹跳声呐",
    "Ink Vac": "吸墨机",
    "Killer Wail 5.1": "喇叭辐射5.1ch",
    "Inkjet": "喷射背包",
    "Ultra Stamp": "终极印章",
    "Crab Tank": "螃蟹坦克",
    "Reefslider": "鲨鱼坐骑",
    "Triple Inkstrike": "三重龙卷风",
    "Tacticooler": "能量站",
    "Super Chump": "诱饵烟花",
    "Kraken Royale": "帝王鱿鱼",
    "Triple Splashdown": "终极着陆",
    "Splattercolor Screen": "浮墨幕墙",
}

# 规范翻译字典 装备 类别名称
# noinspection SpellCheckingInspection
dict_weapon_class_trans = {
    "Shooter": "射击枪",
    "Blaster": "爆破枪",
    "Brella": "伞",
    "Brush": "笔刷",
    "Charger": "狙击枪",
    "Dualie": "双枪",
    "Roller": "滚筒",
    "Slosher": "泼桶",
    "Splatana": "刮水刀",
    "Splatling": "旋转枪",
    "Stringer": "弓",
}

# 武器类别 归属大类
dict_weapon_father_class_trans = {
    "射击枪": "近距离",
    "爆破枪": "中距离",
    "伞": "近距离",
    "笔刷": "近距离",
    "狙击枪": "长距离",
    "双枪": "近距离",
    "滚筒": "近距离",
    "泼桶": "中距离",
    "刮水刀": "中距离",
    "旋转枪": "长距离",
    "弓": "长距离",
}

# 语义化字典 装备 副武器
dict_weapon_sub = {
    "斯普拉炸弹": "斯普拉炸弹",
    "三角雷": "斯普拉炸弹",
    "吸盘炸弹": "吸盘炸弹",
    "粘弹": "吸盘炸弹",
    "黏弹": "吸盘炸弹",
    "快速炸弹": "快速炸弹",
    "水球": "快速炸弹",
    "洒墨器": "洒墨器",
    "花洒": "洒墨器",
    "斯普拉防护墙": "斯普拉防护墙",
    "水帘": "斯普拉防护墙",
    "帘子": "斯普拉防护墙",
    "雨帘": "斯普拉防护墙",
    "碳酸炸弹": "碳酸炸弹",
    "碳酸": "碳酸炸弹",
    "摇摇乐": "碳酸炸弹",
    "冰壶炸弹": "冰壶炸弹",
    "冰壶": "冰壶炸弹",
    "机器人炸弹": "机器人炸弹",
    "小鸡雷": "机器人炸弹",
    "小鸡": "机器人炸弹",
    "跳跃信标": "跳跃信标",
    "跳点": "跳跃信标",
    "信标": "跳跃信标",
    "定点侦测器": "定点侦测器",
    "狗链": "定点侦测器",
    "狗环": "定点侦测器",
    "墨汁陷阱": "墨汁陷阱",
    "陷阱": "墨汁陷阱",
    "地雷": "墨汁陷阱",
    "毒雾": "毒雾",
    "毒瓶": "毒雾",
    "标线器": "标线器",
    "马克笔": "标线器",
    "鱼雷": "鱼雷",
}

# 语义化字典 装备 大招
dict_weapon_special = {
    "终极发射": "终极发射",
    "rpg": "终极发射",
    "RPG": "终极发射",
    "巨大防护罩": "巨大防护罩",
    "防护罩": "巨大防护罩",
    "触手喷射": "触手喷射",
    "触手": "触手喷射",
    "蜘蛛侠": "触手喷射",
    "多重导弹": "多重导弹",
    "导弹": "多重导弹",
    "墨雨云": "墨雨云",
    "下雨": "墨雨云",
    "元气弹": "赞气弹",
    "赞气弹": "赞气弹",
    "nice弹": "赞气弹",
    "弹跳声呐": "弹跳声呐",
    "跳蛋": "弹跳声呐",
    "声呐": "弹跳声呐",
    "吸墨机": "吸墨机",
    "吸尘器": "吸墨机",
    "喇叭辐射5.1ch": "喇叭辐射5.1ch",
    "镭射": "喇叭辐射5.1ch",
    "激光": "喇叭辐射5.1ch",
    "喷射背包": "喷射背包",
    "喷气背包": "喷射背包",
    "飞机": "喷射背包",
    "jet": "喷射背包",
    "JET": "喷射背包",
    "终极印章": "终极印章",
    "印章": "终极印章",
    "锤子": "终极印章",
    "大锤": "终极印章",
    "螃蟹坦克": "螃蟹坦克",
    "螃蟹": "螃蟹坦克",
    "鲨鱼坐骑": "鲨鱼坐骑",
    "鲨鱼": "鲨鱼坐骑",
    "三重龙卷风": "三重龙卷风",
    "龙卷风": "三重龙卷风",
    "能量站": "能量站",
    "饮料站": "能量站",
    "饮料": "能量站",
    "诱饵烟花": "诱饵烟花",
    "反击狼烟": "诱饵烟花",
    "烟花": "诱饵烟花",
    "诱饵": "诱饵烟花",
    "帝王鱿鱼": "帝王鱿鱼",
    "鱿鱼": "帝王鱿鱼",
    "帝王乌贼": "帝王鱿鱼",
    "大王乌贼": "帝王鱿鱼",
    "终极砸地": "终极着陆",
    "砸地": "终极着陆",
    "屏障": "浮墨幕墙",
    "墨墙": "浮墨幕墙",
    "幕墙": "浮墨幕墙",
}

# 语义化字典 装备类别
dict_weapon_class = {
    "射击枪": "射击枪",
    "小枪": "射击枪",
    "爆破枪": "爆破枪",
    "泡": "爆破枪",
    "炮": "爆破枪",
    "伞": "伞",
    "笔刷": "笔刷",
    "画笔": "笔刷",
    "刷子": "笔刷",
    "笔": "笔刷",
    "狙击枪": "狙击枪",
    "狙": "狙击枪",
    "双枪": "双枪",
    "滚筒": "滚筒",
    "筒": "滚筒",
    "刷": "滚筒",
    "泼桶": "泼桶",
    "桶": "泼桶",
    "刮水刀": "刮水刀",
    "电锯": "刮水刀",
    "锯": "刮水刀",
    "水刀": "刮水刀",
    "刀": "刮水刀",
    "旋转枪": "旋转枪",
    "加特林": "旋转枪",
    "加": "旋转枪",
    "弓": "弓",
}

# 鲑鱼跑模式
list_salmonrun_mode = ["coop", "team_coop", "big_run"]
