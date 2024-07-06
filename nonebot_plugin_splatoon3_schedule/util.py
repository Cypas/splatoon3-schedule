import time
from nonebot.adapters.qq import AuditException, ActionFailed

from .config import plugin_config
from .image.image import get_save_temp_image, get_stages_image, get_coop_stages_image, get_events_image
from .utils.utils import get_time_now_china
from .data import db_control, db_image
from .utils.bot import *


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
        for _push_job in push_jobs:
            # active_push = push_job.get("active_push")
            msg_source_type = _push_job.get("msg_source_type")
            msg_source_id = _push_job.get("msg_source_id")
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
        for _push_job in push_jobs:
            # active_push = push_job.get("active_push")
            msg_source_type = _push_job.get("msg_source_type")
            msg_source_id = _push_job.get("msg_source_id")
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
    image = await get_save_temp_image("图", func, num_list, contest_match, rule_match)
    await send_channel_msg(bot, source_id, image)
    time.sleep(1)
    # 发送 工
    func = get_coop_stages_image
    _all = False
    image = await get_save_temp_image("工", func, _all)
    await send_channel_msg(bot, source_id, image)
    time.sleep(1)
    # 发送 活动
    func = get_events_image
    image = await get_save_temp_image("活动", func)
    await send_channel_msg(bot, source_id=source_id, msg=image)


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
