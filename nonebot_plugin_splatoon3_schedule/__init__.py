from typing import Union, Tuple

import nonebot
from nonebot.internal.adapter import Event
from nonebot.internal.matcher import Matcher
from nonebot.internal.params import Depends
from nonebot.params import RegexGroup
from nonebot.plugin import PluginMetadata
from nonebot import on_regex, Bot, params, require, on_command
from nonebot.permission import SUPERUSER
from nonebot.typing import T_State

# onebot11 协议
from nonebot.adapters.onebot.v11 import Bot as V11_Bot
from nonebot.adapters.onebot.v11 import MessageEvent as V11_ME
from nonebot.adapters.onebot.v11 import Message as V11_Msg
from nonebot.adapters.onebot.v11 import MessageSegment as V11_MsgSeg
from nonebot.adapters.onebot.v11 import PrivateMessageEvent as V11_PME
from nonebot.adapters.onebot.v11 import GroupMessageEvent as V11_GME

# onebot12 协议
from nonebot.adapters.onebot.v12 import Bot as V12_Bot
from nonebot.adapters.onebot.v12 import MessageEvent as V12_ME
from nonebot.adapters.onebot.v12 import Message as V12_Msg
from nonebot.adapters.onebot.v12 import MessageSegment as V12_MsgSeg
from nonebot.adapters.onebot.v12 import ChannelMessageEvent as V12_CME
from nonebot.adapters.onebot.v12 import PrivateMessageEvent as V12_PME
from nonebot.adapters.onebot.v12 import GroupMessageEvent as V12_GME

# telegram 协议
from nonebot.adapters.telegram import Bot as Tg_Bot
from nonebot.adapters.telegram.event import MessageEvent as Tg_ME
from nonebot.adapters.telegram import MessageSegment as Tg_MsgSeg
from nonebot.adapters.telegram.event import PrivateMessageEvent as Tg_PME
from nonebot.adapters.telegram.event import GroupMessageEvent as Tg_GME
from nonebot.adapters.telegram.event import ChannelPostEvent as Tg_CME
from nonebot.adapters.telegram.message import File as Tg_File

# kook协议
from nonebot.adapters.kaiheila import Bot as Kook_Bot
from nonebot.adapters.kaiheila.event import MessageEvent as Kook_ME
from nonebot.adapters.kaiheila import MessageSegment as Kook_MsgSeg
from nonebot.adapters.kaiheila.event import PrivateMessageEvent as Kook_PME
from nonebot.adapters.kaiheila.event import ChannelMessageEvent as Kook_CME

# qq官方协议
from nonebot.adapters.qq import Bot as QQ_Bot
from nonebot.adapters.qq.event import MessageEvent as QQ_ME, GroupAtMessageCreateEvent
from nonebot.adapters.qq import MessageSegment as QQ_MsgSeg
from nonebot.adapters.qq.event import GroupAtMessageCreateEvent as QQ_GME  # 群艾特信息
from nonebot.adapters.qq.event import C2CMessageCreateEvent as QQ_C2CME  # Q私聊信息
from nonebot.adapters.qq.event import DirectMessageCreateEvent as QQ_PME  # 频道私聊信息
from nonebot.adapters.qq.event import AtMessageCreateEvent as QQ_CME  # 频道艾特信息

from .data.db_control import db_control
from .image.image import *
from .image import image_to_bytes
from .config import plugin_config, driver, global_config, Config
from .utils import dict_keyword_replace, multiple_replace
from .data import reload_weapon_info, db_image
from .util import (
    get_weapon_info_test,
    check_msg_permission,
    init_blacklist,
    get_channel_info,
    ChannelInfo,
    cron_job,
    push_job,
)

require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler

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


