"""
Playwright 浏览器操作处理器

负责处理浏览器相关的操作，包括：
- 浏览器初始化和管理
- 网页截图功能
- Cloudflare 绕过机制
"""

from urllib.parse import urlparse

import time
import random

# 使用 playwright-stealth 2.0.x 版本（新版 API）
from playwright.async_api import Browser, async_playwright
from playwright_stealth import Stealth

from ..utils import logger
from ..config import plugin_config


class ErrorImage:
    """错误图片包装类

    用于标记这是一个错误截图（元素未找到或超时），不应被缓存。
    但仍然返回图片数据供用户查看。

    Attributes:
        image: PIL.Image 对象或 bytes 数据
        error_message: 错误消息
    """

    def __init__(self, image, error_message=None):
        self.image = image
        self.error_message = error_message or "元素未找到，已返回当前页面截图"


# 浏览器全局变量
_browser = None

# cf_clearance 相关全局变量
cf_clearance_cookies = {}
cf_clearance_ua = ""
cf_clearance_expire_time = 0

# 代理地址（从配置文件获取）
proxy_address = plugin_config.splatoon3_proxy_address

# 统一的 User-Agent（所有地方都使用这个常量）
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36 Edg/148.0.0.0"


async def init_browser() -> Browser:
    """初始化 browser 并唤起"""
    global _browser
    p = await async_playwright().start()
    browser_args = [
        # 禁用自动化标志
        "--disable-blink-features=AutomationControlled",
        # 添加用户代理（使用统一常量）
        f"--user-agent={DEFAULT_USER_AGENT}",
    ]
    if proxy_address:
        proxies = {"server": "http://{}".format(proxy_address)}
        # 代理访问
        _browser = await p.chromium.launch(
            proxy=proxies, args=browser_args, headless=True
        )
    else:
        _browser = await p.chromium.launch(args=browser_args, headless=True)
    return _browser


async def get_browser() -> Browser:
    """获取目前唤起的 browser"""
    global _browser
    if _browser is None or not _browser.is_connected():
        _browser = await init_browser()
    return _browser


async def has_cloudflare_protection(target_url: str) -> bool:
    """检测目标网址是否有 Cloudflare 保护

    Args:
        target_url: 目标网址

    Returns:
        bool: 是否有 Cloudflare 保护
    """
    try:
        # 使用 httpx 快速检测（比浏览器更快）
        import httpx

        headers = {"User-Agent": DEFAULT_USER_AGENT}

        # 使用 httpx 新版本的 transport 参数配置代理（使用异步传输层）
        if proxy_address:
            transport = httpx.AsyncHTTPTransport(proxy=f"http://{proxy_address}")
            async with httpx.AsyncClient(
                transport=transport, timeout=10.0, follow_redirects=True
            ) as client:
                response = await client.get(target_url, headers=headers)
        else:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                response = await client.get(target_url, headers=headers)

            # 检查 Cloudflare 特征
            cf_indicators = [
                "cloudflare" in response.headers.get("server", "").lower(),
                "Just a moment..." in response.text,
                "Please wait" in response.text
                and "cloudflare" in response.text.lower(),
                "challenge-platform" in response.text,
                "cf-challenge" in response.text,
                "cf_clearance" in response.text,
                "__cf_bm" in response.text,
            ]

            return any(cf_indicators)

    except Exception as e:
        logger.warning(f"检测 Cloudflare 保护时出错: {str(e)}")
        # 如果检测失败，假设可能有保护，走 cf_clearance 流程
        return True


async def get_cf_clearance(target_url: str, context, timeout: int = 60) -> dict:
    """获取 cf_clearance cookies（必须传入已有的 context）

    此函数专门为截图服务，必须在已有 browser context 的情况下调用。
    使用 Flaresolverr 服务获取 cookies，然后在 Playwright 中使用。

    Args:
        target_url: 目标网址
        context: 已有的 browser context（必须提供）
        timeout: 超时时间（秒）

    Returns:
        cookies_dict 或 None 如果失败
    """
    global cf_clearance_cookies, cf_clearance_expire_time

    # 检查是否过期（30分钟有效期）
    current_time = time.time()
    if current_time - cf_clearance_expire_time < 1800:  # 30分钟
        return cf_clearance_cookies

    # 先检测是否真的需要 cf_clearance
    needs_protection = await has_cloudflare_protection(target_url)
    if not needs_protection:
        logger.info("目标网站没有 Cloudflare 保护，跳过 cf_clearance 获取")
        return None

    # 直接使用 Flaresolverr 获取 cookies
    return await _get_cf_clearance_fallback(target_url, context, timeout)


