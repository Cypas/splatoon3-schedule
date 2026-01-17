import os, logging, mimetypes, re, sys, hashlib
from datetime import datetime
from typing import Optional, Dict, Any, Tuple
from io import BytesIO

from nonebot import logger

from .utils import plugin_config, get_image_size

try:
    from qcloud_cos import CosConfig, CosS3Client
    from qcloud_cos.cos_exception import CosServiceError, CosClientError
except:
    CosConfig = CosS3Client = None
    CosServiceError = CosClientError = Exception


class COSUploader:
    """腾讯云COS文件上传器
    
    提供文件上传、删除、查询等功能
    """
    def __init__(self):
        """初始化COS上传器

        从配置中读取COS相关配置，初始化COS客户端
        """
        self.config = plugin_config.splatoon3_cos_config
        self.client = None
        self.md5_cache: Dict[str, str] = {}  # MD5到URL的缓存
        if self.config.enabled and all([CosConfig, CosS3Client]):
            self._init_client()

    def _calculate_md5(self, file_data: bytes) -> str:
        """计算文件数据的MD5值

        Args:
            file_data: 文件数据的bytes类型

        Returns:
            str: 文件的MD5值（32位十六进制字符串）
        """
        return hashlib.md5(file_data).hexdigest()

    def _get_cached_url(self, md5: str) -> Optional[str]:
        """从缓存中获取URL

        Args:
            md5: 文件的MD5值

        Returns:
            Optional[str]: 缓存的URL，如果不存在则返回None
        """
        return self.md5_cache.get(md5)

    def _cache_url(self, md5: str, url: str):
        """缓存URL

        Args:
            md5: 文件的MD5值
            url: 文件的URL
        """
        self.md5_cache[md5] = url

    def _init_client(self):
        """初始化COS客户端

        使用配置中的SecretId、SecretKey和Region初始化腾讯云COS客户端
        """
        try:
            cos_config = CosConfig(Region=self.config.region, SecretId=self.config.secret_id,
                                   SecretKey=self.config.secret_key, Scheme='https')
            self.client = CosS3Client(cos_config)
            logger.info(f"[cos_uploader]cos_uploader初始化完成")
        except:
            pass

    def _validate_file(self, file_data: bytes) -> bool:
        """文件大小校验

        Args:
            file_data: 文件数据的bytes类型

        Returns:
            bool: 文件大小是否在限制范围内
        """
        return sys.getsizeof(file_data) <= self.config.max_file_size

    def _generate_cos_key(self, user_id: str = None,
                          md5: str = None, file_data: bytes = None) -> str:
        """生成COS上传路径
        
        Args:
            user_id: 用户ID
            md5: 文件的MD5值
            file_data: 文件数据的bytes类型（用于获取扩展名）
            
        Returns:
            str: COS上传路径，格式为: 用户ID/MD5.扩展名
        """
        # 使用MD5作为文件名
        ext = self._get_file_extension(file_data)
        filename = f"{md5}{ext}"
        
        # 获取上传路径前缀
        upload_prefix = self.config.upload_path_prefix
        
        # 确保前缀以/结尾，避免路径拼接问题
        if upload_prefix and not upload_prefix.endswith('/'):
            upload_prefix += '/'
        
        if user_id:
            return f"{upload_prefix}{user_id}/{filename}"
        else:
            return f"{upload_prefix}{filename}"

    def _get_content_type(self, file_data: bytes) -> str:
        """获取文件的Content-Type
        
        Args:
            file_data: 文件数据的bytes类型
            
        Returns:
            str: 文件的MIME类型，默认为image/jpeg
        """
        # 优先从文件数据获取MIME类型
        if file_data:
            # 读取文件头部字节来判断文件类型
            import imghdr
            image_type = imghdr.what(None, h=file_data[:32])
            if image_type:
                return f'image/{image_type}'
        return 'image/jpeg'

    def _get_file_extension(self, file_data: bytes) -> str:
        """从文件数据或文件名获取文件扩展名
        
        Args:
            file_data: 文件数据的bytes类型
            
        Returns:
            str: 文件扩展名（包含点），如.jpg
        """
        # 优先从文件数据获取扩展名
        import imghdr
        image_type = imghdr.what(None, h=file_data[:32])
        if image_type:
            return f'.{image_type}'
        return '.jpg'

    def upload_file(self, file_data: bytes, user_id: str = None) -> Optional[Dict[str, Any]]:
        """上传文件到COS
        
        Args:
            file_data: 文件数据的bytes类型
            user_id: 用户ID，用于生成路径
            
        Returns:
            Optional[Dict[str, Any]]: 上传结果字典，包含:
                - success: 是否成功
                - cos_key: COS路径
                - file_url: 文件访问URL
                - file_size: 文件大小
                - width: 图片宽度
                - height: 图片高度
                - px: 尺寸字符串
                - cached: 是否来自缓存
        """
        if not self.config.enabled or not self.client:
            return None
        try:
            if not self._validate_file(file_data):
                return None
            
            # 计算文件MD5
            md5 = self._calculate_md5(file_data)
            
            # 检查缓存中是否已存在该MD5的URL
            cached_url = self._get_cached_url(md5)
            if cached_url:
                # 从缓存中获取尺寸信息
                try:
                    dimensions = get_image_size(file_data)
                except:
                    dimensions = (300, 300)
                # 返回缓存的结果
                return {
                    'success': True,
                    'cos_key': cached_url.replace(_get_cos_base_url() + '/', ''),
                    'file_url': cached_url,
                    'filename': os.path.basename(cached_url),
                    'file_size': sys.getsizeof(file_data),
                    'width': dimensions[0],
                    'height': dimensions[1],
                    'px': f'#{dimensions[0]}px #{dimensions[1]}px',
                    'cached': True
                }
            
            try:
                dimensions = get_image_size(file_data)
            except:
                dimensions = (300, 300)
            
            # 使用MD5作为文件名生成cos_key
            cos_key = self._generate_cos_key(user_id, md5, file_data)
            response = self.client.put_object(Bucket=self.config.bucket_name, Body=BytesIO(file_data),
                                              Key=cos_key, ContentType=self._get_content_type(file_data))
            base_url = f"https://{self.config.domain}" if self.config.domain else \
                f"https://{self.config.bucket_name}.cos.{self.config.region}.myqcloud.com"
            file_url = f"{base_url}/{cos_key}"
            # 将URL存入缓存
            self._cache_url(md5, file_url)
            return {
                'success': True, 'cos_key': cos_key, 'file_url': file_url,
                'filename': os.path.basename(cos_key), 'file_size': sys.getsizeof(file_data),
                'width': dimensions[0], 'height': dimensions[1], 'px': f'#{dimensions[0]}px #{dimensions[1]}px',
                'cached': False
            }
        except:
            return None

    def delete_file(self, cos_key: str) -> bool:
        """删除COS上的文件
        
        Args:
            cos_key: COS路径
            
        Returns:
            bool: 是否删除成功
        """
        if not self.client:
            return False
        try:
            self.client.delete_object(Bucket=self.config.bucket_name, Key=cos_key)
            return True
        except:
            return False

    def get_file_info(self, cos_key: str) -> Optional[Dict[str, Any]]:
        """获取COS文件信息
        
        Args:
            cos_key: COS路径
            
        Returns:
            Optional[Dict[str, Any]]: 文件信息字典，包含:
                - cos_key: COS路径
                - content_length: 文件大小
                - content_type: 文件类型
                - last_modified: 最后修改时间
        """
        if not self.client:
            return None
        try:
            response = self.client.head_object(Bucket=self.config.bucket_name, Key=cos_key)
            return {'cos_key': cos_key, 'content_length': response.get('Content-Length'),
                    'content_type': response.get('Content-Type'), 'last_modified': response.get('Last-Modified')}
        except:
            return None

    def list_files(self, prefix: str = None, max_keys: int = 1000) -> Optional[list]:
        """列出COS上的文件
        
        Args:
            prefix: 路径前缀，用于筛选文件
            max_keys: 最大返回数量
            
        Returns:
            Optional[list]: 文件列表，每个元素包含:
                - key: COS路径
                - size: 文件大小
                - last_modified: 最后修改时间
        """
        if not self.client:
            return None
        try:
            kwargs = {'Bucket': self.config.bucket_name, 'MaxKeys': max_keys}
            if prefix:
                kwargs['Prefix'] = prefix
            response = self.client.list_objects(**kwargs)
            if 'Contents' not in response:
                return []
            return [{'key': obj['Key'], 'size': obj['Size'], 'last_modified': obj['LastModified']} for obj in
                    response['Contents']]
        except:
            return None


