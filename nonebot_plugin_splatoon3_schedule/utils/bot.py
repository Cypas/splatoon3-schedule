import nonebot
from nonebot.internal.adapter import Event
from nonebot.internal.matcher import Matcher
from nonebot.internal.params import Depends
from nonebot.params import RegexGroup
from nonebot.plugin import PluginMetadata
from nonebot import on_regex, Bot, params, require, on_command
from nonebot.permission import SUPERUSER
from nonebot.typing import T_State
from nonebot import logger

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
from nonebot.adapters.qq.message import Message as QQ_Msg
from nonebot.adapters.qq.models import MessageKeyboard as QQ_MsgKeyboard, MessageMarkdown as QQ_MsgMarkdown
from nonebot.adapters.qq import AuditException as QQ_AuditException,ActionFailed as QQ_ActionFailed
from nonebot.adapters.qq.event import GroupAtMessageCreateEvent as QQ_GATME # 群艾特信息
from nonebot.adapters.qq.event import GroupMessageCreateEvent as QQ_GME  # 群全量消息
from nonebot.adapters.qq.event import C2CMessageCreateEvent as QQ_C2CME  # Q私聊信息
from nonebot.adapters.qq.event import DirectMessageCreateEvent as QQ_PME  # 频道私聊信息
from nonebot.adapters.qq.event import AtMessageCreateEvent as QQ_CME  # 频道艾特信息

# discord协议
from nonebot.adapters.discord import Bot as Dc_Bot
from nonebot.adapters.discord import Message as Dc_Msg
from nonebot.adapters.discord import MessageSegment as Dc_MsgSeg
from nonebot.adapters.discord import MessageEvent as Dc_ME
from nonebot.adapters.discord import DirectMessageCreateEvent as Dc_PME  # 私信
from nonebot.adapters.discord import GuildMessageCreateEvent as Dc_GME  # 服务器频道消息


# bot
All_BOT = (V11_Bot, V12_Bot, Kook_Bot, Tg_Bot, QQ_Bot, Dc_Bot)
# 需要限制qq平台停用的功能也应该是在该功能前直接阻断，而不是后续再进行过滤，故弃用All_BOT_Without_QQ

# 公开发言消息类型
All_Group_Message = (Kook_CME, Tg_GME, Tg_CME, QQ_CME, QQ_GATME, QQ_GME, V11_GME, V12_GME, V12_CME, Dc_GME)
All_Group_Message_Without_QQ_G = (Kook_CME, Tg_GME, Tg_CME, QQ_CME, V11_GME, V12_GME, V12_CME, Dc_GME)
# 私聊消息
All_Private_Message = (Kook_PME, Tg_PME, QQ_PME, QQ_C2CME, V11_PME, V12_PME, Dc_PME)