async def _get_cf_clearance_fallback(
    target_url: str, context, timeout: int = 60
) -> dict:
    """降级方案：使用 Flaresolverr 服务获取 cf_clearance

    如果配置了 Flaresolverr 服务，则使用它获取 cookies；
    如果未配置或失败，则直接返回失败（不再使用纯 Playwright 方式）。

    Args:
        target_url: 目标网址
        context: 已有的 browser context（必须提供）
        timeout: 超时时间（秒）

    Returns:
        cookies_dict 或 None 如果失败
    """
    global cf_clearance_cookies, cf_clearance_expire_time

    # 检查是否配置了 Flaresolverr 服务
    flaresolverr_url = plugin_config.splatoon3_cf_flaresolverr_server_url

    if not flaresolverr_url:
        logger.info("未配置 Flaresolverr 服务，跳过 cf_clearance 获取")
        return None

    # 配置了 Flaresolverr，尝试使用它
    logger.info(f"使用 Flaresolverr 服务获取 cf_clearance: {flaresolverr_url}")
    cf_clearance_cookies = await _get_cf_clearance_with_flaresolverr(
        target_url, flaresolverr_url, timeout
    )

    if cf_clearance_cookies:
        cf_clearance_expire_time = time.time()
        return cf_clearance_cookies

    # Flaresolverr 获取失败
    logger.warning("Flaresolverr 服务获取失败，无法绕过 Cloudflare")
    return None


async def _get_cf_clearance_with_flaresolverr(
    target_url: str, flaresolverr_url: str, timeout: int = 60
) -> dict:
    """使用 Flaresolverr 服务获取 cf_clearance cookies

    Flaresolverr 是一个专门用于绕过 Cloudflare 保护的服务，
    通过真实浏览器渲染页面来获取有效的 cf_clearance cookies。

    官方文档: https://github.com/FlareSolverr/FlareSolverr

    Args:
        target_url: 目标网址
        flaresolverr_url: Flaresolverr 服务 URL（如 http://localhost:8191/v1）
        timeout: 超时时间（秒）

    Returns:
        cookies_dict 或 None 如果失败
    """
    try:
        from ..utils import async_http_post

        # 构建 Flaresolverr 请求体
        # 注意：FlareSolverr v2 不再支持 headers 参数
        data = {
            "cmd": "request.get",
            "url": target_url,
            "maxTimeout": timeout * 1000 * 3,  # 增加超时时间到 180 秒
            "cookies": [],
            "returnOnlyCookies": True,  # 只返回 cookies，不返回 HTML 内容，提高性能
            "maxWait": 30000,  # 增加等待时间到 30 秒
            "stealth": True,  # 启用隐身模式，模拟真实浏览器
            "ignoreHttpsErrors": True,  # 忽略 HTTPS 错误
            "waitUntil": "domcontentloaded",  # 等待 DOM 加载完成
        }
        if proxy_address:
            proxy_url = "http://{}".format(proxy_address)
            data["proxy"] = {"url": proxy_url}

        # 使用 utils 中的 async_http_post 函数发送请求
        # 使用更长的超时时间（匹配 Flaresolverr 的 maxTimeout）
        response = await async_http_post(
            flaresolverr_url, data, with_proxy=False, timeout=timeout * 3
        )

        if response.status_code != 200:
            # 尝试解析错误响应
            try:
                error_response = response.json()
                error_msg = error_response.get("message", "未知错误")
                logger.error(
                    f"Flaresolverr 返回错误状态码 {response.status_code}: {error_msg}"
                )
            except Exception:
                # 无法解析 JSON，记录原始响应
                logger.error(f"Flaresolverr 返回错误状态码 {response.status_code}")
                logger.debug(f"Flaresolverr 响应内容: {response.text[:1000]}")
            return None

        # 解析响应
        result = response.json()

        if result.get("status") != "ok":
            error_message = result.get("message", "未知错误")
            error_details = result.get("error", "")
            if error_details:
                error_message = f"{error_message} | 详细信息: {error_details}"
            logger.error(f"Flaresolverr 返回错误: {error_message}")

            # 记录更多调试信息
            if "solution" in result:
                logger.debug(f"Flaresolverr solution: {result['solution']}")

            return None

        # 提取 cookies
        cookies = {}
        for cookie in result.get("solution", {}).get("cookies", []):
            cookies[cookie["name"]] = cookie["value"]

        logger.info(f"Flaresolverr 成功获取 cookies: {list(cookies.keys())}")

        # 检查是否获取到了 cf_clearance cookie
        if "cf_clearance" not in cookies:
            logger.warning(
                "Flaresolverr 未返回 cf_clearance cookie，可能无法绕过 Cloudflare"
            )

        return cookies

    except Exception as e:
        error_msg = str(e) if str(e) else type(e).__name__
        logger.error(f"使用 Flaresolverr 获取 cf_clearance 时出错: {error_msg}")
        return None


