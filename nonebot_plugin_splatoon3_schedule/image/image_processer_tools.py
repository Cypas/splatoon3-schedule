import copy
import io
import re
import sys
import textwrap
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageOps

from ..data import db_image
from ..utils import *

# 图片文件夹
image_folder = os.path.join(DIR_RESOURCE, "ImageData")
# 武器文件夹
weapon_folder = os.path.join(DIR_RESOURCE, "weapon")
# 字体
font_folder_path = os.path.join(DIR_RESOURCE, "font")
ttf_path = os.path.join(font_folder_path, "common.otf")
ttf_path_chinese = os.path.join(font_folder_path, "cn.ttf")
ttf_path_jp = os.path.join(font_folder_path, "Splatfont2.otf")


def image_to_bytes(image: Image.Image) -> bytes:
    """图片转bytes"""
    buffered = BytesIO()
    image = image.convert("RGB")
    image.save(buffered, format="JPEG")
    return buffered.getvalue()


def get_file(name, format_name="png") -> Image.Image:
    """取文件"""
    img = Image.open(os.path.join(image_folder, "{}.{}".format(name, format_name)))
    return img


def get_weapon(name) -> Image.Image:
    """获取武器"""
    return Image.open(os.path.join(weapon_folder, "{}".format(name)))


def get_cf_file_url(url) -> bytes:
    """cf 网站读文件"""
    r = cf_http_get(url)
    return r.content


def get_save_file(img: ImageInfo) -> Image.Image:
    """向数据库新增或读取素材图片二进制文件"""
    res = db_image.get_img_data(img.name)
    if not res:
        image_data = get_cf_file_url(img.url)
        if len(image_data) != 0:
            # 如果是太大的图片，需要压缩到100k以下确保最后发出图片的大小
            image_data = compress_image(image_data, kb=100, step=10, quality=50)
            logger.info("[ImageDB] new image {}".format(img.name))
            db_image.add_or_modify_IMAGE_DATA(img.name, image_data, img.zh_name, img.source_type)
        return Image.open(io.BytesIO(image_data))
    else:
        return Image.open(io.BytesIO(res.get("image_data")))


def get_file_path(name, format_name="png") -> str:
    """取文件路径"""
    return os.path.join(image_folder, "{}.{}".format(name, format_name))


def circle_corner(img, radii) -> Image.Image:
    """圆角处理"""
    """
    圆角处理
    :param img: 源图象。
    :param radii: 半径，如：30。
    :return: 返回一个圆角处理后的图象。
    """
    # 原图
    img = img.convert("RGBA")
    w, h = img.size

    if w < 2 * radii:
        radii = w // 2
    if h < 2 * radii:
        radii = h // 2

    # 画圆（用于分离4个角）
    circle = Image.new("L", (radii * 2, radii * 2), 0)  # 创建一个黑色背景的画布
    draw = ImageDraw.Draw(circle)
    draw.ellipse((0, 0, radii * 2, radii * 2), fill=255)  # 画白色圆形

    # 画4个角（将整圆分离为4个部分）
    alpha = Image.new("L", img.size, 255)
    left_top = circle.crop((0, 0, radii, radii))
    # x轴翻转
    left_down = ImageOps.flip(left_top)
    # y轴翻转
    right_top = ImageOps.mirror(left_top)
    # x轴翻转
    right_down = ImageOps.flip(right_top)

    alpha.paste(left_top, (0, 0))  # 左上角
    alpha.paste(right_top, (w - radii, 0))  # 右上角
    alpha.paste(right_down, (w - radii, h - radii))  # 右下角
    alpha.paste(left_down, (0, h - radii))  # 左下角

    img.putalpha(alpha)  # 白色区域透明可见，黑色区域不可见
    return img


def tiled_fill(big_image, small_image) -> Image.Image:
    """图片 平铺填充"""
    big_image_w, big_image_h = big_image.size
    small_image_w, small_image_h = small_image.size
    for left in range(0, big_image_w, small_image_w):  # 横纵两个方向上用两个for循环实现平铺效果
        for top in range(0, big_image_h, small_image_h):
            paste_with_a(big_image, small_image, (left, top))
    return big_image


def drawer_text(
    drawer: ImageDraw, text, text_start_pos, text_width, font_color=(255, 255, 255), font_size=30
) -> Image.Image:
    """绘制文字 带自动换行"""

    # 文本分割
    def add_long_text(_text, _text_width) -> [str]:
        punc_pattern = "[,.，。》、—”]+"
        text_list = textwrap.wrap(_text, width=_text_width)
        write_text = []
        for _i, _line in enumerate(text_list):
            write_text.append(_line)
            punc = re.search(punc_pattern, _line)
            if punc:
                # 如果有标点符号开头
                if punc.start() == 0:
                    _line = write_text.pop(-1)
                    former = write_text.pop(-1)
                    former += punc.group()
                    write_text.append(former)
                    _line = _line[punc.end() :]
                    if len(_line) > 0:
                        write_text.append(_line)
        return write_text

    ttf = ImageFont.truetype(ttf_path_chinese, font_size)
    para = add_long_text(text, text_width)
    # 绘制每一行文本
    height = 0
    width = 0
    line_space = 12
    for i, line in enumerate(para):
        drawer.text((text_start_pos[0], (line_space + font_size) * i + text_start_pos[1]), line, font_color, ttf)
        w, h = ttf.getsize(line)
        height += h + line_space
        # 取最长w
        if w > width:
            width = w
    return width, height


