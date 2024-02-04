import time
from typing import Union
from nonebot import Bot, logger, get_driver
import threading

# kook协议
from nonebot.adapters.kaiheila import Bot as Kook_Bot
from nonebot.adapters.kaiheila import MessageSegment as Kook_MsgSeg
from nonebot.adapters.kaiheila.event import ChannelMessageEvent as Kook_CME

# qq官方协议
from nonebot.adapters.qq import Bot as QQ_Bot, AuditException
from nonebot.adapters.qq import MessageSegment as QQ_MsgSeg
from nonebot.adapters.qq.event import AtMessageCreateEvent as QQ_CME
from nonebot.exception import ActionFailed

# telegram 协议
from nonebot.adapters.telegram import Bot as Tg_Bot
from nonebot.adapters.telegram.event import MessageEvent as Tg_ME
from nonebot.adapters.telegram import MessageSegment as Tg_MsgSeg
from nonebot.adapters.telegram.message import File as Tg_File

from . import get_save_temp_image, get_stages_image, get_coop_stages_image, get_events_image
from .utils.utils import get_time_now_china
from .data import db_control, db_image

blacklist = {}
guilds_info = {}


def get_weapon_info_test() -> bool:
    """测试武器数据库能否取到数据"""
    res = db_image.get_weapon_info("", "", "", "")
    if res is not None:
        return True
    else:
        return False


def write_weapon_trans_dict() -> None:
    """写出武器翻译字典"""
    weapon_trans_dict = db_image.get_all_weapon_info()
    if len(weapon_trans_dict) > 0:
        with open("weapon_trans_dict.txt", "a") as file:
            file.write("{")
        for val in weapon_trans_dict:
            # s += '"' + val["name"] + '":"' + val["zh_name"] + '",'
            s = '"{}":"{}",'.format(val["name"], val["zh_name"])
            with open("weapon_trans_dict.txt", "a") as file:
                file.write(s)
        with open("weapon_trans_dict.txt", "a") as file:
            file.write("}")


# 检查消息来源权限
def check_msg_permission(bot_adapter: str, bot_id: str, msg_source_type: str, msg_source_id: str) -> bool:
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


def get_or_init(dictionary: dict, key: str, default=None):
    """字典赋值"""
    if default is None:
        default = {}
    if dictionary.get(key) is None:
        dictionary.update({key: default})
        return default
    else:
        return dictionary.get(key)


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


async def get_channel_info(bot: any, source_type: str, _id: str, _parent_id: str = None) -> ChannelInfo:
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
                        bot_adapter, bot_id, source_type, _id, source_name, owner_id, _parent_id, _parent_name
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
    return ChannelInfo(bot_adapter, bot_id, source_type, _id, source_name, owner_id, _parent_id, _parent_name)


async def cron_job(bot: Bot, bot_adapter: str, bot_id: str):
    """定时任务， 每1分钟每个bot执行"""
    push_jobs = db_control.get_all_push(bot_adapter, bot_id)
    now = get_time_now_china()

    # 非kook，qqbot机器人不处理
    if not isinstance(bot, (Kook_Bot, QQ_Bot)):
        return

    # 两小时推送一次
    if not (now.hour % 2 == 0 and now.minute == 0):
        # logger.info(f"不在时间段，当前时间{now.hour} : {now.minute}")
        return
    if len(push_jobs) > 0:
        for push_job in push_jobs:
            # active_push = push_job.get("active_push")
            msg_source_type = push_job.get("msg_source_type")
            msg_source_id = push_job.get("msg_source_id")
            # 目前仅开启频道推送
            if msg_source_type == "channel":
                await send_push(bot, msg_source_id)


async def push_job(bot: Bot, bot_adapter: str, bot_id: str):
    """推送定时任务， 每两小时执行一次"""
    push_jobs = db_control.get_all_push(bot_adapter, bot_id)

    # 非kook，qqbot机器人不处理
    if not isinstance(bot, (Kook_Bot, QQ_Bot)):
        return

    if len(push_jobs) > 0:
        for push_job in push_jobs:
            # active_push = push_job.get("active_push")
            msg_source_type = push_job.get("msg_source_type")
            msg_source_id = push_job.get("msg_source_id")
            # 目前仅开启频道推送
            if msg_source_type == "channel":
                await send_push(bot, msg_source_id)


