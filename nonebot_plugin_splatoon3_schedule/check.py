import time
from typing import Union
from collections import deque
from datetime import datetime as dt, timedelta

from .utils.utils import get_msg_id
from .util import send_msg
from .config import plugin_config, global_config
from .data import db_control
from .data.utils import get_blacklist_msg_id
from .utils.bot import *

blacklist = {}
guilds_info = {}

# QPS限制配置
QPS_LIMIT_COUNT = 10  # 60秒内最多请求次数
QPS_LIMIT_TIME = 60  # 时间窗口(秒)

# 用户请求时间戳记录 {user_key: deque([timestamp1, timestamp2, ...])}
user_request_times = {}


def get_or_init(dictionary: dict, key: str, default=None):
    """字典赋值"""
    if default is None:
        default = {}
    if dictionary.get(key) is None:
        dictionary.update({key: default})
        return default
    else:
        return dictionary.get(key)


class ChannelInfo:
    """类 服务器或频道信息 ChannelInfo"""

    def __init__(
        self,
        bot_adapter,
        bot_id,
        source_type,
        source_id,
        source_name,
        owner_id,
        source_parent_id=None,
        source_parent_name=None,
    ):
        self.bot_adapter = bot_adapter
        self.bot_id = bot_id
        self.source_type = source_type
        self.source_id = source_id
        self.source_name = source_name
        self.owner_id = owner_id
        self.source_parent_id = source_parent_id
        self.source_parent_name = source_parent_name


async def get_channel_info(
    bot: any, source_type: str, _id: str, _parent_id: str = None
) -> ChannelInfo:
    """获取服务器或频道信息"""
    global guilds_info
    bot_adapter = bot.adapter.get_name()
    bot_id = bot.self_id
    # 获取字典信息
    adapter_group = guilds_info.get(bot_adapter)
    if adapter_group is not None:
        account_group = adapter_group.get(bot_id)
        if account_group is not None:
            type_group = account_group.get(source_type)
            if type_group is not None:
                guild_info = type_group.get(_id)
                if guild_info is not None:
                    owner_id = guild_info["owner_id"]
                    source_name = guild_info["source_name"]
                    _parent_name = guild_info["source_name"]
                    return ChannelInfo(
                        bot_adapter,
                        bot_id,
                        source_type,
                        _id,
                        source_name,
                        owner_id,
                        _parent_id,
                        _parent_name,
                    )
    # 写入新记录
    owner_id = ""
    source_name = ""
    _parent_name = None
    if source_type == "guild":
        if isinstance(bot, Kook_Bot):
            guild_info = await bot.guild_view(guild_id=_id)
            owner_id = guild_info.user_id
            source_name = guild_info.name
        elif isinstance(bot, QQ_Bot):
            guild_info = await bot.get_guild(guild_id=_id)
            owner_id = guild_info.owner_id
            source_name = guild_info.name
    elif source_type == "channel":
        if _parent_id is not None:
            # 提供了 _parent_id 说明为服务器频道
            if isinstance(bot, Kook_Bot):
                guild_info = await bot.guild_view(guild_id=_parent_id)
                _parent_name = guild_info.name

                channel_info = await bot.channel_view(target_id=_id)
                owner_id = channel_info.user_id
                source_name = channel_info.name
            elif isinstance(bot, QQ_Bot):
                guild_info = await bot.get_guild(guild_id=_parent_id)
                _parent_name = guild_info.name

                channel_info = await bot.get_channel(channel_id=_id)
                owner_id = channel_info.owner_id
                source_name = channel_info.name
        else:
            if isinstance(bot, Kook_Bot):
                channel_info = await bot.channel_view(target_id=_id)
                owner_id = channel_info.user_id
                source_name = channel_info.name
            elif isinstance(bot, QQ_Bot):
                channel_info = await bot.get_channel(channel_id=_id)
                owner_id = channel_info.owner_id
                source_name = channel_info.name
    adapter_group = get_or_init(guilds_info, bot_adapter)
    account_group = get_or_init(adapter_group, bot_id)
    type_group = get_or_init(account_group, source_type)
    type_group.update({"owner_id": owner_id})
    type_group.update({"name": source_name})
    type_group.update({"parent_id": _parent_id})
    type_group.update({"parent_name": _parent_name})
    return ChannelInfo(
        bot_adapter,
        bot_id,
        source_type,
        _id,
        source_name,
        owner_id,
        _parent_id,
        _parent_name,
    )


def init_blacklist() -> None:
    """初始化黑名单字典"""
    global blacklist
    results = db_control.get_all_blacklist()

    # 遍历数组字典，重新整合为新字典
    for item in results:
        adapter_group = get_or_init(blacklist, item["bot_adapter"])
        account_group = get_or_init(adapter_group, item["bot_id"])
        type_group = get_or_init(account_group, item["msg_source_type"])
        type_group.update(
            {
                item["msg_source_id"]: {
                    "msg_source_name": item["msg_source_name"],
                    "status": item["status"],
                    "active_push": item["active_push"],
                }
            }
        )


