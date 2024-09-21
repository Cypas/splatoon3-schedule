from typing import Union, Tuple

from .check import _permission_check, _guild_owner_check, ChannelInfo, init_blacklist
from .data.db_control import db_control
from .image.image import *
from .image import image_to_bytes
from .config import plugin_config, driver, global_config, Config
from .utils import dict_keyword_replace, multiple_replace
from .data import reload_weapon_info, db_image, get_screenshot
from .util import get_weapon_info_test, cron_job, push_job, send_msg

from .utils.bot import *

__plugin_meta__ = PluginMetadata(
    name="splatoon3游戏日程查询",
    description="一个基于nonebot2框架的splatoon3游戏日程查询插件",
    usage="发送 帮助 或 help 可查看详细指令\n",
    type="application",
    # 发布必填，当前有效类型有：`library`（为其他插件编写提供功能），`application`（向机器人用户提供功能）。
    homepage="https://github.com/Cypas/splatoon3-schedule",
    # 发布必填。
    config=Config,
    supported_adapters={"~onebot.v11", "~onebot.v12", "~telegram", "~kaiheila", "~qq"},
)

# 图 触发器  正则内需要涵盖所有的同义词
matcher_stage_group = on_regex("^[\\/.,，。]?[0-9]*(全部)?下*图+[ ]?$", priority=8, block=True)


# 图 触发器处理 二次判断正则前，已经进行了同义词替换，二次正则只需要判断最终词
@matcher_stage_group.handle(parameterless=[Depends(_permission_check)])
async def _(bot: Bot, event: Event):
    plain_text = event.get_message().extract_plain_text().strip()
    # 触发关键词  替换.。\/ 等前缀触发词
    plain_text = multiple_replace(plain_text, dict_keyword_replace)
    logger.info("同义文本替换后触发词为:" + plain_text)
    # 判断是否满足进一步正则
    num_list = []
    contest_match = None
    rule_match = None
    flag_match = False
    # 顺序 单图
    if re.search("^[0-9]+图$", plain_text):
        num_list = list(set([int(x) for x in plain_text[:-1]]))
        num_list.sort()
        flag_match = True
    elif re.search("^下{1,11}图$", plain_text):
        re_list = re.findall("下", plain_text)
        # set是为了去除重复数字
        num_list = list(set([len(re_list)]))
        num_list.sort()
        flag_match = True
    # 多图
    elif re.search("^下?图{1,11}$", plain_text):
        re_list = re.findall("图", plain_text)
        lens = len(re_list)
        # 渲染太慢了，限制查询数量
        if lens > 5:
            lens = 5
        num_list = list(set([x for x in range(lens)]))
        num_list.sort()
        if "下" in plain_text:
            num_list.pop(0)
        flag_match = True
    elif re.search("^全部图*$", plain_text):
        # 渲染太慢了，限制查询数量
        num_list = [0, 1, 2, 3, 4, 5]
        flag_match = True
    # 如果有匹配
    if flag_match:
        # 传递函数指针
        func = get_stages_image
        # 获取图片
        img = await get_save_temp_image(plain_text, func, num_list, contest_match, rule_match)
        # 发送消息
        await send_msg(bot, event, img)


# 对战 触发器
matcher_stage = on_regex(
    "^[\\/.,，。]?"
    "([0-9]*)"
    "(全部)?"
    "(下*)"
    "(区域|区|推塔|抢塔|塔楼|塔|蛤蜊|蛤|抢鱼|鱼虎|鱼|涂地|涂涂|涂|挑战|真格|开放|组排|排排|排|pp|p|PP|P|X段|x段|X赛|x赛|X|x)"
    "(区域|区|推塔|抢塔|塔楼|塔|蛤蜊|蛤|抢鱼|鱼虎|鱼|涂地|涂涂|涂|挑战|真格|开放|组排|排排|排|pp|p|PP|P|X段|x段|X赛|x赛|X|x)?[ ]?$",
    priority=8,
    block=True,
)


