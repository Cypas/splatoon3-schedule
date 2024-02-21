<div align="center">
  <a href="https://v2.nonebot.dev/store"><img src="https://github.com/A-kirami/nonebot-plugin-template/blob/resources/nbp_logo.png" width="180" height="180" alt="NoneBotPluginLogo"></a>
  <br>
  <p><img src="https://github.com/A-kirami/nonebot-plugin-template/blob/resources/NoneBotPlugin.svg" width="240" alt="NoneBotPluginText"></p>
</div>

<div align="center">

# nonebot-plugin-splatoon3-schedule

_✨ splatoon3游戏日程查询插件 ✨_

<p align="center">
<a href="./LICENSE">
    <img src="https://img.shields.io/github/license/Cypas/splatoon3-schedule.svg" alt="license">
</a>
<a href="https://pypi.python.org/pypi/nonebot-plugin-splatoon3-schedule">
  <img alt="PyPI - Downloads" src="https://img.shields.io/pypi/dm/nonebot-plugin-splatoon3-schedule">
</a>
<a href="https://pypi.python.org/pypi/nonebot-plugin-splatoon3-schedule">
    <img src="https://img.shields.io/pypi/v/nonebot-plugin-splatoon3-schedule.svg" alt="pypi">
</a>
<img src="https://img.shields.io/badge/python-3.9+-blue.svg" alt="python">
<br />
<a href="https://onebot.dev/">
  <img src="https://img.shields.io/badge/OneBot-v11-black?style=social&logo=data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEAAAABABAMAAABYR2ztAAAAIVBMVEUAAAAAAAADAwMHBwceHh4UFBQNDQ0ZGRkoKCgvLy8iIiLWSdWYAAAAAXRSTlMAQObYZgAAAQVJREFUSMftlM0RgjAQhV+0ATYK6i1Xb+iMd0qgBEqgBEuwBOxU2QDKsjvojQPvkJ/ZL5sXkgWrFirK4MibYUdE3OR2nEpuKz1/q8CdNxNQgthZCXYVLjyoDQftaKuniHHWRnPh2GCUetR2/9HsMAXyUT4/3UHwtQT2AggSCGKeSAsFnxBIOuAggdh3AKTL7pDuCyABcMb0aQP7aM4AnAbc/wHwA5D2wDHTTe56gIIOUA/4YYV2e1sg713PXdZJAuncdZMAGkAukU9OAn40O849+0ornPwT93rphWF0mgAbauUrEOthlX8Zu7P5A6kZyKCJy75hhw1Mgr9RAUvX7A3csGqZegEdniCx30c3agAAAABJRU5ErkJggg==" alt="onebot">
</a>
<a href="https://onebot.dev/">
  <img src="https://img.shields.io/badge/OneBot-v12-black?style=social&logo=data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEAAAABABAMAAABYR2ztAAAAIVBMVEUAAAAAAAADAwMHBwceHh4UFBQNDQ0ZGRkoKCgvLy8iIiLWSdWYAAAAAXRSTlMAQObYZgAAAQVJREFUSMftlM0RgjAQhV+0ATYK6i1Xb+iMd0qgBEqgBEuwBOxU2QDKsjvojQPvkJ/ZL5sXkgWrFirK4MibYUdE3OR2nEpuKz1/q8CdNxNQgthZCXYVLjyoDQftaKuniHHWRnPh2GCUetR2/9HsMAXyUT4/3UHwtQT2AggSCGKeSAsFnxBIOuAggdh3AKTL7pDuCyABcMb0aQP7aM4AnAbc/wHwA5D2wDHTTe56gIIOUA/4YYV2e1sg713PXdZJAuncdZMAGkAukU9OAn40O849+0ornPwT93rphWF0mgAbauUrEOthlX8Zu7P5A6kZyKCJy75hhw1Mgr9RAUvX7A3csGqZegEdniCx30c3agAAAABJRU5ErkJggg==" alt="onebot">
</a>
<a href="https://github.com/nonebot/adapter-telegram">
<img src="https://img.shields.io/badge/telegram-Adapter-lightgrey?style=social&logo=telegram" alt="telegram">
</a>
<a href="https://github.com/Tian-que/nonebot-adapter-kaiheila">
<img src="https://img.shields.io/badge/kook-Adapter-lightgrey?style=social" alt="kook">
</a>
<a href="https://github.com/nonebot/adapter-qq">
<img src="https://img.shields.io/badge/QQ-Adapter-lightgrey?style=social" alt="QQ">
</a>
</p>

</div>


## 📖 介绍