async def send_push(bot: Bot, source_id):
    """频道主动推送"""
    logger.info(f"即将主动推送消息")
    # 发送 图
    func = get_stages_image
    num_list = [0]
    contest_match = None
    rule_match = None
    image = get_save_temp_image("图", func, num_list, contest_match, rule_match)
    await send_channel_msg(bot, source_id, image)
    time.sleep(1)
    # 发送 工
    func = get_coop_stages_image
    _all = False
    image = get_save_temp_image("工", func, _all)
    await send_channel_msg(bot, source_id, image)
    time.sleep(1)
    # 发送 活动
    func = get_events_image
    image = get_save_temp_image("活动", func)
    await send_channel_msg(bot, source_id=source_id, msg=image)


async def send_channel_msg(bot: Bot, source_id, msg: str | bytes):
    """公用发送频道消息"""
    if isinstance(msg, str):
        # 文字消息
        if isinstance(bot, Kook_Bot):
            await bot.send_channel_msg(channel_id=source_id, message=Kook_MsgSeg.text(msg))
        elif isinstance(bot, QQ_Bot):
            try:
                await bot.send_to_channel(channel_id=source_id, message=QQ_MsgSeg.text(msg))
            except AuditException as e:
                logger.warning(f"主动消息审核结果为{e.__dict__}")
            except ActionFailed as e:
                logger.warning(f"主动消息发送失败，api操作结果为{e.__dict__}")
        elif isinstance(bot, Tg_Bot):
            await bot.send_message(chat_id=source_id, text=msg)
    elif isinstance(msg, bytes):
        # 图片
        img = msg
        if isinstance(bot, Kook_Bot):
            url = await bot.upload_file(img)
            await bot.send_channel_msg(channel_id=source_id, message=Kook_MsgSeg.image(url))
        elif isinstance(bot, QQ_Bot):
            try:
                await bot.send_to_channel(channel_id=source_id, message=QQ_MsgSeg.file_image(img))
            except AuditException as e:
                logger.warning(f"主动消息审核结果为{e.__dict__}")
            except ActionFailed as e:
                logger.warning(f"主动消息发送失败，api操作结果为{e.__dict__}")
        elif isinstance(bot, Tg_Bot):
            await bot.send_photo(source_id, img)


async def send_private_msg(bot: Bot, source_id, msg: str | bytes, event=None):
    """公用发送私聊消息"""
    if isinstance(msg, str):
        # 文字消息
        if isinstance(bot, Kook_Bot):
            await bot.send_private_msg(user_id=source_id, message=Kook_MsgSeg.text(msg))
        elif isinstance(bot, QQ_Bot):
            try:
                if event:
                    await bot.send_to_dms(guild_id=event.guild_id, message=msg, msg_id=event.id)
            except AuditException as e:
                logger.warning(f"主动消息审核结果为{e.__dict__}")
            except ActionFailed as e:
                logger.warning(f"主动消息发送失败，api操作结果为{e.__dict__}")
        elif isinstance(bot, Tg_Bot):
            await bot.send_message(chat_id=source_id, text=msg)

    elif isinstance(msg, bytes):
        # 图片
        img = msg
        if isinstance(bot, Kook_Bot):
            url = await bot.upload_file(img)
            await bot.send_private_msg(user_id=source_id, message=Kook_MsgSeg.image(url))
        elif isinstance(bot, QQ_Bot):
            try:
                await bot.send_to_dms(guild_id=event.guild_id, message=QQ_MsgSeg.file_image(img), msg_id=event.id)
            except AuditException as e:
                logger.warning(f"主动消息审核结果为{e.__dict__}")
            except ActionFailed as e:
                logger.warning(f"主动消息发送失败，api操作结果为{e.__dict__}")
        elif isinstance(bot, Tg_Bot):
            await bot.send_photo(source_id, img)