# 对战 触发器处理
@matcher_stage.handle(parameterless=[Depends(_permission_check)])
async def _(bot: Bot, event: Event, re_tuple: Tuple = RegexGroup()):
    re_list = []
    for k, v in enumerate(re_tuple):
        # 遍历正则匹配字典进行替换文本
        re_list.append(dict_keyword_replace.get(v, v))
    logger.info("同义文本替换后触发词组为:" + json.dumps(re_list, ensure_ascii=False))
    # 输出格式为 ["", null, "下下", "挑战", null] 涉及?匹配且没有提供该值的是null
    # 索引 全部 下 匹配1 匹配2

    plain_text = ""
    if re_list[0]:
        plain_text = plain_text + re_list[0]
    elif re_list[1]:
        plain_text = plain_text + re_list[1]
    elif re_list[2]:
        plain_text = plain_text + re_list[2]
    if re_list[3]:
        plain_text = plain_text + re_list[3]
    if re_list[4]:
        plain_text = plain_text + re_list[4]

    num_list: list = []
    contest_match = None
    rule_match = None
    flag_match = True

    # 计算索引列表
    if re_list[1]:
        # 含有全部
        num_list = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
    elif re_list[2]:
        # 含有 下
        splits = re_list[2].split("下")  # 返回拆分数组
        lens = len(splits) - 1  # 返回拆分次数-1
        num_list = list(set([lens]))
        num_list.sort()
    elif re_list[0]:
        # 数字索引
        num_list = list(set([int(x) for x in re_list[0]]))
        num_list.sort()
    else:
        num_list = [0]

    # 计算比赛和规则
    if re_list[3] and re_list[4]:
        # 双匹配
        # 判断第一个参数是比赛还是规则
        if re_list[3] in dict_contest_trans and re_list[4] in dict_rule_trans:
            # 比赛 规则
            contest_match = re_list[3]
            rule_match = re_list[4]
        elif re_list[3] in dict_rule_trans and re_list[4] in dict_contest_trans:
            # 规则 比赛
            contest_match = re_list[4]
            rule_match = re_list[3]
        else:
            flag_match = False
    elif re_list[3] and (not re_list[4]):
        # 单匹配
        # 判断参数是比赛还是规则
        if re_list[3] in dict_contest_trans:
            # 比赛
            contest_match = re_list[3]
        elif re_list[3] in dict_rule_trans:
            # 规则
            rule_match = re_list[3]
        else:
            flag_match = False
    else:
        flag_match = False

    # 如果有匹配
    if flag_match:
        # 传递函数指针
        func = get_stages_image
        # 获取图片
        img = await get_save_temp_image(plain_text, func, num_list, contest_match, rule_match)
        # 发送消息
        await send_msg(bot, event, img)


# 打工 触发器
matcher_coop = on_regex("^[\\/.,，。]?(全部)?(工|打工|鲑鱼跑|bigrun|big run|团队打工)[ ]?$", priority=8, block=True)


# matcher_coop = on_command("全部打工", priority=8, block=True)


# 打工 触发器处理
@matcher_coop.handle(parameterless=[Depends(_permission_check)])
async def _(bot: Bot, event: Event):
    plain_text = event.get_message().extract_plain_text().strip()
    # 触发关键词  替换.。\/ 等前缀触发词
    plain_text = multiple_replace(plain_text, dict_keyword_replace)
    logger.info("同义文本替换后触发词为:" + plain_text)
    # 判断是否满足进一步正则
    _all = False
    if "全部" in plain_text:
        _all = True
    # 传递函数指针
    func = get_coop_stages_image
    # 获取图片
    img = await get_save_temp_image(plain_text, func, _all)
    # 发送消息
    await send_msg(bot, event, img)


# 配装 触发器
matcher_build = on_regex(
    "^[\\/.,，。]?配装\s{0,2}([\\u4e00-\\u9fa5a-zA-Z0-9·-]{2,20}?(\s(装饰|改装|联名|新型|新艺术|金属箔|精英|精英装饰|姐妹|高磁波|墨黑|薄荷|黑|白|甲|乙))?)?\s?(区域|区|推塔|抢塔|塔楼|塔|蛤蜊|蛤|抢鱼|鱼虎|鱼|涂地|涂涂|涂)?$",
    priority=8,
    block=True,
)


