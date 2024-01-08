import asyncio
from nonebot_plugin_splatoon3_schedule import reload_weapon_info
from nonebot_plugin_splatoon3_schedule.image.image import *
from nonebot_plugin_splatoon3_schedule.util import write_weapon_trans_dict, init_blacklist, check_msg_permission

# 测试打工图片
# res = get_coop_stages_image(True)
# res.show()


# # 测试 旧版 随机武器
# res = get_random_weapon(weapon1=None, weapon2=None)
# file = open('../output/random_weapon.jpg', "wb")
# file.write(res)

# 测试nonebot 打工 命令文本触发
# plain_text = "工"
# # 传递函数指针
# func = get_coop_stages_image
# res = get_save_temp_image(plain_text, func, False)
# img = res


# 测试nonebot 对战 命令文本触发
# re_tuple = ("", None, "下下", "挑战", None)
# re_list = []
# for k, v in enumerate(re_tuple):
#     # 遍历正则匹配字典进行替换文本
#     re_list.append(dict_keyword_replace.get(v, v))
# logger.info("同义文本替换后触发词为:" + json.dumps(re_list, ensure_ascii=False))
# # 输出格式为 ["", null, "下下", "挑战", null] 涉及?匹配且没有提供该值的是null
# # 索引 全部 下 匹配1 匹配2
#
# plain_text = ""
# if re_list[0]:
#     plain_text = plain_text + re_list[0]
# elif re_list[1]:
#     plain_text = plain_text + re_list[1]
# elif re_list[2]:
#     plain_text = plain_text + re_list[2]
# if re_list[3]:
#     plain_text = plain_text + re_list[3]
# if re_list[4]:
#     plain_text = plain_text + re_list[4]
#
# num_list: list = []
# contest_match = None
# rule_match = None
# flag_match = True
#
# # 计算索引列表
# if re_list[1]:
#     # 含有全部
#     num_list = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
# elif re_list[2]:
#     # 含有 下
#     splits = re_list[2].split("下")  # 返回拆分数组
#     lens = len(splits) - 1  # 返回拆分次数-1
#     num_list = list(set([lens]))
#     num_list.sort()
# elif re_list[0]:
#     # 数字索引
#     num_list = list(set([int(x) for x in re_list[0]]))
#     num_list.sort()
# else:
#     num_list = [0]
#
# # 计算比赛和规则
# if re_list[3] and re_list[4]:
#     # 双匹配
#     # 判断第一个参数是比赛还是规则
#     if re_list[3] in dict_contest_trans and re_list[4] in dict_rule_trans:
#         # 比赛 规则
#         contest_match = re_list[3]
#         rule_match = re_list[4]
#     elif re_list[3] in dict_rule_trans and re_list[4] in dict_contest_trans:
#         # 规则 比赛
#         contest_match = re_list[4]
#         rule_match = re_list[3]
#     else:
#         flag_match = False
# elif re_list[3] and (not re_list[4]):
#     # 单匹配
#     # 判断参数是比赛还是规则
#     if re_list[3] in dict_contest_trans:
#         # 比赛
#         contest_match = re_list[3]
#     elif re_list[3] in dict_rule_trans:
#         # 规则
#         rule_match = re_list[3]
#     else:
#         flag_match = False
# else:
#     flag_match = False
#
# # 如果有匹配
# if flag_match:
#     # 传递函数指针
#     func = get_stages_image
#     # 获取图片
#     img = get_save_temp_image(plain_text, func, num_list, contest_match, rule_match)

# # 测试nonebot 对战 命令文本触发
# plain_text = "全部图"
#
# num_list = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
# # num_list = list(set([int(x) for x in plain_text[:-2]]))
# num_list.sort()
#
# # stage_mode = plain_text[-2:]
# rule_match = None
# contest_match = None
# # res = get_stages_image(num_list, contest_match, rule_match)
# func = get_stages_image
# img = get_save_temp_image(plain_text, func, num_list, contest_match, rule_match)
# # res.show()


# 测试新版随机武器
# plain_text = "随机武器rpg rpg rpg rpg"
# res = get_random_weapon_image(plain_text)
# res.show()

# 测试活动
# res = get_events_image()
# res.show()

# 测试祭典
# res = get_festival_image()
# res.show()

# 测试帮助
# res = get_help_image()
# res.show()

# 测试重载武器数据
# asyncio.run(reload_weapon_info())

# 写出武器翻译字典
# write_weapon_trans_dict()

# 黑名单初始化
# init_blacklist()

# 黑名单测试
# init_blacklist()
# check_msg_permission("Kaiheila", "2486998048", "guild", "4498783094960820")
# check_msg_permission("Kaiheila", "2486998048", "channel", "1339318493016829")

# imageDB.add_or_modify_MESSAGE_CONTROL(
#     "Kaiheila",
#     "2486998048",
#     "channel",
#     "1339318493016829",
#     "嘤嘤嘤",
#     1,
# )
