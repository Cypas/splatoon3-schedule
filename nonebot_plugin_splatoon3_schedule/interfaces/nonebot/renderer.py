from ...util import send_msg
from ...application.result import ServiceResult


class NoneBotRenderer:
    """将应用服务结果渲染为 NoneBot 消息。"""

    async def send(self, bot, event, result: ServiceResult) -> None:
        if result.message:
            await send_msg(bot, event, result.message)
        if result.image_data is not None:
            await send_msg(
                bot,
                event,
                result.image_data,
                is_cache=result.data.get("cached", True),
            )