- 一个基于nonebot2框架的splatoon3游戏日程查询插件,支持onebot11,onebot12,[telegram](https://github.com/nonebot/adapter-telegram)协议,[kook](https://github.com/Tian-que/nonebot-adapter-kaiheila)协议,[QQ官方bot](https://github.com/nonebot/adapter-qq)协议
- 全部查询图片,全部采用pillow精心绘制,图片效果可查看下面的[效果图](#效果图)
- 建议配合我做的[nso查询插件](https://github.com/Cypas/splatoon3-nso)一起使用

> 也可以邀请我目前做好的小鱿鱿bot直接加入频道或群聊，[kook频道bot](https://www.kookapp.cn/app/oauth2/authorize?id=22230&permissions=4096&client_id=4Kn4ukf1To48rax8&redirect_uri=&scope=bot),[qq群聊bot](https://qun.qq.com/qunpro/robot/qunshare?robot_appid=102083290&robot_uin=3889005657)

> 小鱿鱿官方kook频道:[kook频道](https://kook.top/mkjIOn)

## 💿 安装

<details>
<summary>使用 nb-cli 安装</summary>
在 nonebot2 项目的根目录下打开命令行, 输入以下指令即可安装

    nb plugin install nonebot-plugin-splatoon3-schedule

</details>


<details>
<summary>使用包管理器安装</summary>
在 nonebot2 项目的插件目录下, 打开命令行, 根据你使用的包管理器, 输入相应的安装命令
<details>
<summary>pdm</summary>

    pdm add nonebot-plugin-splatoon3-schedule
</details>

<details>
<summary>poetry</summary>

    poetry add nonebot-plugin-splatoon3-schedule
</details>


</details>


## ⚙️ 配置

以下配置项均为可选值，根据自己需要将配置项添加至nonebot目录的`.env.prod`文件

|                   配置项                   | 必填 | 值类型  |  默认值  |                      说明                      |
|:---------------------------------------:|:--:|:----:|:-----:|:--------------------------------------------:|
|         splatoon3_proxy_address         | 否  | str  |  ""   |           代理地址，格式为 127.0.0.1:20171           |
|          splatoon3_reply_mode           | 否  | bool | False |       指定回复模式，开启后将通过触发词的消息进行回复，默认为False       |
|        splatoon3_permit_private         | 否  | bool | False |             是否允许频道私聊触发，默认为False              |
|          splatoon3_permit_c2c           | 否  | bool | False |           是否允许qq私聊(c2c)触发，默认为False           |
|        splatoon3_permit_channel         | 否  | bool | True  |               是否允许频道触发，默认为True               |
|         splatoon3_permit_group          | 否  | bool | True  |          是否允许群聊(如qq群，tg群)触发，默认为True          |
|      splatoon3_permit_unknown_src       | 否  | bool | False |             是否允许未知来源触发，默认为False              |
|          splatoon3_sole_prefix          | 否  | bool | False |                  限制消息触发前缀为/                  |
|    splatoon3_guild_owner_switch_push    | 否  | bool | False |   频道服务器拥有者是否允许开关主动推送功能(为False时仅允许管理员开启关闭)    |
|        splatoon3_is_official_bot        | 否  | bool | False |          是否是官方小鱿鱿bot(会影响输出的帮助图片内容)           |
| splatoon3_schedule_plugin_priority_mode | 否  | bool | False | 日程插件的帮助菜单优先模式(会影响帮助菜单由哪个插件提供，该配置项与nso查询插件公用) |

<details>
<summary>示例配置</summary>
  
```env
# splatoon3-schedule示例配置
splatoon3_proxy_address = "" #代理地址
splatoon3_reply_mode = False #指定回复模式
splatoon3_permit_private = False #是否允许频道私聊触发
splatoon3_permit_c2c = False #是否允许qq私聊(c2c)触发
splatoon3_permit_channel = True #是否允许频道触发
splatoon3_permit_group = True # 是否允许群聊(如qq群，tg群)触发
splatoon3_permit_unkown_src = False #是否允许未知来源触发
splatoon3_sole_prefix = False # 限制消息触发前缀为/
splatoon3_guild_owner_switch_push = False # 频道服务器拥有者是否允许开关主动推送功能(为False时仅允许管理员开启关闭)
splatoon3_is_official_bot = False	# 是否是小鱿鱿bot(会影响输出的帮助图片内容)
splatoon3_schedule_plugin_priority_mode = False #日程插件的帮助菜单优先模式(会影响帮助菜单由哪个插件提供，该配置项与nso查询插件公用)
```

</details>

## 🎉 使用
### 指令表
<details>
<summary>指令帮助手册</summary>

![help.png](images/help.png)

</details>


### 效果图
<details>
<summary>对战查询</summary>

![stages.png](images/stages.png)

</details>
<details>
<summary>打工查询</summary>

![coop.png](images/coop.jpg)

</details>
<details>
<summary>活动</summary>

![events.png](images/events.png)

</details>
<details>
<summary>祭典</summary>

![festival.png](images/festival.png)

</details>
<details>
<summary>随机武器</summary>

![random_weapon.png](images/random_weapon.png)

</details>

## ✨喜欢的话就点个star✨吧，球球了QAQ

## 鸣谢

- https://splatoon3.ink 日程数据来源
- https://splatoonwiki.org 武器数据来源

## ⏳ Star 趋势

[![Stargazers over time](https://starchart.cc/Cypas/splatoon3-schedule.svg)](https://starchart.cc/Cypas/splatoon3-schedule)
