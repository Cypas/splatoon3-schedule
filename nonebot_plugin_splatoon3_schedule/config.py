from typing import List, Union

from nonebot import get_driver
from pydantic import BaseModel, validator


# 其他地方出现的类似 from .. import config，均是从 __init__.py 导入的 Config 实例
class Config(BaseModel):
    # 默认 proxy = None 表示不使用代理进行连接
    splatoon3_proxy_address: str = ""
    # 是否允许频道私聊消息回应，默认False
    splatoon3_permit_private: bool = False
    # 是否允许qq私聊(c2c)消息回应，默认False
    splatoon3_permit_c2c: bool = False
    # 是否允许频道消息回应，默认False
    splatoon3_permit_channel: bool = True
    # 是否允许群聊消息回应(如qq群，tg群)，默认True
    splatoon3_permit_group: bool = True
    # 是否允许未知来源消息回应，默认False
    splatoon3_permit_unknown_src: bool = False
    # 指定回复模式，开启后将通过触发词的消息进行回复
    splatoon3_reply_mode: bool = False
    # 限制消息触发前缀为/
    splatoon3_sole_prefix: bool = False
    # 频道服务器拥有者是否允许开关主动推送功能(为False时仅允许管理员开启关闭)
    splatoon3_guild_owner_switch_push: bool = False
    # 是否是官方小鱿鱿bot(会影响输出的帮助图片内容)
    splatoon3_is_official_bot: bool = False
    # 日程插件优先模式(会影响帮助图片内容，该配置项与nso查询插件公用)
    splatoon3_schedule_plugin_priority_mode: bool = False


# 本地测试时由于不启动 driver，需要将下面三行注释并取消再下面两行的注释
driver = get_driver()
global_config = driver.config
plugin_config = Config.parse_obj(global_config)

# driver = None
# global_config = None
# plugin_config = Config()