async def _permission_check(bot: Bot, event: Event, matcher: Matcher, state: T_State):
    """检查消息来源权限
    return值无意义，主要是靠matcher.finish()阻断事件"""
    # 前缀限定判断
    if plugin_config.splatoon3_sole_prefix:
        plain_text = event.get_message().extract_plain_text().strip()
        if not plain_text.startswith("/"):
            await matcher.finish()
    # id定义
    default_id = 25252
    guid: Union[int, str] = default_id  # 服务器id
    gid: Union[int, str] = default_id  # Q群id
    cid: Union[int, str] = default_id  # 频道id
    uid: Union[int, str] = default_id  # 用户id
    state["_guid_"] = default_id
    state["_gid_"] = default_id
    state["_cid_"] = default_id
    state["_uid_"] = default_id

    bot_adapter = bot.adapter.get_name()
    bot_id = bot.self_id
    uid = event.get_user_id()
    state["_uid_"] = uid or default_id

    if isinstance(event, (V11_PME, V12_PME, Tg_PME, Kook_PME, QQ_PME, QQ_C2CME)):
        # 频道私聊
        if isinstance(event, (V11_PME, V12_PME, Tg_PME, Kook_PME, QQ_PME)):
            state["_msg_source_type_"] = "private"
            rule = plugin_config.splatoon3_permit_private
        # qq c2c私聊
        elif isinstance(event, QQ_C2CME):
            state["_msg_source_type_"] = "c2c"
            rule = plugin_config.splatoon3_permit_c2c
        if rule:
            ok = check_msg_permission(bot_adapter, bot_id, state["_msg_source_type_"], uid)
            if not ok:
                logger.info(f'{state["_msg_source_type_"]} 对象 {uid} 位于黑名单或关闭中，不予提供服务')
            return ok
        else:
            logger.info(f'插件配置项未允许 {state["_msg_source_type_"]} 类别用户触发查询')
            await matcher.finish()
    # 群聊
    elif isinstance(event, (V11_GME, V12_GME, Tg_GME, QQ_GME)):
        state["_msg_source_type_"] = "group"
        if plugin_config.splatoon3_permit_group:
            if isinstance(event, Tg_GME):
                gid = event.chat.id
            elif isinstance(event, (V11_GME, V12_GME)):
                gid = event.group_id
            elif isinstance(event, QQ_GME):
                gid = event.group_openid
            state["_gid_"] = gid
            ok = check_msg_permission(bot_adapter, bot_id, state["_msg_source_type_"], gid)
            if ok:
                # 再判断触发者是否有权限
                ok = check_msg_permission(bot_adapter, bot_id, "c2c", uid)
                if not ok:
                    logger.info(f"c2c 对象 {uid} 位于黑名单或关闭中，不予提供服务")
                return ok
            else:
                logger.info(f"group 对象 {gid} 位于黑名单或关闭中，不予提供服务")
                await matcher.finish()
        else:
            logger.info(f'插件配置项未允许 {state["_msg_source_type_"]} 类别用户触发查询')
            await matcher.finish()
    # 服务器频道
    elif isinstance(event, (V12_CME, Kook_CME, QQ_CME)):
        state["_msg_source_type_"] = "channel"
        if plugin_config.splatoon3_permit_channel:
            if isinstance(event, V12_CME):
                guid = event.guild_id
                cid = event.channel_id
            elif isinstance(event, Kook_CME):
                guid = event.extra.guild_id
                cid = event.group_id
            elif isinstance(event, QQ_CME):
                guid = event.guild_id
                cid = event.channel_id
            state["_guid_"] = guid
            state["_cid_"] = cid
            # 判断服务器是否有权限
            ok = check_msg_permission(bot_adapter, bot_id, "guild", guid)
            if ok:
                # 再判断频道是否有权限
                ok = check_msg_permission(bot_adapter, bot_id, "channel", cid)
                if ok:
                    # 再判断触发者是否有权限
                    ok = check_msg_permission(bot_adapter, bot_id, "private", uid)
                    if not ok:
                        logger.info(f"private 对象 {uid} 位于黑名单或关闭中，不予提供服务")
                    return ok
                else:
                    logger.info(f"channel 对象 {cid} 位于黑名单或关闭中，不予提供服务")
                    await matcher.finish()
            else:
                logger.info(f"guild 对象 {guid} 位于黑名单或关闭中，不予提供服务")
                await matcher.finish()
        else:
            logger.info(f'插件配置项未允许 {state["_msg_source_type_"]} 类别用户触发查询')
            await matcher.finish()
    # 单频道
    elif isinstance(event, Tg_CME):
        state["_msg_source_type_"] = "channel"
        if plugin_config.splatoon3_permit_channel:
            if isinstance(event, Tg_CME):
                cid = event.chat.id
            state["_cid_"] = cid
            ok = check_msg_permission(bot_adapter, bot_id, "channel", cid)
            if ok:
                # 再判断触发者是否有权限
                ok = check_msg_permission(bot_adapter, bot_id, "private", uid)
                if not ok:
                    logger.info(f"private 对象 {uid} 位于黑名单或关闭中，不予提供服务")
                return ok
            else:
                logger.info(f"channel 对象 {cid} 位于黑名单或关闭中，不予提供服务")
                await matcher.finish()
        else:
            logger.info(f'插件配置项未允许 {state["_msg_source_type_"]} 类别用户触发查询')
            await matcher.finish()
    # 其他
    else:
        state["_uid_"] = "unknown"
        ok = plugin_config.splatoon3_permit_unknown_src
        if not ok:
            logger.info(f"插件配置项未允许 unknown 类别用户触发查询")
        return ok


