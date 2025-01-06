from playwright.async_api import Browser, async_playwright
from playwright.sync_api import FloatRect

from .db_image import db_image
from ..utils import *

schedule_res = None
_browser = None
festivals_res = None
festivals_res_save_ymdt: str


def get_schedule_data():
    """取日程数据"""

    # 校验过期日程
    def check_expire_schedule(schedule):
        # json取到的时间是utc，本地时间也要取utc后才能比较
        st = time_converter(schedule["regularSchedules"]["nodes"][0]["startTime"])
        ed = time_converter(schedule["regularSchedules"]["nodes"][0]["endTime"])
        now = get_time_now_china()
        if st < now < ed:
            return False
        return True

    global schedule_res
    if schedule_res is None or check_expire_schedule(schedule_res):
        logger.info("重新请求:日程数据")
        result = cf_http_get("https://splatoon3.ink/data/schedules.json").text
        schedule_res = json.loads(result)
        schedule_res = schedule_res["data"]
        return schedule_res
    else:
        return schedule_res


def get_festivals_data():
    """取祭典数据"""
    global festivals_res
    global festivals_res_save_ymdt

    # 校验过期祭典数据 记录%Y-%m-%dT%H，2h刷新一次
    def check_expire_data(_festivals_res_save_ymd):
        now_ymdt = get_expire_time()
        if now_ymdt != _festivals_res_save_ymd:
            return True
        return False

    if festivals_res is None or check_expire_data(festivals_res_save_ymdt):
        logger.info("重新请求:祭典数据")
        result = cf_http_get("https://splatoon3.ink/data/festivals.json").text
        festivals_res = json.loads(result)
        # 刷新储存时 时间
        festivals_res_save_ymdt = get_expire_time()
        return festivals_res
    else:
        return festivals_res


def get_coop_info(_all=None):
    """取 打工 信息"""

    # 取地图信息
    def get_stage_image_info(sch):  # sch为schedule[idx]
        return ImageInfo(
            sch["setting"]["coopStage"]["name"],
            sch["setting"]["coopStage"]["image"]["url"],
            get_trans_stage(sch["setting"]["coopStage"]["id"]),
            "打工地图",
        )

    # 取装备信息
    def get_weapon_image_info(sch):  # sch为schedule[idx]
        # for _i in range(4) 是循环执行4次，不是多余的代码
        return [
            ImageInfo(
                name=sch["setting"]["weapons"][_i]["name"] + "_" + sch["setting"]["weapons"][_i]["__splatoon3ink_id"],
                url=sch["setting"]["weapons"][_i]["image"]["url"],
                zh_name=get_trans_weapon(sch["setting"]["weapons"][_i]["__splatoon3ink_id"]),
                source_type="武器",
            )
            for _i in range(4)
        ]

    # 取时间信息
    def get_str_time(sch):
        _start_time = time_converter_mdhm(sch["startTime"])
        _end_time = time_converter_mdhm(sch["endTime"])
        return "{} - {}".format(_start_time, _end_time)

    # 取boss名称
    def get_str_boss(sch):
        return sch["__splatoon3ink_king_salmonid_guess"]

    # 校验普通打工时间，是否在特殊打工模式之后
    def check_salmonrun_time(_start_time, _special_mode_start_time):
        # 输入时间都缺少年份，需要手动补充一个年份后还原为date对象
        year = get_time_now_china().year
        _start_time = str(year) + "-" + _start_time
        _special_mode_start_time = str(year) + "-" + _special_mode_start_time
        st = datetime.datetime.strptime(_start_time, "%Y-%m-%d %H:%M")
        su_st = datetime.datetime.strptime(_special_mode_start_time, "%Y-%m-%d %H:%M")
        if st > su_st:
            return True
        return False

    # 取日程
    schedule = get_schedule_data()
    # 取翻译
    get_trans_cht_data()
    # 一般打工数据
    regular_schedule = schedule["coopGroupingSchedule"]["regularSchedules"]["nodes"]
    # 团队打工竞赛
    team_schedule = schedule["coopGroupingSchedule"]["teamContestSchedules"]["nodes"]
    # big run 数据
    bigrun_schedule = schedule["coopGroupingSchedule"]["bigRunSchedules"]["nodes"]
    stage = []
    weapon = []
    time = []
    boss = []
    mode = []
    schedule = regular_schedule
    if not _all:
        # 只输出两排
        for i in range(2):
            stage.append(get_stage_image_info(schedule[i]))
            weapon.append(get_weapon_image_info(schedule[i]))
            time.append(get_str_time(schedule[i]))
            boss.append(get_str_boss(schedule[i]))
            mode.append(list_salmonrun_mode[0])
    else:
        # 输出全部(五排)
        stage = [get_stage_image_info(sch) for sch in schedule]
        weapon = [get_weapon_image_info(sch) for sch in schedule]
        time = [get_str_time(sch) for sch in schedule]
        boss = [get_str_boss(sch) for sch in schedule]
        mode = [list_salmonrun_mode[0] for sch in schedule]

    # 如果存在 团队打工
    if len(team_schedule) != 0:
        schedule = team_schedule
        # 计算插入索引
        insert_idx = 0
        need_offset = False
        special_mode_start_time = get_str_time(schedule[0]).split(" - ")[0]
        for k, v in enumerate(time):
            start_time = v.split(" - ")[0]
            if check_salmonrun_time(start_time, special_mode_start_time):
                insert_idx = k
                need_offset = True
                break
        if not need_offset:
            insert_idx = len(time)
        # 插入数据
        stage.insert(insert_idx, get_stage_image_info(schedule[0]))
        weapon.insert(insert_idx, get_weapon_image_info(schedule[0]))
        time.insert(insert_idx, get_str_time(schedule[0]))
        # 团队打工取不到boss信息
        boss.insert(insert_idx, "")
        mode.insert(insert_idx, list_salmonrun_mode[1])

    # 如果存在 bigrun
    if len(bigrun_schedule) != 0:
        schedule = bigrun_schedule
        # 计算插入索引
        insert_idx = 0
        need_offset = False
        special_mode_start_time = get_str_time(schedule[0]).split(" - ")[0]
        for k, v in enumerate(time):
            start_time = v.split(" - ")[0]
            if check_salmonrun_time(start_time, special_mode_start_time):
                insert_idx = k
                need_offset = True
                break
        if not need_offset:
            insert_idx = len(time)
        # 插入数据
        stage.insert(insert_idx, get_stage_image_info(schedule[0]))
        weapon.insert(insert_idx, get_weapon_image_info(schedule[0]))
        time.insert(insert_idx, get_str_time(schedule[0]))
        boss.insert(insert_idx, get_str_boss(schedule[0]))
        mode.insert(insert_idx, list_salmonrun_mode[2])

    return stage, weapon, time, boss, mode