def drawer_help_card(pre: str, order_list: [str], desc_list: [str], text_width=20) -> Image.Image:
    """绘制文字 帮助卡片"""
    width = 0
    height = 10
    font_size = 30
    # 创建一张纯透明图片 用来存放卡片
    background = Image.new("RGBA", (1200, 1000), (0, 0, 0, 0))
    drawer = ImageDraw.Draw(background)
    # pre
    text = pre
    pre_pos = (width, height)
    w, h = drawer_text(drawer, text, pre_pos, text_width)
    width += w + 10
    # order_list
    if len(order_list) > 0:
        for i, order in enumerate(order_list):
            text_bg = get_translucent_name_bg(order, 60, font_size)
            text_bg_size = text_bg.size
            text_bg_pos = (width, height - 8)
            paste_with_a(background, text_bg, text_bg_pos)
            width += text_bg_size[0] + 3
        width = pre_pos[0] + 50
        height += font_size + 25
    # desc
    if len(desc_list) > 0:
        for i, desc in enumerate(desc_list):
            text = desc
            text_pos = (width, height)
            w, h = drawer_text(drawer, text, text_pos, text_width, font_size=25)
            height += h + 5
    return background, height


def drawer_nso_help_card(cmd_list: [str], args_list: [(str, str)], text_width=20) -> Image.Image:
    """绘制文字 nso帮助卡片
    cmd_list 第一个值为指令，后面为别名
    args_list 封装的元祖为 指令，介绍
    """

    width = 0
    height = 10
    font_size = 30
    # 创建一张纯透明图片 用来存放卡片
    background = Image.new("RGBA", (1200, 1000), (0, 0, 0, 0))
    drawer = ImageDraw.Draw(background)
    # main_cmd
    # 文字
    text = "指令:"
    pre_pos = (width, height)
    w, h = drawer_text(drawer, text, pre_pos, text_width)
    width += w + 10
    main_cmd_pos = copy.deepcopy(pre_pos)
    # 主要指令
    text_bg = get_translucent_name_bg(cmd_list[0], 60, font_size)
    text_bg_size = text_bg.size
    text_bg_pos = (width, height - 8)
    paste_with_a(background, text_bg, text_bg_pos)
    width += text_bg_size[0] + 10
    if len(cmd_list) > 1:
        # 文字
        text = "别名:"
        pre_pos = (width, height)
        w, h = drawer_text(drawer, text, pre_pos, text_width)
        width += w + 10
        # 遍历渲染别名
        for i, order in enumerate(cmd_list[1:]):
            text_bg = get_translucent_name_bg(order, 60, font_size)
            text_bg_size = text_bg.size
            text_bg_pos = (width, height - 8)
            paste_with_a(background, text_bg, text_bg_pos)
            width += text_bg_size[0] + 3

    width = main_cmd_pos[0] + 20
    height += font_size + 25
    # 参数标题
    text = "参数:"
    arg_pre_pos = (width, height)
    w, h = drawer_text(drawer, text, arg_pre_pos, text_width)
    width += w + 10
    # 参数与参数介绍
    if len(args_list) > 0:
        for i, tup in enumerate(args_list):
            arg, desc = tup
            # 参数
            text_bg = get_translucent_name_bg(arg, 60, font_size, line_height=10)
            text_bg_size = text_bg.size
            text_bg_pos = (width, height - 8)
            paste_with_a(background, text_bg, text_bg_pos)
            # 介绍
            text = desc
            text_pos = (text_bg_size[0] + width + 10, height)
            w, h = drawer_text(drawer, text, text_pos, text_width, font_size=25)
            height += h + 5
    return background, height


def paste_with_a(image_background, image_pasted, pos):
    """图像粘贴 加上a通道参数 使圆角透明"""
    _, _, _, a = image_pasted.convert("RGBA").split()
    image_background.paste(image_pasted, pos, mask=a)