# 图 触发器  正则内需要涵盖所有的同义词
matcher_stage_group = on_regex("^[\\/.,，。]?[0-9]*(全部)?下*图+[ ]?$", priority=8, block=True)


# 图 触发器处理 二次判断正则前，已经进行了同义词替换，二次正则只需要判断最终词
@matcher_stage_group.handle(parameterless=[Depends(_permission_check)])
async def _(bot: Bot, event: Event):
    plain_text = event.get_message().extract_plain_text().strip()
    # 触发关键词  替换.。\/ 等前缀触发词
    plain_text = multiple_replace(plain_text, dict_keyword_replace)
    logger.info("同义文本替换后触发词为:" + plain_text + "\n")
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
        img = get_save_temp_image(plain_text, func, num_list, contest_match, rule_match)
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
        img = get_save_temp_image(plain_text, func, num_list, contest_match, rule_match)
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
    logger.info("同义文本替换后触发词为:" + plain_text + "\n")
    # 判断是否满足进一步正则
    _all = False
    if "全部" in plain_text:
        _all = True
    # 传递函数指针
    func = get_coop_stages_image
    # 获取图片
    img = get_save_temp_image(plain_text, func, _all)
    # 发送消息
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
    logger.info("同义文本替换后触发词为:" + plain_text + "\n")
    # 判断是否满足进一步正则
    # 随机武器
    if re.search("^随机武器.*$", plain_text):
        # 这个功能不能进行缓存，必须实时生成图
        # 测试数据库能否取到武器数据
        if not get_weapon_info_test():
            msg = "请机器人管理员先发送 更新武器数据 更新本地武器数据库后，才能使用随机武器功能"
            await send_msg(bot, event, msg)
        else:
            img = image_to_bytes(get_random_weapon_image(plain_text))
            # 发送消息
            await send_msg(bot, event, img)
    elif re.search("^祭典$", plain_text):
        # 传递函数指针
        func = get_festival_image
        # 获取图片
        img = get_save_temp_image(plain_text, func)
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
        img = get_save_temp_image(plain_text, func)
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
        img = get_save_temp_image(plain_text, func)
        # 发送图片
        await send_msg(bot, event, img)
        # 当优先帮助打开时，额外发送nso帮助
        if plugin_config.splatoon3_schedule_plugin_priority_mode:
            await send_msg(bot, event, "若需要查看完整的nso指令请发送 /nso帮助")

    elif re.search("^nso帮助$", plain_text):
        # 传递函数指针
        func = get_nso_help_image
        # 获取图片
        img = get_save_temp_image(plain_text, func)
        # 发送图片
        await send_msg(bot, event, img)

    # elif re.search("^装备$", plain_text):
    #     img = await get_screenshot(shot_url="https://splatoon3.ink/gear")
    #     # 发送图片
    #     await send_img(bot, event, img)


