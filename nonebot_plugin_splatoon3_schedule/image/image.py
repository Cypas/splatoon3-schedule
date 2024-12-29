from ..data import get_coop_info, get_stage_info, get_weapon_info, get_schedule_data, get_screenshot
from .image_processer import *
from .image_processer_tools import image_to_bytes


async def get_coop_stages_image(*args):
    """取 打工图片"""
    _all = args[0]
    # 获取数据
    stage, weapon, time, boss, mode = get_coop_info(_all)
    # 绘制图片
    image = get_coop_stages(stage, weapon, time, boss, mode)
    return image


async def get_stages_image(*args):
    """取 对战图片"""
    num_list = args[0]
    contest_match = args[1]
    rule_match = args[2]
    logger.info("num_list为:" + str(num_list))
    logger.info("contest_match为:" + str(contest_match))
    logger.info("rule_match为:" + str(rule_match))
    # 获取数据
    schedule, new_num_list, new_contest_match, new_rule_match = get_stage_info(num_list, contest_match, rule_match)
    # 绘制图片
    image = get_stages(schedule, new_num_list, new_contest_match, new_rule_match)
    return image


async def get_festival_image(*args):
    """取 祭典图片"""
    festivals = get_festivals_data()
    image = get_festival(festivals)
    return image


async def get_events_image(*args):
    """取 活动图片"""
    schedule = get_schedule_data()
    events = schedule["eventSchedules"]["nodes"]
    # 如果存在活动
    if len(events) > 0:
        image = get_events(events)
        return image
    else:
        return None


async def get_help_image(*args):
    """取 帮助图片"""
    image = get_help()
    return image


async def get_nso_help_image(*args):
    """取 nso帮助图片"""
    image = get_nso_help()
    return image


async def get_build_image(*args):
    """取 配装网页截图图片"""
    sendou_name, mode = args[0], args[1]
    # 取mode翻译
    mode = dict_builds_mode_trans.get(mode, mode)

    url = f"https://sendou.ink/builds/{sendou_name}?limit=6"
    if mode:
        url += '&f=[{"type":"mode","mode":"' + mode + '"},{"type":"date","date":"2024-11-20"}]'
    else:
        url += '&f=[{"type":"date","date":"2024-09-12"}]'

    logger.info(f"sendou.ink url: {url}")
    try:
        img = await get_screenshot(shot_url=url, mode="pc", selector=".layout__main")
    except Exception as e:
        return f"bot服务器网络错误，网页截图失败，请稍后再试:{e}"
    return img


async def get_random_weapon_image(*args):
    """取 新版 随机武器图片 不能进行缓存，这个需要实时生成"""
    plain_text = args[0]
    # 判断是否有空格
    list_weapon = []
    # 是否携带参数
    if "完全随机" in plain_text:
        for v in range(4):
            list_weapon.append({"type": "zh_father_class", "name": ""})
    elif " " in plain_text:
        plain_text = plain_text.replace("随机武器", "").strip()
        args = plain_text.split(" ")
        # 如果参数超出
        if len(args) > 4:
            args = args[:4]
        for v in args:
            _type, name = weapon_semantic_word_conversion(v)
            list_weapon.append({"type": _type, "name": name})
        # 如果数量不够四个,用随机大类组别来填充
        if len(list_weapon) < 4:
            for v in range(4 - len(list_weapon)):
                _type, name = weapon_semantic_word_conversion("")
                list_weapon.append({"type": _type, "name": name})
    else:
        # 四个全部用随机大类组别填充
        for v in range(4):
            _type, name = weapon_semantic_word_conversion("")
            list_weapon.append({"type": _type, "name": name})
    # 日志输出组别list信息
    logger.info("武器筛选条件为:" + json.dumps(list_weapon, ensure_ascii=False))
    # 按照 list_weapon 要求随机从sql数据库查找数据
    weapon1, weapon2 = get_weapon_info(list_weapon)
    # 进行乱序
    random.shuffle(weapon1)
    random.shuffle(weapon2)

    # 绘制图片
    image = get_random_weapon(weapon1, weapon2)
    return image


async def get_save_temp_image(trigger_word, func, *args):
    """向数据库新增或读取图片二进制  缓存图片"""
    res = db_image.get_img_temp(trigger_word)
    image: Image
    image_data: bytes
    if not res:
        # 重新生成图片并写入
        image = await func(*args)
        if image is None:
            return image
        if isinstance(image, str):
            # 错误文本消息
            return image
        if isinstance(image, Image.Image):
            image_data = image_to_bytes(image)
        else:
            image_data = image
        if len(image_data) != 0:
            # 如果是太大的图片，需要压缩到1000k以下确保最后发出图片的大小
            image_data = compress_image(image_data, kb=1000, step=10, quality=80)
            logger.info("[ImageDB] new temp image {}".format(trigger_word))
            if "配装" not in trigger_word:
                db_image.add_or_modify_IMAGE_TEMP(trigger_word, image_data, get_expire_time())
            else:
                # 配装截图一个月过期
                time_now = get_time_now_china()
                expire_time = time_now + datetime.timedelta(days=30)
                expire_time_str = expire_time.strftime(time_format_ymdh).strip()
                db_image.add_or_modify_IMAGE_TEMP(trigger_word, image_data, expire_time_str)
        return image_data
    else:
        image_expire_time = res.get("image_expire_time")
        image_data = res.get("image_data")
        # 判断时间是否过期
        expire_time = datetime.datetime.strptime(image_expire_time, time_format_ymdh)
        time_now = get_time_now_china()
        if time_now >= expire_time or (time_now.hour == 0 and time_now.minute < 1):
            # 重新生成图片并写入
            image = await func(*args)
            if image is None:
                return image
            if isinstance(image, str):
                # 错误文本消息
                return image
            if isinstance(image, Image.Image):
                image_data = image_to_bytes(image)
            else:
                image_data = image
            if len(image_data) != 0:
                # 如果是太大的图片，需要压缩到1000k以下确保最后发出图片的大小
                image_data = compress_image(image_data, kb=1000, step=10, quality=80)
                logger.info("[ImageDB] update temp image {}".format(trigger_word))
                db_image.add_or_modify_IMAGE_TEMP(trigger_word, image_data, get_expire_time())
            return image_data
        else:
            logger.info(f"触发词:{trigger_word} 存在时效范围内的缓存图片，将读取缓存图片")
            return image_to_bytes(Image.open(io.BytesIO(image_data)))


# 旧版 取 随机武器图片 不能进行缓存，这个需要实时生成
# def old_get_random_weapon_image(*args):
#     weapon1 = args[0]
#     weapon2 = args[1]
#     # 绘制图片
#     image = old_get_random_weapon(weapon1, weapon2)
#     return image_to_bytes(image)
