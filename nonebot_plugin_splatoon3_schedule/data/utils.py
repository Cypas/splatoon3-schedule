import json


async def get_or_set_plugin_data(key, value=None):
    """获取或设置插件数据"""
    from nonebot import require

    require("nonebot_plugin_datastore")
    from nonebot_plugin_datastore import get_plugin_data

    if value is None:
        # 读取配置
        value = await get_plugin_data("sp3_xyy_bot").config.get(key)
        return value
    else:
        # 存储配置
        await get_plugin_data("sp3_xyy_bot").config.set(key, value)
        return value


async def get_blacklist_msg_id():
    """使用插件数据获取黑名单msg_id列表"""
    key = "xyy_blacklist_msg_id"
    black_str = await get_or_set_plugin_data(key)
    if not black_str:
        return []
    black_l = json.loads(black_str)
    return black_l


async def add_blacklist_msg_id(msg_id: str):
    """添加黑名单用户列表"""
    key = "xyy_blacklist_msg_id"
    black_l = await get_blacklist_msg_id()
    black_l.append(msg_id)
    black_str = json.dumps(black_l)
    await get_or_set_plugin_data(key, black_str)


async def del_blacklist_msg_id(msg_id: str):
    """删除黑名单用户"""
    key = "xyy_blacklist_msg_id"
    black_l = await get_blacklist_msg_id()
    while msg_id in black_l:
        black_l.remove(msg_id)
    black_str = json.dumps(black_l)
    await get_or_set_plugin_data(key, black_str)