async def _guild_owner_check(bot: Bot, event: Event, matcher: Matcher, state: T_State):
    """服务器频道主人校验
    return值无意义，主要是靠matcher.finish()阻断事件"""
    channel_info: ChannelInfo
    if isinstance(event, (Kook_CME, QQ_CME)):
        guid = ""
        cid = ""
        uid = ""
        if isinstance(event, Kook_CME):
            guid = event.extra.guild_id
            cid = event.group_id
            uid = event.user_id
        elif isinstance(event, QQ_CME):
            guid = event.guild_id
            cid = event.channel_id
            uid = event.author.id
        guild_info = await get_channel_info(bot, "guild", guid)
        channel_info = await get_channel_info(bot, "channel", cid, guid)
        owner_id = guild_info.owner_id
        state["_channel_info_"] = channel_info
        if (uid == owner_id) or (uid in global_config.superusers):
            if uid == owner_id:
                state["_user_level_"] = "owner"
            if uid in global_config.superusers:
                state["_user_level_"] = "superuser"
            return True
        else:
            await matcher.finish()
    else:
        await matcher.finish()


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


async def send_msg(bot: Bot, event: Event, msg: str | bytes):
    """公用send_msg"""
    # 指定回复模式
    reply_mode = plugin_config.splatoon3_reply_mode

    if isinstance(msg, str):
        # 文字消息
        if isinstance(bot, V11_Bot):
            await bot.send(event, message=V11_MsgSeg.text(msg), reply_message=reply_mode)
        elif isinstance(bot, V12_Bot):
            await bot.send(event, message=V12_MsgSeg.text(msg), reply_message=reply_mode)
        elif isinstance(bot, Tg_Bot):
            if reply_mode:
                await bot.send(event, msg, reply_to_message_id=event.dict().get("message_id"))
            else:
                await bot.send(event, msg)
        elif isinstance(bot, Kook_Bot):
            await bot.send(event, message=Kook_MsgSeg.text(msg), reply_sender=reply_mode)
        elif isinstance(bot, QQ_Bot):
            await bot.send(event, message=QQ_MsgSeg.text(msg))

    elif isinstance(msg, bytes):
        # 图片
        img = msg
        if isinstance(bot, V11_Bot):
            try:
                await bot.send(event, message=V11_MsgSeg.image(file=img, cache=False), reply_message=reply_mode)
            except Exception as e:
                logger.warning(f"QQBot send error: {e}")
        elif isinstance(bot, V12_Bot):
            # onebot12协议需要先上传文件获取file_id后才能发送图片
            try:
                resp = await bot.upload_file(type="data", name="temp.png", data=img)
                file_id = resp["file_id"]
                if file_id:
                    await bot.send(event, message=V12_MsgSeg.image(file_id=file_id), reply_message=reply_mode)
            except Exception as e:
                logger.warning(f"QQBot send error: {e}")
        elif isinstance(bot, Tg_Bot):
            if reply_mode:
                await bot.send(event, Tg_File.photo(img), reply_to_message_id=event.dict().get("message_id"))
            else:
                await bot.send(event, Tg_File.photo(img))
        elif isinstance(bot, Kook_Bot):
            url = await bot.upload_file(img)
            await bot.send(event, Kook_MsgSeg.image(url), reply_sender=reply_mode)
        elif isinstance(bot, QQ_Bot):
            if not isinstance(event, GroupAtMessageCreateEvent):
                await bot.send(event, message=QQ_MsgSeg.file_image(img))
            else:
                # 目前q群只支持url图片，得想办法上传图片获取url
                kook_bot = None
                bots = nonebot.get_bots()
                for k, b in bots.items():
                    if isinstance(b, Kook_Bot):
                        kook_bot = b
                        break
                if kook_bot is not None:
                    # 使用kook的接口传图片
                    url = await kook_bot.upload_file(img)
                    # logger.info("url:" + url)
                    await bot.send(event, message=QQ_MsgSeg.image(url))


@driver.on_startup
async def startup():
    """nb启动时事件"""
    # 清空合成图片缓存表
    db_image.clean_image_temp()
    # 初始化黑名单字典
    init_blacklist()


@driver.on_shutdown
async def shutdown():
    """nb关闭时事件"""
    # 关闭数据库
    db_image.close()
    db_control.close()
    # 删除任务
    bots = nonebot.get_bots()
    for k in bots.keys():
        job_id = f"sp3_schedule_push_job_{k}"
        if scheduler.get_job(job_id):
            scheduler.remove_job(job_id)
            logger.info(f"remove job {job_id}!")


@driver.on_bot_connect
async def _(bot: Bot):
    """bot接入时事件"""
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