# 检查消息来源权限
def check_msg_permission(
    bot_adapter: str, bot_id: str, msg_source_type: str, msg_source_id: str
) -> bool:
    """检查消息来源"""
    global blacklist
    adapter_group = blacklist.get(bot_adapter)
    if adapter_group is not None:
        account_group = adapter_group.get(bot_id)
        if account_group is not None:
            type_group = account_group.get(msg_source_type)
            if type_group is not None:
                info = type_group.get(msg_source_id)
                if info is not None:
                    status = info["status"]
                    return status
    return True


async def _check_session_blacklist_handler(bot: Bot, event: Event, matcher: Matcher):
    """校验用户是否在黑名单"""
    platform = bot.adapter.get_name()
    user_id = event.get_user_id()
    user_key = get_msg_id(platform, user_id)
    # 黑名单列表
    black_l = await get_blacklist_msg_id()
    if user_key in black_l:
        msg = "你已无权使用小鱿鱿bot，若存在误封，请联系q群827977720"
        logger.warning(f"黑名单 {user_key} 已禁止使用bot")
        await send_msg(bot, event, msg=msg)
        matcher.stop_propagation()
        await matcher.finish()


async def _check_session_qps_limit_handler(bot: Bot, event: Event, matcher: Matcher):
    """校验用户请求qps"""
    platform = bot.adapter.get_name()
    user_id = event.get_user_id()
    user_key = get_msg_id(platform, user_id)

    # QPS检测
    current_time = time.time()
    if user_key not in user_request_times:
        user_request_times[user_key] = deque()

    # 移除超过时间窗口的记录
    while (
        user_request_times[user_key]
        and current_time - user_request_times[user_key][0] > QPS_LIMIT_TIME
    ):
        user_request_times[user_key].popleft()

    # 检查请求次数是否超过限制
    if len(user_request_times[user_key]) >= QPS_LIMIT_COUNT:
        msg = "请勿频繁请求"
        await send_msg(bot, event, msg=msg)
        matcher.stop_propagation()
        await matcher.finish()

    # 记录当前请求时间
    user_request_times[user_key].append(current_time)


async def _permission_check(bot: Bot, event: Event, matcher: Matcher, state: T_State):
    """检查消息来源权限
    return值无意义，主要是靠matcher.finish()阻断事件"""
    # 前缀限定判断
    if plugin_config.splatoon3_sole_prefix:
        plain_text = event.get_message().extract_plain_text().strip()
        if not plain_text.startswith("/"):
            await matcher.finish()

    # xyy qps校验
    await _check_session_qps_limit_handler(bot, event, matcher)
    # xyy 黑名单校验
    await _check_session_blacklist_handler(bot, event, matcher)

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
        else:
            rule = plugin_config.splatoon3_permit_unknown_src
        if rule:
            ok = check_msg_permission(
                bot_adapter, bot_id, state["_msg_source_type_"], uid
            )
            if not ok:
                logger.info(
                    f'{state["_msg_source_type_"]} 对象 {uid} 位于黑名单或关闭中，不予提供服务'
                )
            return ok
        else:
            logger.info(
                f'插件配置项未允许 {state["_msg_source_type_"]} 类别用户触发查询'
            )
            await matcher.finish()
    # 群聊
    elif isinstance(event, (V11_GME, V12_GME, Tg_GME, QQ_GATME, QQ_GME)):
        state["_msg_source_type_"] = "group"
        if plugin_config.splatoon3_permit_group:
            if isinstance(event, Tg_GME):
                gid = event.chat.id
            elif isinstance(event, (V11_GME, V12_GME)):
                gid = event.group_id
            elif isinstance(event, (QQ_GATME, QQ_GME)):
                gid = event.group_openid
            state["_gid_"] = gid
            ok = check_msg_permission(
                bot_adapter, bot_id, state["_msg_source_type_"], gid
            )
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
            logger.info(
                f'插件配置项未允许 {state["_msg_source_type_"]} 类别用户触发查询'
            )
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
                        logger.info(
                            f"private 对象 {uid} 位于黑名单或关闭中，不予提供服务"
                        )
                    return ok
                else:
                    logger.info(f"channel 对象 {cid} 位于黑名单或关闭中，不予提供服务")
                    await matcher.finish()
            else:
                logger.info(f"guild 对象 {guid} 位于黑名单或关闭中，不予提供服务")
                await matcher.finish()
        else:
            logger.info(
                f'插件配置项未允许 {state["_msg_source_type_"]} 类别用户触发查询'
            )
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
            logger.info(
                f'插件配置项未允许 {state["_msg_source_type_"]} 类别用户触发查询'
            )
            await matcher.finish()
    # 其他
    else:
        state["_uid_"] = "unknown"
        ok = plugin_config.splatoon3_permit_unknown_src
        if not ok:
            logger.info(f"插件配置项未允许 unknown 类别用户触发查询")
        return ok


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