# 配装 触发器处理
@matcher_build.handle(parameterless=[Depends(_permission_check)])
async def _(bot: Bot, event: Event, re_tuple: Tuple = RegexGroup()):
    re_list = []
    for k, v in enumerate(re_tuple):
        # 遍历正则匹配字典进行替换文本
        if k == 0:
            # 武器名
            if v:
                v = v.upper()
                v = multiple_replace(v, dict_builds_pre_replace)
            re_list.append(v)
        if k == len(re_tuple) - 1:
            # 模式
            value = dict_keyword_replace.get(v, v)
            re_list.append(value)
    logger.info("同义文本替换后触发参数为:" + json.dumps(re_list, ensure_ascii=False))

    if not re_list[0]:
        msg = "请携带需要查询的武器或模式信息作为参数，若为贴牌需要加上贴牌二字，如:\n/配装 小绿\n指定模式查询:\n/配装 贴牌碳刷 塔楼"
        await send_msg(bot, event, msg)
        return

    # 整理参数
    is_deco = False
    mode = None
    weapon_name = re_list[0]
    if "贴牌" in weapon_name:
        is_deco = True
        weapon_name = weapon_name.replace("贴牌", "")

    # 查询对应武器
    build_info = db_image.get_build_info(weapon_name, is_deco)
    if not build_info:
        msg = f"该关键词 {weapon_name} 未查询到对应武器，请试试使用官方中文武器名称或其他常用名称后再试，如:\n/配装 小绿\n指定模式查询:\n/配装 贴牌碳刷 塔楼"
        logger.warning(f"该关键词未匹配到武器 {weapon_name}")
        await send_msg(bot, event, msg)
        return
    zh_name: str = build_info.get("zh_name")
    sendou_name: str = build_info.get("sendou_name")

    plain_text = "配装"
    re_list[0] = f'{zh_name.replace(" ", "")}'
    plain_text = f"{plain_text} {re_list[0]}"
    if re_list[1]:
        plain_text = f"{plain_text} {re_list[1]}"

    # mode
    if re_list[1]:
        mode = re_list[1]
        mode_str = mode
    else:
        mode_str = "全部"
    msg = f"正在获取武器 {re_list[0]} 在 {mode_str}模式下的配装推荐，请稍等..."
    await send_msg(bot, event, msg)

    # 传递函数指针
    func = get_build_image
    # 获取图片
    img = await get_save_temp_image(plain_text, func, sendou_name, mode)
    # 发送图片
    await send_msg(bot, event, img)


# 其他命令 触发器
matcher_else = on_regex("^[\\/.,，。]?(帮助|help|nso帮助|(随机武器).*|装备|衣服|祭典|活动)[ ]?$", priority=8, block=True)


# 其他命令 触发器处理
@matcher_else.handle(parameterless=[Depends(_permission_check)])
async def _(bot: Bot, event: Event):
    plain_text = event.get_message().extract_plain_text().strip()
    # 触发关键词  替换.。\/ 等前缀触发词
    plain_text = multiple_replace(plain_text, dict_prefix_replace)
    plain_text = plain_text.replace("help", "帮助")
    logger.info("同义文本替换后触发词为:" + plain_text)
    # 判断是否满足进一步正则
    # 随机武器
    if re.search("^随机武器.*$", plain_text):
        # 这个功能不能进行缓存，必须实时生成图
        # 测试数据库能否取到武器数据
        if not get_weapon_info_test():
            msg = "请机器人管理员先发送 更新武器数据 更新本地武器数据库后，才能使用随机武器功能"
            await send_msg(bot, event, msg)
        else:
            img = image_to_bytes(await get_random_weapon_image(plain_text))
            # 发送消息
            await send_msg(bot, event, img)
    elif re.search("^祭典$", plain_text):
        # 传递函数指针
        func = get_festival_image
        # 获取图片
        img = await get_save_temp_image(plain_text, func)
        if img is None:
            msg = "近期没有任何祭典"
            await send_msg(bot, event, msg)
        else:
            # 发送图片
            await send_msg(bot, event, img)
    elif re.search("^活动$", plain_text):
        # 传递函数指针
        func = get_events_image
        # 获取图片
        img = await get_save_temp_image(plain_text, func)
        if img is None:
            msg = "近期没有任何活动比赛"
            await send_msg(bot, event, msg)
        else:
            # 发送图片
            await send_msg(bot, event, img)

    elif re.search("^帮助$", plain_text):
        # 传递函数指针
        func = get_help_image
        # 获取图片
        img = await get_save_temp_image(plain_text, func)
        # 发送图片
        await send_msg(bot, event, img)
        # 当优先帮助打开时，额外发送nso帮助
        if plugin_config.splatoon3_schedule_plugin_priority_mode:
            await send_msg(bot, event, "若需要查看完整的nso指令请发送 /nso帮助")

    elif re.search("^nso帮助$", plain_text):
        # 传递函数指针
        func = get_nso_help_image
        # 获取图片
        img = await get_save_temp_image(plain_text, func)
        # 发送图片
        await send_msg(bot, event, img)

    elif re.search("^装备$", plain_text):
        img = await get_screenshot(shot_url="https://splatoon3.ink/gear", mode="mobile")
        # 发送图片
        await send_msg(bot, event, img)


