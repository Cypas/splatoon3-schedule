from typing import Any


class CosFileStorage:
    """基于现有腾讯云 COS 上传器的图片存储适配。"""

    def upload_image(self, image_data: bytes, owner_id: str | None = None) -> dict[str, Any] | None:
        try:
            from ..utils.cos_upload import cos_uploader

            return cos_uploader.upload_file(image_data, owner_id)
        except Exception:
            return None
