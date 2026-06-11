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
        
        headers = {
            "User-Agent": DEFAULT_USER_AGENT
        }
        
        # 使用 httpx 新版本的 transport 参数配置代理（使用异步传输层）
        if proxy_address:
            transport = httpx.AsyncHTTPTransport(proxy=f"http://{proxy_address}")
            async with httpx.AsyncClient(transport=transport, timeout=10.0, follow_redirects=True) as client:
                response = await client.get(target_url, headers=headers)
        else:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                response = await client.get(target_url, headers=headers)
            
            # 检查 Cloudflare 特征
            cf_indicators = [
                "cloudflare" in response.headers.get("server", "").lower(),
                "Just a moment..." in response.text,
                "Please wait" in response.text and "cloudflare" in response.text.lower(),
                "challenge-platform" in response.text,
                "cf-challenge" in response.text,
                "cf_clearance" in response.text,
                "__cf_bm" in response.text
            ]
            
            return any(cf_indicators)
            
    except Exception as e:
        logger.warning(f"检测 Cloudflare 保护时出错: {str(e)}")
        # 如果检测失败，假设可能有保护，走 cf_clearance 流程
        return True


async def get_cf_clearance(target_url: str, context, timeout: int = 60) -> tuple:
    """获取 cf_clearance cookies 和 user_agent（必须传入已有的 context）
    
    此函数专门为截图服务，必须在已有 browser context 的情况下调用。
    使用 cloudscraper 获取 cookies（更可靠的 Cloudflare 绕过），然后在 Playwright 中使用。
    
    Args:
        target_url: 目标网址
        context: 已有的 browser context（必须提供）
        timeout: 超时时间（秒）
        
    Returns:
        (cookies_dict, user_agent_str, page) 或 (None, None, None) 如果失败
        page 是已经准备好的页面，可直接用于截图
    """
    global cf_clearance_cookies, cf_clearance_ua, cf_clearance_expire_time
    
    # 检查是否过期（30分钟有效期）
    current_time = time.time()
    if current_time - cf_clearance_expire_time < 1800:  # 30分钟
        return cf_clearance_cookies, cf_clearance_ua, None
    
    # 先检测是否真的需要 cf_clearance
    needs_protection = await has_cloudflare_protection(target_url)
    if not needs_protection:
        logger.info("目标网站没有 Cloudflare 保护，跳过 cf_clearance 获取")
        return None, None, None
    
    # 使用 cloudscraper 获取 cookies（更可靠）
    try:
        import cloudscraper
        
        # 创建增强版 cloudscraper 实例
        # 添加更多伪装配置来绕过更严格的 Cloudflare 检测
        scraper = cloudscraper.create_scraper(
            delay=10,  # 添加延迟
            browser={
                'custom': DEFAULT_USER_AGENT,
                'platform': 'windows',
                'mobile': False
            }
        )
        
        # 添加更多请求头来模拟真实浏览器
        scraper.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="148", "Microsoft Edge";v="148"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
        })
        
        # 设置代理（如果有）
        if proxy_address:
            scraper.proxies = {
                'http': f'http://{proxy_address}',
                'https': f'http://{proxy_address}'
            }
        
        # 发送请求获取 cookies
        logger.info(f"使用 cloudscraper 访问 {target_url}")
        response = scraper.get(target_url, timeout=timeout)
        
        if response.status_code == 200:
            logger.info("cloudscraper 成功获取页面")
        else:
            logger.warning(f"cloudscraper 收到状态码: {response.status_code}")
            # 如果收到 403，尝试增加延迟并重试
            if response.status_code == 403:
                logger.info("收到 403，尝试增加延迟并重试...")
                # 使用更长的延迟重试（time 已在文件顶部导入）
                time.sleep(5)  # 等待 5 秒
                # 创建新的 scraper 实例（可能需要新的会话）
                scraper = cloudscraper.create_scraper(
                    delay=30,
                    browser={
                        'custom': DEFAULT_USER_AGENT
                    }
                )
                response = scraper.get(target_url, timeout=timeout * 2)
                logger.info(f"重试后状态码: {response.status_code}")
        
        # 提取 cookies
        cf_clearance_cookies = {}
        for cookie in scraper.cookies:
            cf_clearance_cookies[cookie.name] = cookie.value
        
        # 检查是否获取到了 cf_clearance cookie
        if 'cf_clearance' not in cf_clearance_cookies:
            logger.warning("未获取到 cf_clearance cookie，可能无法绕过 Cloudflare")
        
        # 获取 user_agent
        cf_clearance_ua = scraper.headers.get('User-Agent', DEFAULT_USER_AGENT)
        cf_clearance_expire_time = time.time()
        
        logger.info(f"cloudscraper 获取 cookies: {list(cf_clearance_cookies.keys())}")
        
        # 将 cookies 添加到 context
        if cf_clearance_cookies:
            parsed = urlparse(target_url)
            domain = parsed.netloc
            cookies_to_add = []
            for name, value in cf_clearance_cookies.items():
                cookies_to_add.append({
                    'name': name,
                    'value': value,
                    'domain': '.' + domain if not domain.startswith('.') else domain,
                    'path': '/'
                })
            await context.add_cookies(cookies_to_add)
            logger.info(f"已将 {len(cookies_to_add)} 个 cookies 添加到 context")
        
        # 创建页面（此时 cookies 已经在 context 中）
        page = await context.new_page()
        
        # 应用隐身插件（额外保护）
        stealth = Stealth()
        await stealth.apply_stealth_async(context)
        
        # 访问目标页面（使用已获取的 cookies）
        await page.goto(target_url, timeout=timeout * 1000)
        
        # 等待页面加载
        await page.wait_for_load_state("load", timeout=30000)
        
        return cf_clearance_cookies, cf_clearance_ua, page
            
    except Exception as e:
        logger.error(f"使用 cloudscraper 获取 cf_clearance 时出错: {str(e)}")
        # 降级到纯 playwright 方式
        return await _get_cf_clearance_fallback(target_url, context, timeout)


