"""
MinIO Service để quản lý upload/download files từ MinIO Object Storage
"""
import os
import logging
from io import BytesIO
from typing import Optional, BinaryIO
from minio import Minio
from minio.error import S3Error
from app.config import settings

logger = logging.getLogger(__name__)

class MinIOService:
    def __init__(self):
        """Khởi tạo MinIO client"""
        try:
            self.client = Minio(
                settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=settings.MINIO_USE_SSL
            )
            self.bucket_name = settings.MINIO_BUCKET_NAME
            self._ensure_bucket_exists()
            logger.info(f"✅ MinIO service initialized. Bucket: {self.bucket_name}")
        except Exception as e:
            logger.error(f"❌ Failed to initialize MinIO service: {e}")
            raise
    
    def _ensure_bucket_exists(self):
        """Đảm bảo bucket tồn tại, nếu không thì tạo mới"""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                logger.info(f"✅ Created bucket: {self.bucket_name}")
        except S3Error as e:
            logger.error(f"❌ Error ensuring bucket exists: {e}")
            raise
    
    def upload_file(self, object_path: str, file_data: bytes, content_type: str = "application/octet-stream") -> bool:
        """
        Upload file lên MinIO
        
        Args:
            object_path: Đường dẫn object trong bucket (ví dụ: "images/customer_1.jpg")
            file_data: Dữ liệu file dạng bytes
            content_type: MIME type của file
        
        Returns:
            True nếu thành công, False nếu thất bại
        """
        try:
            data_stream = BytesIO(file_data)
            self.client.put_object(
                self.bucket_name,
                object_path,
                data_stream,
                length=len(file_data),
                content_type=content_type
            )
            logger.info(f"✅ Uploaded to MinIO: {object_path}")
            return True
        except S3Error as e:
            logger.error(f"❌ Error uploading to MinIO: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error uploading to MinIO: {e}", exc_info=True)
            return False
    
    def download_file(self, object_path: str) -> Optional[bytes]:
        """
        Download file từ MinIO
        
        Args:
            object_path: Đường dẫn object trong bucket
        
        Returns:
            Dữ liệu file dạng bytes hoặc None nếu lỗi
        """
        try:
            response = self.client.get_object(self.bucket_name, object_path)
            data = response.read()
            response.close()
            response.release_conn()
            logger.debug(f"✅ Downloaded from MinIO: {object_path}")
            return data
        except S3Error as e:
            if e.code == 'NoSuchKey':
                logger.warning(f"⚠️  Object not found in MinIO: {object_path}")
            else:
                logger.error(f"❌ Error downloading from MinIO: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected error downloading from MinIO: {e}", exc_info=True)
            return None
    
    def file_exists(self, object_path: str) -> bool:
        """Kiểm tra file có tồn tại trong MinIO không"""
        try:
            self.client.stat_object(self.bucket_name, object_path)
            return True
        except S3Error as e:
            if e.code == 'NoSuchKey':
                return False
            logger.error(f"❌ Error checking file existence in MinIO: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error checking file existence: {e}", exc_info=True)
            return False
    
    def delete_file(self, object_path: str) -> bool:
        """Xóa file từ MinIO"""
        try:
            self.client.remove_object(self.bucket_name, object_path)
            logger.info(f"✅ Deleted from MinIO: {object_path}")
            return True
        except S3Error as e:
            logger.error(f"❌ Error deleting from MinIO: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error deleting from MinIO: {e}", exc_info=True)
            return False
    
    def get_file_url(self, object_path: str) -> str:
        """
        Lấy URL để truy cập file từ MinIO (presigned URL)
        
        Args:
            object_path: Đường dẫn object trong bucket
        
        Returns:
            Presigned URL (expires sau 7 ngày)
        """
        try:
            from datetime import timedelta
            url = self.client.presigned_get_object(
                self.bucket_name,
                object_path,
                expires=timedelta(days=7)
            )
            return url
        except Exception as e:
            logger.error(f"❌ Error generating presigned URL: {e}")
            # Fallback: trả về endpoint URL
            protocol = "https" if settings.MINIO_USE_SSL else "http"
            return f"{protocol}://{settings.MINIO_ENDPOINT}/{self.bucket_name}/{object_path}"
    
    def list_files(self, prefix: str = "") -> list:
        """Liệt kê tất cả files với prefix"""
        try:
            objects = self.client.list_objects(self.bucket_name, prefix=prefix, recursive=True)
            return [obj.object_name for obj in objects]
        except Exception as e:
            logger.error(f"❌ Error listing files from MinIO: {e}")
            return []

# Singleton instance
minio_service = MinIOService()