cos_uploader = COSUploader()


def upload_image(file_data: bytes, user_id: str = None, return_url_only: bool = False):
    """上传图片到COS
    
    Args:
        file_data: 图片数据的bytes类型
        user_id: 用户ID
        return_url_only: 是否只返回URL
        
    Returns:
        上传结果或URL
    """
    result = cos_uploader.upload_file(file_data, user_id)
    return result['file_url'] if result and return_url_only else result


def upload_file(file_data: bytes, user_id: str = None, return_url_only: bool = False):
    return upload_image(file_data, user_id, return_url_only=return_url_only)


def simple_upload_file(file_data: bytes, user_id: str = None):
    return upload_image(file_data, user_id, return_url_only=True)


def _get_cos_base_url() -> str:
    base_url = f"https://{cos_uploader.config['domain']}" if cos_uploader.config.get('domain') else \
        f"https://{cos_uploader.config['bucket_name']}.cos.{cos_uploader.config['region']}.myqcloud.com"
    return base_url


def get_upload_url(cos_key: str):
    return f"{_get_cos_base_url()}/{cos_key}"


def delete_by_url(file_url: str):
    if not file_url:
        return False
    base_url = _get_cos_base_url()
    return cos_uploader.delete_file(file_url[len(base_url):]) if file_url.startswith(base_url) else False