async def _get_cf_clearance_fallback(target_url: str, context, timeout: int = 60) -> tuple:
    """降级方案：纯 Playwright 方式获取 cf_clearance（当 cloudscraper 失败时使用）"""
    global cf_clearance_cookies, cf_clearance_ua, cf_clearance_expire_time
    
    logger.info("降级到纯 Playwright 方式获取 cf_clearance")
    
    try:
        page = await context.new_page()
        
        # 应用隐身插件
        stealth = Stealth()
        await stealth.apply_stealth_async(context)
        
        # 访问目标页面
        await page.goto(target_url, timeout=timeout * 1000)
        
        # 等待页面加载
        await page.wait_for_load_state("load", timeout=30000)
        
        # 获取 cookies
        cookies = await context.cookies()
        cf_clearance_cookies = {cookie['name']: cookie['value'] for cookie in cookies}
        
        # 获取 user_agent
        cf_clearance_ua = await page.evaluate('() => {return navigator.userAgent}')
        cf_clearance_expire_time = time.time()
        
        logger.info(f"Playwright 方式获取 cookies: {list(cf_clearance_cookies.keys())}")
        
        return cf_clearance_cookies, cf_clearance_ua, page
            
    except Exception as e:
        logger.error(f"降级方案也失败: {str(e)}")
        return None, None, None


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
    is_sendou_domain = parsed_url.netloc.endswith('sendou.ink')
    
    cf_cookies = None
    cf_ua = None
    cf_page = None  # 用于接收已通过 CF 挑战的页面
    
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
        # 先尝试获取 cf_clearance cookies（使用已有的 context）
        # 返回的 cf_page 是已经通过 CF 挑战的页面，可直接用于截图
        cf_cookies, cf_ua, cf_page = await get_cf_clearance(shot_url, context, timeout=30)
        # logger.info(f"检测到 sendou.ink 域名，使用 cf_clearance 机制")
        
        # 如果获取到新的 user_agent，更新 context 的 user_agent
        if cf_ua:
            user_agent = cf_ua
    
    # 如果获取到 cf_clearance cookies，则添加到 context（使用正确的域名）
    if cf_cookies and is_sendou_domain:
        await context.add_cookies([
            {'name': name, 'value': value, 'domain': '.sendou.ink', 'path': '/'}
            for name, value in cf_cookies.items()
        ])
        logger.info("使用 cf_clearance cookies 进行请求")
    
    # 如果 cf_page 存在（说明刚通过 CF 挑战），直接使用这个页面
    # 否则创建新页面
    if cf_page:
        page = cf_page
        logger.info("复用已通过 CF 挑战的页面进行截图")
    else:
        page = await context.new_page()

    try:
        # 如果是新创建的页面，需要 goto；如果是复用的页面，已经在目标页面上了
        if not cf_page:
            # 添加随机延迟模拟人类行为
            await page.goto(shot_url, wait_until="load", timeout=300000)
            await page.wait_for_timeout(random.randint(2000, 4000))
        else:
            # 复用页面，只需等待页面完全加载
            await page.wait_for_load_state("load")
            await page.wait_for_timeout(random.randint(1000, 2000))
        
        if selector:
            # 元素选择器 - 支持CSS选择器表达式，包括动态类名匹配
            # 例如：传入 [class^="_buildsContainer_"] 来匹配以 _buildsContainer_ 开头的类名
            try:
                await page.wait_for_selector(selector, timeout=30000)
                element = await page.query_selector(selector)
                img = await element.screenshot(path=shot_path)
                return img  # 成功找到元素，返回正常截图
            except Exception as selector_error:
                logger.error(f"Selector '{selector}' not found within timeout: {str(selector_error)}")
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