# 广告域名列表（用于阻止请求）
AD_DOMAINS = [
    "googlesyndication.com",
    "googleadservices.com",
    "doubleclick.net",
    "google.com/ads",
    "ads.google.com",
    "safeframe.googlesyndication.com",
]


async def remove_ads(page):
    """移除页面中的广告元素

    该函数通过以下方式移除广告：
    1. 删除包含广告的 DOM 元素
    2. 阻止广告相关的网络请求

    Args:
        page: Playwright Page 对象
    """
    try:
        # 1. 删除广告容器元素
        await page.evaluate(
            """
            // 删除谷歌广告容器
            document.querySelectorAll('[id*="google_ads"], [id*="google-ads"], [id*="ad-"], [class*="advertisement"]').forEach(el => el.remove());
            
            // 删除 iframe 广告
            document.querySelectorAll('iframe[src*="googlesyndication"], iframe[src*="doubleclick"], iframe[title*="广告"]').forEach(el => el.remove());
            
            // 删除 sticky footer 广告
            document.querySelectorAll('[id*="sticky_footer"], [class*="sticky-footer"]').forEach(el => el.remove());
        """
        )

        logger.debug("已移除页面中的广告元素")
    except Exception as e:
        logger.debug(f"移除广告时出错: {str(e)}")


async def get_screenshot(
    shot_url,
    mode="pc",
    selector=None,
    shot_path=None,
) -> bytes:
    """通过 browser 获取 shot_url 中的网页截图

    Args:
        shot_url: 要截图的网址
        mode: 模式，"pc" 或 "mobile"
        selector: CSS 选择器，可选
        shot_path: 截图保存路径，可选

    Returns:
        bytes: 截图的二进制数据
    """
    # 只对 sendou.ink 域名使用 cf_clearance 机制
    parsed_url = urlparse(shot_url)
    is_sendou_domain = parsed_url.netloc.endswith("sendou.ink")

    cf_cookies = None
    # 使用统一的默认 user_agent
    user_agent = DEFAULT_USER_AGENT

    # playwright 要求不能有多个 browser 被同时唤起
    browser = await get_browser()

    if mode == "pc":
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            locale="zh-CH",
            user_agent=user_agent,
        )
    elif mode == "mobile":
        context = await browser.new_context(
            viewport={"width": 500, "height": 2000},
            locale="zh-CH",
            user_agent=user_agent,
        )

    # 在创建 context 后调用 get_cf_clearance，传入已有的 context
    if is_sendou_domain:
        # 尝试获取 cf_clearance cookies（使用已有的 context）
        cf_cookies = await get_cf_clearance(shot_url, context, timeout=30)

    # 如果获取到 cf_clearance cookies，则添加到 context（使用正确的域名）
    if cf_cookies and is_sendou_domain:
        await context.add_cookies(
            [
                {"name": name, "value": value, "domain": ".sendou.ink", "path": "/"}
                for name, value in cf_cookies.items()
            ]
        )
        logger.info("使用 cf_clearance cookies 进行请求")

    # 创建新页面
    page = await context.new_page()

    # 添加网络请求拦截，阻止广告域名的请求
    async def block_ads(route):
        request_url = route.request.url
        for domain in AD_DOMAINS:
            if domain in request_url:
                await route.abort()
                return
        await route.continue_()

    await page.route("**/*", block_ads)

    try:
        # 访问目标页面
        await page.goto(shot_url, wait_until="load", timeout=300000)
        await page.wait_for_timeout(random.randint(2000, 4000))

        # 移除广告元素
        await remove_ads(page)

        if selector:
            # 元素选择器 - 支持CSS选择器表达式，包括动态类名匹配
            # 例如：传入 [class^="_buildsContainer_"] 来匹配以 _buildsContainer_ 开头的类名
            try:
                await page.wait_for_selector(selector, timeout=30000)
                element = await page.query_selector(selector)
                img = await element.screenshot(path=shot_path)
                return img  # 成功找到元素，返回正常截图
            except Exception as selector_error:
                logger.error(
                    f"Selector '{selector}' not found within timeout: {str(selector_error)}"
                )
                # 仍然截图供用户查看，但返回 ErrorImage 标记不应缓存
                img = await page.screenshot(path=shot_path)
                return ErrorImage(img, f"页面元素 '{selector}' 未找到")
        else:
            img = await page.screenshot(path=shot_path)

        return img
    except Exception as e:
        logger.error("Screenshot failed" + str(e))
        raise e
    finally:
        await context.close()