# 管理命令 触发器
matcher_manage = on_regex("^[\\/.,，。]?(开启|关闭)(查询|推送)[ ]?$", priority=8, block=True)


# 管理命令 触发器处理
@matcher_manage.handle(parameterless=[Depends(_guild_owner_check)])
async def _(bot: Bot, event: Event, state: T_State, re_tuple: Tuple = RegexGroup()):
    re_list = []
    for k, v in enumerate(re_tuple):
        re_list.append(v)
    # 触发关键词  替换.。\/ 等前缀触发词
    plain_text = event.get_message().extract_plain_text().strip()
    plain_text = multiple_replace(plain_text, dict_prefix_replace)
    # 获取字典
    channel_info: ChannelInfo = state.get("_channel_info_")
    if channel_info is not None:
        status = 0
        if re_list[0] == "开启":
            status = 1
        elif re_list[0] == "关闭":
            status = 0
        if re_list[1] == "查询":
            db_control.add_or_modify_MESSAGE_CONTROL(
                channel_info.bot_adapter,
                channel_info.bot_id,
                channel_info.source_type,
                channel_info.source_id,
                msg_source_name=channel_info.source_name,
                status=status,
                msg_source_parent_id=channel_info.source_parent_id,
                msg_source_parent_name=channel_info.source_parent_name,
            )
            init_blacklist()
        elif re_list[1] == "推送" in plain_text:
            user_level = state.get("_user_level_")
            if (not plugin_config.splatoon3_guild_owner_switch_push) & (user_level == "owner"):
                logger.info(f"插件配置项未允许 频道服务器拥有者 修改主动推送开关")
                return
            db_control.add_or_modify_MESSAGE_CONTROL(
                channel_info.bot_adapter,
                channel_info.bot_id,
                channel_info.source_type,
                channel_info.source_id,
                msg_source_name=channel_info.source_name,
                active_push=status,
                msg_source_parent_id=channel_info.source_parent_id,
                msg_source_parent_name=channel_info.source_parent_name,
            )
        await send_msg(bot, event, f"已{re_list[0]}本频道 日程{re_list[1]} 功能")


matcher_admin = on_regex("^[\\/.,，。]?(重载武器数据|更新武器数据|清空图片缓存)$", priority=8, block=True, permission=SUPERUSER)


# 重载武器数据，包括：武器图片，副武器图片，大招图片，武器配置信息
@matcher_admin.handle()
async def _(bot: Bot, event: Event):
    # 触发关键词  替换.。\/ 等前缀触发词
    plain_text = event.get_message().extract_plain_text().strip()
    plain_text = multiple_replace(plain_text, dict_prefix_replace)
    err_msg = "执行失败，错误日志为: "
    # 清空图片缓存
    if re.search("^清空图片缓存$", plain_text):
        msg = "数据库合成图片缓存数据已清空！"
        try:
            db_image.clean_image_temp()
        except Exception as e:
            msg = err_msg + str(e)
        # 发送消息
        await send_msg(bot, event, msg)

    elif re.search("^(重载武器数据|更新武器数据)$", plain_text):
        msg_start = "将开始重新爬取武器数据，此过程可能需要10min左右,请稍等..."
        msg = "武器数据更新完成"
        await send_msg(bot, event, msg_start)
        try:
            await reload_weapon_info()
        except Exception as e:
            msg = err_msg + str(e) + "\n如果错误信息是timed out，不妨可以等会儿重新发送指令"
        await send_msg(bot, event, msg)


@driver.on_startup
async def startup():
    """nb启动时事件"""
    # 清空合成图片缓存表
    # db_image.clean_image_temp()
    # 初始化黑名单字典
    init_blacklist()


@driver.on_shutdown
async def shutdown():
    """nb关闭时事件"""
    # 关闭数据库
    db_image.close()
    db_control.close()


@driver.on_bot_connect
async def _(bot: Bot):
    """bot接入时事件"""
    require("nonebot_plugin_apscheduler")
    from nonebot_plugin_apscheduler import scheduler

    bot_adapter = bot.adapter.get_name()
    bot_id = bot.self_id

    # 防止bot重连时重复添加任务
    job_id = f"sp3_schedule_push_job_{bot_id}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
        logger.info(f"remove job {job_id} first")

    scheduler.add_job(
        push_job,
        trigger="cron",
        hour="0,2,4,6,8,10,12,14,16,18,20,22",
        minute=1,
        id=job_id,
        args=[bot, bot_adapter, bot_id],
        misfire_grace_time=60,
        coalesce=True,
        max_instances=1,
    )
    logger.info(f"add job {job_id}")