def get_stage_name_bg(stage_name, font_size=24) -> Image.Image:
    """绘制 地图名称及文字底图"""
    ttf = ImageFont.truetype(ttf_path_chinese, font_size)
    w, h = ttf.getsize(stage_name)
    stage_name_bg_size = (w + 20, h + 10)
    # 新建画布
    stage_name_bg = Image.new("RGBA", stage_name_bg_size, (34, 34, 34))
    # 圆角化
    stage_name_bg = circle_corner(stage_name_bg, radii=font_size // 2)
    # # 绘制文字
    drawer = ImageDraw.Draw(stage_name_bg)
    # 文字居中绘制
    text_pos = ((stage_name_bg_size[0] - w) // 2, (stage_name_bg_size[1] - h) // 2)
    drawer.text(text_pos, stage_name, font=ttf, fill=(255, 255, 255))
    return stage_name_bg


def get_translucent_name_bg(
    text, transparency, font_size=24, bg_color=None, font_path: str = ttf_path_chinese, line_height: int = 20
) -> Image.Image:
    """绘制 半透明文字背景"""
    ttf = ImageFont.truetype(font_path, font_size)
    w, h = ttf.getsize(text)
    # 文字背景
    text_bg_size = (w + 20, h + line_height)
    text_bg = get_file("filleted_corner").resize(text_bg_size).convert("RGBA")
    if bg_color is not None:
        text_bg = circle_corner(Image.new("RGBA", text_bg_size, bg_color), radii=20)
    text_bg = circle_corner(text_bg, radii=text_bg_size[1] // 2)
    # 调整透明度
    text_bg = change_image_alpha(text_bg, transparency)
    drawer = ImageDraw.Draw(text_bg)
    # 文字居中绘制
    text_pos = ((text_bg_size[0] - w) / 2, (text_bg_size[1] - h) / 2 - text_bg_size[1] // 10)
    drawer.text(text_pos, text, font=ttf, fill=(255, 255, 255))
    return text_bg


def get_time_head_bg(time_head_bg_size, date_time, start_time, end_time) -> Image.Image:
    """绘制 时间表头"""
    # 绘制背景
    time_head_bg = get_file("time_head_bg").resize(time_head_bg_size)
    # 绘制开始，结束时间 文字居中绘制
    ttf = ImageFont.truetype(ttf_path, 40)
    time_head_text = "{}  {} - {}".format(date_time, start_time, end_time)
    w, h = ttf.getsize(time_head_text)
    time_head_text_pos = (
        (time_head_bg_size[0] - w) / 2,
        (time_head_bg_size[1] - h) / 2 - 12,
    )
    drawer = ImageDraw.Draw(time_head_bg)
    drawer.text(time_head_text_pos, time_head_text, font=ttf, fill=(255, 255))
    return time_head_bg


def have_festival(_festivals) -> bool:
    """是否存在祭典   祭典的结构需要遍历判断"""
    for v in _festivals:
        settings = v.get("festMatchSettings")
        if settings is not None:
            return True
    return False


def now_is_festival(_festivals) -> bool:
    """现在是否是祭典"""
    now = get_time_now_china()
    festival = _festivals[0]
    setting = festival.get("festMatchSetting") or festival.get("festMatchSettings")
    if setting:
        # 如果祭典有参数 且现在时间位于这个区间
        st = time_converter(festival["startTime"])
        et = time_converter(festival["endTime"])
        # logger.info(f"st {st}")
        # logger.info(f"now {now}")
        # logger.info(f"et {et}")
        if st < now < et:
            return True
    return False


# 绘制 一排 地图卡片
def get_stage_card(
    stage1,
    stage2,
    contest_mode,
    contest_name,
    game_mode,
    start_time="",
    end_time="",
    desc="",
    img_size=(1024, 340),
) -> Image.Image:
    image_background = circle_corner(get_file("bg").resize(img_size), radii=20)

    # 绘制两张地图
    # 计算尺寸，加载图片
    stage_size = (int(img_size[0] * 0.48), int(img_size[1] * 0.7))
    image_left = get_save_file(stage1).resize(stage_size, Image.ANTIALIAS)
    image_right = get_save_file(stage2).resize(stage_size, Image.ANTIALIAS)
    # 定义圆角 蒙版
    image_alpha = circle_corner(image_left, radii=16)

    # 计算地图间隔
    width_between_stages = int((img_size[0] - 2 * stage_size[0]) / 3)
    # 绘制第一张地图
    # 图片左上点位
    start_stage_pos = (
        width_between_stages,
        int((img_size[1] - stage_size[1]) / 8 * 7) - 20,
    )
    image_background.paste(image_left, start_stage_pos, mask=image_alpha)
    # 绘制第二张地图
    # 图片左上点位
    next_stage_pos = (
        start_stage_pos[0] + width_between_stages + stage_size[0],
        start_stage_pos[1],
    )
    image_background.paste(image_right, next_stage_pos, mask=image_alpha)

    # 绘制地图中文名及文字背景
    # 左半地图名
    stage_name_bg = get_stage_name_bg(stage1.zh_name, 30)
    stage_name_bg_size = stage_name_bg.size
    # X:地图x点位+一半的地图宽度-文字背景的一半宽度   Y:地图Y点位+一半地图高度-文字背景高度
    stage_name_bg_pos = (
        start_stage_pos[0] + stage_size[0] // 2 - stage_name_bg_size[0] // 2,
        start_stage_pos[1] + stage_size[1] - stage_name_bg_size[1],
    )
    paste_with_a(image_background, stage_name_bg, stage_name_bg_pos)

    # 右半地图名
    stage_name_bg = get_stage_name_bg(stage2.zh_name, 30)
    stage_name_bg_size = stage_name_bg.size
    # X:地图x点位+一半的地图宽度-文字背景的一半宽度   Y:地图Y点位+一半地图高度-文字背景高度
    stage_name_bg_pos = (
        next_stage_pos[0] + +stage_size[0] // 2 - stage_name_bg_size[0] // 2,
        next_stage_pos[1] + stage_size[1] - stage_name_bg_size[1],
    )
    paste_with_a(image_background, stage_name_bg, stage_name_bg_pos)

    # 中间绘制 模式图标
    # 中文转英文来取文件
    image_icon = get_file(contest_name)
    image_icon_size = image_icon.size
    # X: 整张卡片宽度/2 - 图标宽度/2    Y: 左地图x点位+地图高度/2 - 图标高度/2
    stage_mid_pos = (
        img_size[0] // 2 - image_icon_size[0] // 2,
        start_stage_pos[1] + stage_size[1] // 2 - image_icon_size[1] // 2,
    )
    paste_with_a(image_background, image_icon, stage_mid_pos)

    # 绘制模式文本
    # 空白尺寸
    blank_size = (img_size[0], start_stage_pos[1])
    drawer = ImageDraw.Draw(image_background)
    # 绘制竞赛模式文字
    ttf = ImageFont.truetype(ttf_path_chinese, 40)
    contest_mode_pos = (start_stage_pos[0] + 10, start_stage_pos[1] - 60)
    drawer.text(contest_mode_pos, contest_mode, font=ttf, fill=(255, 255, 255))
    # 绘制游戏模式文字
    game_mode_text = get_trans_game_mode(game_mode)
    game_mode_text_pos = (blank_size[0] // 3, contest_mode_pos[1])
    drawer.text(game_mode_text_pos, game_mode_text, font=ttf, fill=(255, 255, 255))
    # 绘制游戏模式小图标
    game_mode_img = get_file(game_mode).resize((35, 35), Image.ANTIALIAS)
    game_mode_img_pos = (game_mode_text_pos[0] - 40, game_mode_text_pos[1] + 10)
    paste_with_a(image_background, game_mode_img, game_mode_img_pos)
    # # 绘制开始，结束时间
    # ttf = ImageFont.truetype(ttf_path, 40)
    # time_pos = (blank_size[0] * 2 // 3, contest_mode_pos[1] - 10)
    # drawer.text(
    #     time_pos, "{} - {}".format(start_time, end_time), font=ttf, fill=(255, 255, 255)
    # )
    # 绘制活动模式描述
    if desc != "":
        ttf = ImageFont.truetype(ttf_path, 40)
        desc_pos = (blank_size[0] * 2 // 3, contest_mode_pos[1] - 10)
        drawer.text(desc_pos, desc, font=ttf, fill=(255, 255, 255))

    return image_background


def get_weapon_card(weapon: [WeaponData], weapon_card_bg_size, rgb, font_color) -> Image.Image:
    """绘制一排武器"""
    # 单张武器背景
    weapon_bg_size = (150, 230)
    # 主武器，副武器，大招
    main_size = (120, 120)
    sub_size = (55, 55)
    special_size = (55, 55)
    # 一排武器的背景
    weapon_card_bg = circle_corner(Image.new("RGBA", weapon_card_bg_size, rgb), radii=20)

    # 遍历进行贴图
    for i, v in enumerate(weapon):
        v: WeaponData
        # 单张武器背景
        weapon_bg = Image.new("RGB", weapon_bg_size, rgb)
        weapon_bg = circle_corner(weapon_bg, radii=20)
        # 调整透明度
        weapon_bg = change_image_alpha(weapon_bg, 80)
        # 主武器
        main_image_bg = Image.new("RGBA", main_size, (30, 30, 30, 255))
        main_image = Image.open(io.BytesIO(v.image)).resize(main_size, Image.ANTIALIAS)
        main_image_bg_pos = ((weapon_bg_size[0] - main_size[0]) // 2, 10)
        # main_image = circle_corner(main_image, radii=16)
        # main_image_bg.paste(main_image, (0, 0))
        # 副武器
        sub_image_bg = Image.new("RGBA", sub_size, (60, 60, 60, 255))
        sub_image = Image.open(io.BytesIO(v.sub_image)).resize(sub_size, Image.ANTIALIAS)
        sub_image_bg_pos = (main_image_bg_pos[0], main_image_bg_pos[1] + main_size[1] + 10)
        # sub_image = circle_corner(sub_image, radii=16)
        # sub_image_bg.paste(sub_image, (0, 0))
        # 大招
        special_image_bg = Image.new("RGBA", special_size, (30, 30, 30, 255))
        special_image = Image.open(io.BytesIO(v.special_image)).resize(special_size, Image.ANTIALIAS)
        special_image_bg_pos = (main_image_bg_pos[0] + main_size[0] - special_size[0], sub_image_bg_pos[1])
        # special_image = circle_corner(special_image, radii=16)
        # special_image_bg.paste(special_image, (0, 0))
        # 贴到单个武器背景
        # weapon_bg.paste(main_image, main_image_bg_pos)
        # weapon_bg.paste(sub_image, sub_image_bg_pos)
        # weapon_bg.paste(special_image, special_image_bg_pos)

        paste_with_a(weapon_bg, main_image, main_image_bg_pos)
        paste_with_a(weapon_bg, sub_image, sub_image_bg_pos)
        paste_with_a(weapon_bg, special_image, special_image_bg_pos)

        # 武器名
        weapon_zh_name = v.zh_name
        font_size = 16
        if len(weapon_zh_name) > 8:
            font_size = 15
        if len(weapon_zh_name) > 10:
            font_size = 14
        font = ImageFont.truetype(ttf_path_chinese, font_size)
        zh_name_size = font.getsize(weapon_zh_name)
        # 纯文字不带背景 实现方式
        dr = ImageDraw.Draw(weapon_bg)
        zh_name_pos = ((weapon_bg_size[0] - zh_name_size[0]) // 2, weapon_bg_size[1] - zh_name_size[1] - 7)
        dr.text(zh_name_pos, weapon_zh_name, font=font, fill=font_color)
        # 带背景文字 实现方式
        # weapon_zh_name_bg = get_stage_name_bg(weapon_zh_name, font_size)
        # weapon_zh_name_bg_size = weapon_zh_name_bg.size
        # zh_name_pos = (
        #     (weapon_bg_size[0] - weapon_zh_name_bg_size[0]) // 2,
        #     weapon_bg_size[1] - weapon_zh_name_bg_size[1],
        # )
        # paste_with_a(weapon_bg, weapon_zh_name_bg, zh_name_pos)

        # 将武器背景贴到武器区域
        paste_with_a(
            weapon_card_bg,
            weapon_bg,
            ((weapon_bg_size[0] + 10) * i + 10, (weapon_card_bg_size[1] - weapon_bg_size[1]) // 2),
        )

    return weapon_card_bg


def get_event_card(event, event_card_bg_size) -> Image.Image:
    """绘制 活动地图卡片"""
    # 背景
    event_card_bg = get_file("filleted_corner").resize(event_card_bg_size).convert("RGBA")
    # 调整透明度
    event_card_bg = change_image_alpha(event_card_bg, 70)
    # 比赛卡片
    stage_card_pos = (10, 20)
    stage = event["leagueMatchSetting"]["vsStages"]
    stage_card = get_stage_card(
        ImageInfo(
            name=stage[0]["name"],
            url=stage[0]["image"]["url"],
            zh_name=get_trans_stage(stage[0]["id"]),
            source_type="对战地图",
        ),
        ImageInfo(
            name=stage[1]["name"],
            url=stage[1]["image"]["url"],
            zh_name=get_trans_stage(stage[1]["id"]),
            source_type="对战地图",
        ),
        "活动比赛",
        "event_bg",
        event["leagueMatchSetting"]["vsRule"]["rule"],
    )
    stage_card_size = stage_card.size
    paste_with_a(event_card_bg, stage_card, stage_card_pos)
    # 绘制三个或多个活动时间
    drawer = ImageDraw.Draw(event_card_bg)
    ttf = ImageFont.truetype(ttf_path_chinese, 40)
    pos_h = stage_card_pos[1] + stage_card_size[1] + 20
    for v in range(len(event["timePeriods"])):
        # 绘制游戏模式小图标
        game_mode_text = event["leagueMatchSetting"]["vsRule"]["rule"]
        game_mode_img_size = (35, 35)
        game_mode_img = get_file(game_mode_text).resize(game_mode_img_size, Image.ANTIALIAS)
        game_mode_img_pos = (20, pos_h)
        paste_with_a(event_card_bg, game_mode_img, game_mode_img_pos)
        # 绘制时间
        st = event["timePeriods"][v]["startTime"]
        et = event["timePeriods"][v]["endTime"]
        time_text_pos = (game_mode_img_pos[0] + game_mode_img_size[0] + 10, pos_h)
        time_text = "{} {}  {} - {} {}".format(
            time_converter_yd(st),
            "周" + dict_weekday_trans.get(time_converter_weekday(st)),
            time_converter_hm(st),
            time_converter_yd(et),
            time_converter_hm(et),
        )
        drawer.text(time_text_pos, time_text, font=ttf, fill=(255, 255, 255))
        # 绘制虚线
        transverse_line_pos = (game_mode_img_pos[0], game_mode_img_pos[1] + game_mode_img_size[1] + 20)
        # 开始与结束的xy坐标
        transverse_line_pos_list = [
            transverse_line_pos,
            (transverse_line_pos[0] + event_card_bg_size[0] - 50, transverse_line_pos[1]),
        ]
        draw_grid_transverse_line(drawer, transverse_line_pos_list, fill="white", width=3, gap=25)
        # 绘制 时间状态 文字
        now = get_time_now_china()
        text = ""
        text_color = ""
        if time_converter(st) > now:
            text = "未开始"
            text_color = (243, 254, 176)
        elif time_converter(st) < now < time_converter(et):
            text = "进行中"
            text_color = (144, 203, 251)
        elif time_converter(et) < now:
            text = "已结束"
            text_color = (165, 170, 163)
        text_size = ttf.getsize(text)
        drawer.text(
            (transverse_line_pos_list[1][0] - text_size[0] - 10, time_text_pos[1]),
            text,
            font=ttf,
            fill=text_color,
        )
        # 计算下一行高度
        pos_h += 80
    return event_card_bg


def get_festival_team_card(
    festival, card_bg_size: tuple, teams_list: [], area_title: str, font_path: str = ttf_path_chinese
) -> Image.Image:
    """绘制 祭典组别卡片"""
    group_img_size = (1000, 390)
    rectangle_h = 100
    # 取背景rgb颜色
    bg_rgb = dict_bg_rgb["祭典"]
    # 组别卡片
    team_bg = Image.new("RGB", card_bg_size, bg_rgb)
    team_bg = circle_corner(team_bg, radii=20)
    # 调整透明度
    team_bg = change_image_alpha(team_bg, 60)
    # 整理数据
    title = festival["title"]
    st = festival["startTime"]
    et = festival["endTime"]
    time_text = "{} {}  {} - {} {}  {}".format(
        time_converter_yd(st),
        "周" + dict_weekday_trans.get(time_converter_weekday(st)),
        time_converter_hm(st),
        time_converter_yd(et),
        "周" + dict_weekday_trans.get(time_converter_weekday(et)),
        time_converter_hm(et),
    )
    # 绘制标题
    font_size = 30
    text_bg = get_translucent_name_bg(title, 80, font_size, font_path=font_path)
    text_bg_size = text_bg.size
    # 贴上文字背景
    text_bg_pos = ((card_bg_size[0] - text_bg_size[0]) // 2, 20)
    paste_with_a(team_bg, text_bg, text_bg_pos)
    # 绘制区域标题
    drawer = ImageDraw.Draw(team_bg)
    area_title_text_pos = ((card_bg_size[0] - group_img_size[0]) // 2, 30)
    text_rgb = dict_bg_rgb["祭典时间-金黄"]
    ttf = ImageFont.truetype(ttf_path_chinese, font_size)
    drawer.text(area_title_text_pos, area_title, font=ttf, fill=text_rgb)
    # 存放阵营图片的透明卡片
    group_card_size = (group_img_size[0], group_img_size[1] + rectangle_h)
    group_card = Image.new("RGBA", group_card_size, (0, 0, 0, 0))

    # 绘制阵营图片
    group_img = get_save_file(
        ImageInfo(name=title, url=festival["image"]["url"], zh_name=title, source_type="祭典阵营图片")
    ).resize(group_img_size)
    paste_with_a(group_card, group_img, (0, 0))
    # 绘制阵营名称
    drawer = ImageDraw.Draw(group_card)
    pos_w = group_card_size[0] // 6
    font_size = 30
    ttf = ImageFont.truetype(ttf_path_chinese, font_size)
    for k, v in enumerate(teams_list):
        group_text_bg_rgb = (int(v["color"]["r"] * 255), int(v["color"]["g"] * 255), int(v["color"]["b"] * 255))
        # 绘制色块对比图
        satrt_xy = (group_card_size[0] // 3 * k, group_img_size[1])
        end_xy = (satrt_xy[0] + group_card_size[0] // 3, satrt_xy[1] + rectangle_h)
        drawer.rectangle((satrt_xy, end_xy), fill=group_text_bg_rgb)
        # 绘制阵营名称
        group_text_bg = get_translucent_name_bg(v["teamName"], 100, font_size, group_text_bg_rgb, font_path=font_path)
        w, h = group_text_bg.size
        group_text_bg_pos = (pos_w - (w // 2), group_img_size[1] - h - 5)
        paste_with_a(group_card, group_text_bg, group_text_bg_pos)
        # 计算下一个
        pos_w += group_card_size[0] // 3
    group_card = circle_corner(group_card, radii=20)
    group_card_pos = ((card_bg_size[0] - group_img_size[0]) // 2, text_bg_pos[1] + text_bg_size[1] + 20)
    paste_with_a(team_bg, group_card, group_card_pos)

    drawer = ImageDraw.Draw(team_bg)
    # 绘制时间
    w, h = ttf.getsize(time_text)
    # 文字居中绘制
    time_text_pos = ((card_bg_size[0] - w) / 2, group_card_pos[1] + rectangle_h + group_img_size[1] + 20)
    text_rgb = dict_bg_rgb["祭典时间-金黄"]
    drawer.text(time_text_pos, time_text, font=ttf, fill=text_rgb)

    return team_bg


def get_festival_result_card(card_bg_size: tuple, teams_list: [], font_path: str = ttf_path_chinese) -> Image.Image:
    """绘制 祭典结算卡片"""
    bg_rgb: tuple[int, int, int] = (0, 0, 0)
    win_team_name: str = ""
    # 背景颜色取获胜队伍的rgb颜色
    for k, v in enumerate(teams_list):
        if v["result"]["isWinner"]:
            bg_rgb = (int(v["color"]["r"] * 255), int(v["color"]["g"] * 255), int(v["color"]["b"] * 255))
            win_team_name = v["teamName"]

    # 取背景rgb颜色
    win_rgb = dict_bg_rgb["祭典时间-金黄"]
    # 结算卡片
    result_bg = Image.new("RGB", card_bg_size, bg_rgb)
    result_bg = circle_corner(result_bg, radii=20)
    # 存放素材的临时卡片
    temp_card_size = (card_bg_size[0] - 40, card_bg_size[1] - 80)
    temp_card = Image.new("RGB", temp_card_size, bg_rgb)
    # 绘制队伍图标
    for k, v in enumerate(teams_list):
        team_bg_size = (200, 80)
        team_icon_size = (70, 70)
        # 绘制纯色背景
        team_bg_rgb = (int(v["color"]["r"] * 255), int(v["color"]["g"] * 255), int(v["color"]["b"] * 255))
        team_bg = Image.new("RGB", team_bg_size, team_bg_rgb)
        team_bg = circle_corner(team_bg, radii=14)
        # 绘制图标
        team_icon = get_save_file(
            ImageInfo(name=v["teamName"], url=v["image"]["url"], zh_name=v["teamName"], source_type="祭典阵营单图")
        ).resize(team_icon_size)
        team_icon_pos = ((team_bg_size[0] - team_icon_size[0]) // 2, (team_bg_size[1] - team_icon_size[1]) // 2)
        paste_with_a(team_bg, team_icon, team_icon_pos)
        # 粘贴队伍图标
        width_space = card_bg_size[0] // 5 + 30
        team_bg_pos = (300 + width_space * k, 20)
        paste_with_a(temp_card, team_bg, team_bg_pos)
    # 绘制每个条目结果
    list_item_names = ["法螺获得率", "得票率", "开放", "挑战", "三色夺宝攻击"]
    pos_h = 120
    font_size = 30
    ttf = ImageFont.truetype(ttf_path_chinese, font_size)
    drawer = ImageDraw.Draw(temp_card)
    for v in range(5):
        # 绘制条目名称
        text = list_item_names[v]
        w, h = ttf.getsize(text)
        # 文字居中绘制
        text_pos = (130 + (60 - w) // 2, pos_h + 5)
        drawer.text(text_pos, text, font=ttf, fill=(255, 255, 255))
        # 绘制条目结算
        item_card_size = (card_bg_size[0] // 3 * 2, 50)
        item_card = get_festival_result_item_card(item_card_size, teams_list, v)
        item_card_pos = (290, pos_h)
        paste_with_a(temp_card, item_card, item_card_pos)
        pos_h += h + 30
    # 绘制最终冠军
    font_size = 50
    ttf_cn = ImageFont.truetype(ttf_path_chinese, font_size)
    ttf_win = ImageFont.truetype(font_path, font_size)
    win_text_1 = win_team_name
    win_text_2 = " 获胜!"
    w, h = ttf_win.getsize(win_text_1 + win_text_2)
    text_1_pos = ((temp_card_size[0] - w) // 2, pos_h + 30)
    drawer.text(text_1_pos, win_text_1, font=ttf_win, fill=win_rgb)
    # 分开绘制队伍名和获胜
    w, h = ttf_win.getsize(win_text_1)
    text_2_pos = (text_1_pos[0] + w, text_1_pos[1])
    drawer.text(text_2_pos, win_text_2, font=ttf_cn, fill=win_rgb)

    # 将临时图片容器贴到底图
    temp_card = circle_corner(temp_card, radii=16)
    temp_card = change_image_alpha(temp_card, 80)
    temp_card_pos = ((card_bg_size[0] - temp_card_size[0]) // 2, (card_bg_size[1] - temp_card_size[1]) // 2)
    paste_with_a(result_bg, temp_card, temp_card_pos)

    return result_bg


def get_festival_result_item_card(
    card_bg_size: tuple, teams_list: [dict], item_index: int, font_path: str = ttf_path_chinese
) -> Image.Image:
    """绘制 祭典条目结算卡片"""
    bg_rgb = dict_bg_rgb["祭典结算项目卡片"]
    item_card = Image.new("RGBA", card_bg_size, bg_rgb)
    item_card = circle_corner(item_card, radii=30)
    drawer = ImageDraw.Draw(item_card)
    font_size = 24
    ttf = ImageFont.truetype(font_path, font_size)

    # 格式化整理数据,返回 是否是赢家，百分比点数
    def get_data(index: int, value: dict) -> (bool, str):
        flag_win = False
        _percentage = 0
        if index == 0:
            flag_win = value["result"]["isHoragaiRatioTop"]
            _percentage = value["result"]["horagaiRatio"]
        elif index == 1:
            flag_win = value["result"]["isVoteRatioTop"]
            _percentage = value["result"]["voteRatio"]
        elif index == 2:
            flag_win = value["result"]["isRegularContributionRatioTop"]
            _percentage = value["result"]["regularContributionRatio"]
        elif index == 3:
            flag_win = value["result"]["isChallengeContributionRatioTop"]
            _percentage = value["result"]["challengeContributionRatio"]
        elif index == 4:
            flag_win = value["result"]["isTricolorContributionRatioTop"]
            _percentage = value["result"]["tricolorContributionRatio"]
        return flag_win, "{:.2f}%".format(_percentage * 100)

    win_rgb = dict_bg_rgb["祭典时间-金黄"]
    width_space = card_bg_size[0] // 3 + 10
    for k, v in enumerate(teams_list):
        text_rgb = (255, 255, 255)
        win, percentage = get_data(item_index, v)
        if win:
            text_rgb = win_rgb
        # 绘制百分比
        w, h = ttf.getsize(percentage)
        # 文字居中绘制
        text_pos = (65 + width_space * k, (card_bg_size[1] - h) // 2)
        drawer.text(text_pos, percentage, font=ttf, fill=text_rgb)
    return item_card


def get_event_desc_card(cht_event_data, event_desc_card_bg_size) -> Image.Image:
    """绘制 活动地图描述卡片"""
    # 背景
    event_desc_card_bg = get_file("filleted_corner").resize(event_desc_card_bg_size).convert("RGBA")
    # 调整透明度
    event_desc_card_bg = change_image_alpha(event_desc_card_bg, 60)
    # 对规则文字分行
    desc = cht_event_data["desc"]
    regulation = cht_event_data["regulation"]
    regulation_list = regulation.split("<br />")
    # 绘制文本
    drawer = ImageDraw.Draw(event_desc_card_bg)
    ttf = ImageFont.truetype(ttf_path_chinese, 30)
    pos_h = 20
    for v in regulation_list:
        if v != "":
            text_pos = (20, pos_h)
            drawer.text(text_pos, v, font=ttf, fill=(255, 255, 255))
        pos_h += 40
    return event_desc_card_bg


def draw_grid_vertical_line(draw, pos_list, fill, width, gap):
    """画虚线 竖线"""
    x_begin, y_begin = pos_list[0]
    x_end, y_end = pos_list[1]
    for y in range(y_begin, y_end, gap):
        draw.line([(x_begin, y), (x_begin, y + gap / 2)], fill=fill, width=width)


def draw_grid_transverse_line(draw, pos_list, fill, width, gap):
    """画虚线 横线"""
    x_begin, y_begin = pos_list[0]
    x_end, y_end = pos_list[1]
    for x in range(x_begin, x_end, gap):
        draw.line([(x, y_begin), (x + gap / 2, y_begin)], fill=fill, width=width)


def change_image_alpha(image, transparency) -> Image.Image:
    """改变图片不透明度  值为0-100"""
    image = image.convert("RGBA")
    alpha = image.split()[-1]
    alpha = alpha.point(lambda p: p * transparency // 100)
    new_image = Image.merge("RGBA", image.split()[:-1] + (alpha,))
    return new_image


def compress_image(image_bytes: bytes, kb=500, step=10, quality=50) -> bytes:
    """不改变图片尺寸压缩到指定大小
    :param image_bytes: 压缩源文件
    :param kb: 压缩目标，KB
    :param step: 每次调整的压缩比率
    :param quality: 初始压缩比率
    :return: 压缩后文件
    """
    o_size = sys.getsizeof(image_bytes) / 1024
    if o_size <= kb:
        return image_bytes
    new_image: bytes = None
    while o_size > kb:
        buffered: io.BytesIO = BytesIO()
        im = Image.open(io.BytesIO(image_bytes))
        rgb_im = im.convert("RGB")
        rgb_im.save(buffered, quality=quality, format="JPEG")
        if quality - step < 0:
            break
        quality -= step
        new_image = buffered.getvalue()
        o_size = sys.getsizeof(new_image) / 1024
    return new_image


# 旧版函数 随机武器
# def old_get_random_weapon(weapon1: [] = None, weapon2: [] = None):
#     # 取两组随机武器
#     if weapon1 is None:
#         weapon1 = random.sample(os.listdir(weapon_folder), k=4)
#     if weapon2 is None:
#         weapon2 = random.sample(os.listdir(weapon_folder), k=4)
#     weapon_size = (122, 158)
#     image_background = circle_corner(get_file("bg").resize((620, 420)), radii=20)
#     dr = ImageDraw.Draw(image_background)
#     font = ImageFont.truetype(ttf_path, 50)
#     # 绘制中间vs和长横线
#     dr.text((278, 160), "VS", font=font, fill="#FFFFFF")
#     dr.line([(18, 210), (270, 210)], fill="#FFFFFF", width=4)
#     dr.line([(350, 210), (602, 210)], fill="#FFFFFF", width=4)
#     # 遍历进行贴图
#     for i in range(4):
#         image = get_weapon(weapon1[i]).resize(weapon_size, Image.ANTIALIAS)
#         image_background.paste(image, ((160 * i + 5), 20))
#         image = get_weapon(weapon2[i]).resize(weapon_size, Image.ANTIALIAS)
#         image_background.paste(image, ((160 * i + 5), 20 + 220))
#
#     return image_background


# if __name__ == '__main__':
#     get_random_weapon().show()