def get_weapon_info(list_weapon: list):
    """取 装备信息"""
    weapon1 = []
    weapon2 = []
    for v in list_weapon:
        _type = v["type"]
        name = v["name"]
        zh_weapon_class = ""
        zh_weapon_sub = ""
        zh_weapon_special = ""
        zh_father_class = ""
        if _type == weapon_image_type[3]:
            # class
            zh_weapon_class = name
        elif _type == weapon_image_type[1]:
            # sub
            zh_weapon_sub = name
        elif _type == weapon_image_type[2]:
            # special
            zh_weapon_special = name
        elif _type == weapon_image_type[4]:
            # father_class
            zh_father_class = name
        weaponData = db_image.get_weapon_info(zh_weapon_class, zh_weapon_sub, zh_weapon_special, zh_father_class)
        weaponData2 = db_image.get_weapon_info(zh_weapon_class, zh_weapon_sub, zh_weapon_special, zh_father_class)
        # 获取图片数据
        # Main
        weaponData.image = db_image.get_weapon_image(weaponData.name, weapon_image_type[0]).get("image")
        weaponData2.image = db_image.get_weapon_image(weaponData2.name, weapon_image_type[0]).get("image")
        # Sub
        weaponData.sub_image = db_image.get_weapon_image(weaponData.sub_name, weapon_image_type[1]).get("image")
        weaponData2.sub_image = db_image.get_weapon_image(weaponData2.sub_name, weapon_image_type[1]).get("image")
        # Special
        weaponData.special_image = db_image.get_weapon_image(weaponData.special_name, weapon_image_type[2]).get("image")
        weaponData2.special_image = db_image.get_weapon_image(weaponData2.special_name, weapon_image_type[2]).get(
            "image"
        )
        # Class
        weaponData.weapon_class_image = db_image.get_weapon_image(weaponData.weapon_class, weapon_image_type[3]).get(
            "image"
        )
        weaponData2.weapon_class_image = db_image.get_weapon_image(weaponData2.weapon_class, weapon_image_type[3]).get(
            "image"
        )
        # 添加
        weapon1.append(weaponData)
        weapon2.append(weaponData2)
    return weapon1, weapon2


def get_stage_info(num_list=None, contest_match=None, rule_match=None):
    """取 图 信息"""
    if num_list is None:
        num_list = [0]
    schedule = get_schedule_data()
    get_trans_cht_data()
    # 竞赛 规则
    if contest_match is not None and contest_match != "":
        new_contest_match = dict_contest_trans[contest_match]
    else:
        new_contest_match = contest_match
    if rule_match is not None and rule_match != "":
        new_rule_match = dict_rule_trans[rule_match]
    else:
        new_rule_match = rule_match

    return schedule, num_list, new_contest_match, new_rule_match


async def init_browser() -> Browser:
    """初始化 browser 并唤起"""
    global _browser
    p = await async_playwright().start()
    if proxy_address:
        proxies = {"server": "http://{}".format(proxy_address)}
        # 代理访问
        _browser = await p.chromium.launch(proxy=proxies)
    else:
        _browser = await p.chromium.launch()
    return _browser


async def get_browser() -> Browser:
    """获取目前唤起的 browser"""
    global _browser
    if _browser is None or not _browser.is_connected():
        _browser = await init_browser()
    return _browser


async def get_screenshot(
    shot_url,
    mode="pc",
    selector=None,
    shot_path=None,
) -> bytes:
    """通过 browser 获取 shot_url 中的网页截图"""
    # playwright 要求不能有多个 browser 被同时唤起
    browser = await get_browser()
    if mode == "pc":
        context = await browser.new_context(viewport={"width": 1920, "height": 1080}, locale="zh-CH")
    elif mode == "mobile":
        context = await browser.new_context(viewport={"width": 500, "height": 2000}, locale="zh-CH")
    page = await context.new_page()

    try:
        await page.goto(shot_url, wait_until="load", timeout=300000)
        await page.wait_for_timeout(1500)
        if selector:
            # 元素选择器
            await page.wait_for_selector(selector)
            element = await page.query_selector(selector)
            screenshot = await element.screenshot(path=shot_path)
            img = screenshot
        else:
            img = await page.screenshot(path=shot_path)

        return img
    except Exception as e:
        logger.error("Screenshot failed" + str(e))
        # return await page.screenshot(full_page=True)
        raise e
    finally:
        await context.close()
